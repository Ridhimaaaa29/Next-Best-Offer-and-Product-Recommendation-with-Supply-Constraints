"""
Supply-Constrained Decision Module with Lightweight Laya + Weighted Fallback.

Architecture:
Customer ID
  -> Candidate Generation
  -> Recommendation Model Scoring (Gradient Boosting Propensity / Heuristic)
  -> Authoritative Deterministic Policy Engine (Active, Stock > 0, Known/Fresh Inventory, Margin >= 10%, Contexts)
  -> Remove EXCLUDE Candidates (Strict Infeasibility Pruning)
  -> Capped Feasible Shortlist -> Laya Decision Layer (lazy singleton, CPU, bounded candidates)
  -> Authoritative Policy Revalidation of Laya Selection
  -> Fallback to WeightedDecisionEngine (and Baseline Ranker if needed) ONLY when Laya fails/unavailable/invalid
  -> Top-K Structured Output with objective scores, weights, and audit metadata.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.app.db.repositories import CustomerRepository, OperationalCatalogueRepository
from backend.app.db.session import SessionLocal
from backend.app.decision.baseline_ranker import rank_feasible_candidates
from backend.app.decision.laya_adapter import LayaAdapter
from backend.app.decision.weighted_engine import WeightedDecisionEngine
from backend.app.recommendation.recommendation_model import (
    RecommendationModel,
    ScoredCandidate,
)
from backend.app.recommendation.policy_engine import evaluate_product


class DecisionModule:
    """
    Decision Engine combining Gradient Boosting recommendation scoring,
    deterministic supply/policy constraints, primary Laya inference, and
    lightweight weighted deterministic fallback.
    """

    def __init__(
        self,
        recommender: Optional[RecommendationModel] = None,
        session: Optional[Session] = None,
        laya_adapter: Optional[LayaAdapter] = None,
        decision_engine: Optional[WeightedDecisionEngine] = None,
    ):
        self.recommender = recommender or RecommendationModel(session=session)
        self.session = session
        self.laya_adapter = laya_adapter or LayaAdapter()
        self.decision_engine = decision_engine or WeightedDecisionEngine()

    def _load_operational_map(self, product_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Best-effort fetch of operational catalogue metrics for objective scoring."""
        if not product_ids:
            return {}
        try:
            if self.session is not None:
                result = OperationalCatalogueRepository(self.session).get_products_policy_map(product_ids)
                return result if isinstance(result, dict) else {}
            with SessionLocal() as session:
                result = OperationalCatalogueRepository(session).get_products_policy_map(product_ids)
                return result if isinstance(result, dict) else {}
        except Exception:
            return {}

    def decide(
        self,
        customer_id: str,
        top_k: int = 5,
        candidate_limit: int = 20,
        reward_context: bool = False,
        promotion_context: bool = False,
        express_context: bool = False,
        injected_candidates: Optional[List[Dict[str, Any]]] = None,
        use_decision_engine: bool = True,
        use_laya: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Execute the supply-constrained recommendation and decision workflow."""
        if not customer_id or not isinstance(customer_id, str):
            raise ValueError(f"Invalid customer_id: '{customer_id}'. Must be a non-empty string.")

        if not isinstance(top_k, int) or top_k <= 0:
            raise ValueError(f"Invalid top_k: {top_k}. Must be a positive integer.")

        engine_requested = use_decision_engine if use_laya is None else bool(use_laya)

        # 1. Validate customer exists
        self._validate_customer_exists(customer_id)

        # 2. Candidate Generation & Recommendation Scoring
        try:
            scored_candidates: List[ScoredCandidate] = self.recommender.rank_candidates(
                customer_id=customer_id,
                candidates=injected_candidates,
                candidate_limit=candidate_limit,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to generate and score candidates for {customer_id}: {e}") from e

        if not scored_candidates:
            return {
                "status": "NO_CANDIDATES",
                "customer_id": customer_id,
                "candidate_count": 0,
                "feasible_count": 0,
                "excluded_count": 0,
                "top_k_requested": top_k,
                "recommendations": [],
                "feasible_candidates": [],
                "excluded_candidates": [],
                "all_evaluated_candidates": [],
                "decision_method": "NONE",
                "decision_engine_status": "SKIPPED_NO_CANDIDATES",
                "selected_product": None,
                "decision_weights": None,
                "objective_scores": {},
                "final_ranking": [],
                "final_validation": None,
                "fallback_used": False,
                "fallback_reason": None,
                "decision_explanation": "No candidate products found for customer.",
                "message": f"No candidate products found for customer {customer_id}.",
            }

        # 3. Deterministic Policy Evaluation (Authoritative Pre-Filter)
        prod_ids = [str(c.product_id) for c in scored_candidates]
        op_map = self._load_operational_map(prod_ids)
        injected_map = (
            {str(item["product_id"]): item for item in injected_candidates if item.get("product_id")}
            if injected_candidates
            else {}
        )

        evaluated_candidates: List[Dict[str, Any]] = []
        feasible_candidates: List[Dict[str, Any]] = []
        excluded_candidates: List[Dict[str, Any]] = []

        for candidate in scored_candidates:
            cand_dict = candidate.to_dict()
            prod_id = str(candidate.product_id)
            op_info = op_map.get(prod_id, {})
            inj_info = injected_map.get(prod_id, {})

            try:
                policy_eval = evaluate_product(
                    product_id=prod_id,
                    reward_context=reward_context,
                    promotion_context=promotion_context,
                    express_context=express_context,
                )
            except ValueError as ve:
                policy_eval = {
                    "product_id": prod_id,
                    "decision": "EXCLUDE",
                    "reasons": [f"Operational catalogue data missing or unverified: {ve}"],
                    "flags": [],
                }
            except Exception as pe_err:
                raise RuntimeError(
                    f"Database or policy evaluation failure on product {prod_id}: {pe_err}"
                ) from pe_err

            def _pick(key: str, default: Any = None) -> Any:
                if key in inj_info and inj_info[key] is not None:
                    return inj_info[key]
                if key in op_info and op_info[key] is not None:
                    return op_info[key]
                return default

            margin_val = _pick("gross_margin_pct")
            stock_val = _pick("available_stock")

            item_summary = {
                "product_id": cand_dict["product_id"],
                "product_name": cand_dict["product_name"],
                "category": cand_dict["category"],
                "subcategory": cand_dict["subcategory"],
                "brand": cand_dict["brand"],
                "unit_price": cand_dict["unit_price"],
                "product_rating": cand_dict["product_rating"],
                "product_popularity": cand_dict["product_popularity"],
                "product_status": cand_dict.get("product_status", "active"),
                "recommendation_score": cand_dict["score"],
                "score_explanation": cand_dict["explanation"],
                "policy_decision": policy_eval["decision"],
                "policy_reasons": policy_eval["reasons"],
                "policy_flags": policy_eval["flags"],
                "available_stock": float(stock_val) if stock_val is not None else None,
                "inventory_status": _pick("inventory_status"),
                "gross_margin_pct": float(margin_val) if margin_val is not None else None,
                "shipping_days": _pick("shipping_days"),
                "reorder_point": _pick("reorder_point"),
                "data_freshness_status": _pick("data_freshness_status"),
                "reward_eligible": _pick("reward_eligible"),
                "promotion_eligible": _pick("promotion_eligible"),
                "max_discount_pct": (
                    float(_pick("max_discount_pct"))
                    if _pick("max_discount_pct") is not None
                    else None
                ),
            }

            evaluated_candidates.append(item_summary)
            if policy_eval["decision"] == "PASS":
                feasible_candidates.append(item_summary)
            else:
                excluded_candidates.append(item_summary)

        if not feasible_candidates:
            return {
                "status": "ALL_CANDIDATES_EXCLUDED",
                "customer_id": customer_id,
                "candidate_count": len(evaluated_candidates),
                "feasible_count": 0,
                "excluded_count": len(excluded_candidates),
                "top_k_requested": top_k,
                "recommendations": [],
                "feasible_candidates": [],
                "excluded_candidates": excluded_candidates,
                "all_evaluated_candidates": evaluated_candidates,
                "decision_method": "NONE",
                "laya_status": "SKIPPED_NO_FEASIBLE_CANDIDATES",
                "decision_engine_status": "SKIPPED_NO_FEASIBLE_CANDIDATES",
                "laya_selected_product": None,
                "selected_product": None,
                "decision_weights": None,
                "objective_scores": {},
                "final_ranking": [],
                "final_validation": None,
                "fallback_used": False,
                "fallback_reason": None,
                "decision_explanation": "All candidate products failed deterministic policy checks.",
            }

        # 4. Pre-compute deterministic objective metrics for full audit transparency
        feasible_ids = {str(c["product_id"]) for c in feasible_candidates}
        enriched_pool = list(feasible_candidates)
        decision_weights: Optional[Dict[str, float]] = None
        objective_scores: Dict[str, Any] = {}
        if self.decision_engine.enabled:
            try:
                pre_eval = self.decision_engine.choose(
                    feasible_candidates,
                    express_context=express_context,
                )
                decision_weights = pre_eval.get("weights")
                objective_scores = pre_eval.get("objective_scores", {})
                obj_by_id = objective_scores
                enriched_pool = [
                    {
                        **cand,
                        "objective_scores": obj_by_id.get(str(cand["product_id"]), {}),
                        "weighted_score": (
                            obj_by_id.get(str(cand["product_id"]), {}).get("weighted_score")
                        ),
                    }
                    for cand in feasible_candidates
                ]
            except Exception:
                enriched_pool = list(feasible_candidates)

        # 5. Primary Laya Inference -> Final Policy Revalidation -> Deterministic Weighted Fallback
        selected_product: Optional[Dict[str, Any]] = None
        final_validation: Optional[Dict[str, Any]] = None
        final_ranking: List[Dict[str, Any]] = []
        decision_explanation: str = ""
        fallback_used = False
        fallback_reason: Optional[str] = None
        laya_status = "SUCCESS"
        decision_engine_status = "LAYA_PRIMARY"
        decision_method = "LAYA"
        final_recommendations: List[Dict[str, Any]] = []
        laya_selected_product: Optional[Dict[str, Any]] = None

        if not engine_requested:
            fallback_used = True
            laya_status = "UNAVAILABLE"
            fallback_reason = "Laya was bypassed by request configuration; deterministic weighted fallback applied."
        else:
            try:
                laya_result = self.laya_adapter.choose(
                    enriched_pool,
                    express_context=express_context,
                )
                chosen_item = laya_result["selected"]
                chosen_id = str(chosen_item.get("product_id"))

                if chosen_id not in feasible_ids:
                    raise RuntimeError(
                        f"Laya selected '{chosen_id}' which is not in the feasible candidate pool."
                    )

                reval = evaluate_product(
                    product_id=chosen_id,
                    reward_context=reward_context,
                    promotion_context=promotion_context,
                    express_context=express_context,
                )
                if reval["decision"] != "PASS":
                    raise RuntimeError(
                        f"Laya-selected product {chosen_id} failed authoritative policy revalidation: "
                        f"{', '.join(reval['reasons'])}"
                    )

                laya_selected_product = chosen_item
                selected_product = chosen_item
                final_validation = reval
                remaining = [
                    item
                    for item in rank_feasible_candidates(enriched_pool, top_k=len(enriched_pool))
                    if str(item["product_id"]) != chosen_id
                ]
                ordered = [chosen_item] + remaining
                for rank_idx, entry in enumerate(ordered, start=1):
                    entry["rank"] = rank_idx
                final_recommendations = ordered[:top_k]
                final_ranking = [
                    {
                        "rank": item.get("rank", idx + 1),
                        "product_id": item["product_id"],
                        "product_name": item["product_name"],
                        "weighted_score": item.get("weighted_score"),
                        "recommendation_score": item["recommendation_score"],
                        "objective_scores": item.get("objective_scores", {}),
                    }
                    for idx, item in enumerate(final_recommendations)
                ]
                decision_explanation = laya_result.get("explanation", "")
            except Exception as laya_err:
                fallback_used = True
                laya_status = "FALLBACK"
                fallback_reason = str(laya_err)

        if fallback_used:
            decision_engine_status = "FALLBACK"
            candidate_pool_ordered: List[Dict[str, Any]] = []
            try:
                if self.decision_engine.enabled:
                    decision_method = "WEIGHTED_DECISION_FALLBACK"
                    fallback_res = self.decision_engine.choose(
                        feasible_candidates,
                        express_context=express_context,
                    )
                    decision_weights = fallback_res.get("weights")
                    objective_scores = fallback_res.get("objective_scores", {})
                    candidate_pool_ordered = fallback_res.get("ranked_candidates", [])
                else:
                    raise RuntimeError(self.decision_engine.reason or "Weighted engine disabled.")
            except Exception:
                decision_method = "DETERMINISTIC_FALLBACK"
                candidate_pool_ordered = rank_feasible_candidates(
                    enriched_pool, top_k=len(enriched_pool)
                )

            validated_fallback: List[Dict[str, Any]] = []
            for cand in candidate_pool_ordered:
                pid = str(cand["product_id"])
                try:
                    reval = evaluate_product(
                        product_id=pid,
                        reward_context=reward_context,
                        promotion_context=promotion_context,
                        express_context=express_context,
                    )
                except Exception as reval_err:
                    reval = {
                        "product_id": pid,
                        "decision": "EXCLUDE",
                        "reasons": [f"Policy revalidation error: {reval_err}"],
                        "flags": [],
                    }
                if reval["decision"] == "PASS":
                    entry = dict(cand)
                    entry["rank"] = len(validated_fallback) + 1
                    validated_fallback.append(entry)
                    if selected_product is None:
                        selected_product = entry
                        final_validation = reval
                else:
                    excluded_candidates.append(
                        {
                            **cand,
                            "policy_decision": "EXCLUDE",
                            "policy_reasons": reval["reasons"],
                        }
                    )

            final_recommendations = validated_fallback[:top_k]
            final_ranking = [
                {
                    "rank": item.get("rank", idx + 1),
                    "product_id": item["product_id"],
                    "product_name": item["product_name"],
                    "weighted_score": item.get("weighted_score"),
                    "recommendation_score": item["recommendation_score"],
                    "objective_scores": item.get("objective_scores", {}),
                }
                for idx, item in enumerate(final_recommendations)
            ]
            if selected_product is not None:
                decision_explanation = (
                    f"{decision_method} selected {selected_product['product_id']} "
                    f"(recommendation_score={selected_product['recommendation_score']:.4f}) "
                    f"because Laya was unavailable or rejected: {fallback_reason}"
                )
            else:
                decision_explanation = (
                    f"No feasible candidate passed final policy revalidation during fallback ({fallback_reason})."
                )

        # Final audit invariant: ZERO excluded products may ever reach final_recommendations
        for rec in final_recommendations:
            if rec["policy_decision"] != "PASS":
                raise RuntimeError(
                    f"CRITICAL CONSTRAINT VIOLATION: Excluded product {rec['product_id']} "
                    "breached into final recommendations."
                )

        status = "SUCCESS" if final_recommendations else "ALL_CANDIDATES_EXCLUDED"

        return {
            "status": status,
            "customer_id": customer_id,
            "candidate_count": len(evaluated_candidates),
            "feasible_count": len(feasible_candidates),
            "excluded_count": len(excluded_candidates),
            "top_k_requested": top_k,
            "recommendations": final_recommendations,
            "feasible_candidates": feasible_candidates,
            "excluded_candidates": excluded_candidates,
            "all_evaluated_candidates": evaluated_candidates,
            "decision_method": decision_method,
            "laya_status": laya_status,
            "decision_engine_status": decision_engine_status,
            "laya_selected_product": laya_selected_product,
            "selected_product": selected_product,
            "decision_weights": decision_weights,
            "objective_scores": objective_scores,
            "final_ranking": final_ranking,
            "final_validation": final_validation,
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
            "decision_explanation": decision_explanation,
        }

    def _validate_customer_exists(self, customer_id: str) -> None:
        """Validate that the customer exists using the request-scoped session."""
        try:
            if self.session is not None:
                customer = CustomerRepository(self.session).get_by_id(customer_id)
                if customer is None:
                    raise ValueError(f"Customer not found: {customer_id}")
                return

            with SessionLocal() as session:
                customer = CustomerRepository(session).get_by_id(customer_id)
                if customer is None:
                    raise ValueError(f"Customer not found: {customer_id}")
        except ValueError:
            raise
        except Exception as e:
            raise RuntimeError(
                f"Database query error while checking customer {customer_id}: {e}"
            ) from e


def make_decision(
    customer_id: str,
    top_k: int = 5,
    reward_context: bool = False,
    promotion_context: bool = False,
    express_context: bool = False,
    use_decision_engine: bool = True,
) -> Dict[str, Any]:
    """Convenience function to run the decision module."""
    module = DecisionModule()
    return module.decide(
        customer_id=customer_id,
        top_k=top_k,
        reward_context=reward_context,
        promotion_context=promotion_context,
        express_context=express_context,
        use_decision_engine=use_decision_engine,
    )
