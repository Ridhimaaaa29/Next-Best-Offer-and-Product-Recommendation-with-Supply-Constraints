"""
Deterministic Decision Module with Mandatory Laya Integration (Day 3 Step 2)
Project: Next-Best-Offer and Product Recommendation with Supply Constraints

Integrates scored recommendation candidates from `recommendation_model.py`
with the deterministic business constraints in `policy_engine.py` and the
mandatory Laya decision layer from `backend.app.decision.laya_adapter`.

Required Architecture:
Customer ID
  -> Candidate Generation
  -> Recommendation Model Scoring (Preference / Affinity / Popularity / Rating)
  -> Policy Engine Evaluation (Stock > 0, Stock not NULL, Margin >= 10%, Active, Context rules)
  -> Remove EXCLUDE Candidates (Strict Infeasibility Pruning)
  -> Laya Decision Layer: Compares only policy-feasible candidate pool
  -> Policy Engine Revalidation: Selected candidate validated again before final decision
  -> Safe Failure Guarantee: Never silently report a fallback as a Laya decision
  -> Top-K Structured Output with decision provenance and audit records.

Strict Guarantees:
- Laya may select ONLY from policy-feasible candidates.
- Any candidate with policy decision == "EXCLUDE" NEVER appears in final recommendations.
- Missing operational records are safely excluded with explicit reason.
- Both final recommendations and rejected candidates are retained for full auditability.
"""

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.app.db.repositories import CustomerRepository
from backend.app.db.session import SessionLocal
from backend.app.recommendation.recommendation_model import (
    RecommendationModel,
    ScoredCandidate,
)
from backend.app.recommendation.candidate_generator import generate_candidates
from backend.app.recommendation.policy_engine import evaluate_product
from backend.app.decision.laya_adapter import LayaAdapter


class DecisionModule:
    """
    Decision Engine combining recommendation scoring, deterministic policy constraints,
    and the mandatory Laya decision layer.
    """

    def __init__(
        self,
        recommender: Optional[RecommendationModel] = None,
        session: Optional[Session] = None,
        laya_adapter: Optional[LayaAdapter] = None,
    ):
        self.recommender = recommender or RecommendationModel(session=session)
        self.session = session
        self.laya_adapter = laya_adapter if laya_adapter is not None else LayaAdapter()

    def decide(
        self,
        customer_id: str,
        top_k: int = 5,
        candidate_limit: int = 20,
        reward_context: bool = False,
        promotion_context: bool = False,
        express_context: bool = False,
        injected_candidates: Optional[List[Dict[str, Any]]] = None,
        use_laya: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute decision workflow for a customer.

        Args:
            customer_id: Target customer ID (e.g. 'CUST_0001').
            top_k: Number of final recommendations to return (must be > 0).
            candidate_limit: Maximum candidates to generate.
            reward_context: Whether reward redemption eligibility applies.
            promotion_context: Whether promotion eligibility applies.
            express_context: Whether 7-day express delivery applies.
            injected_candidates: Optional list of raw candidate dictionaries for testing/audit.
            use_laya: Whether to invoke the Laya decision layer on feasible candidates.

        Returns:
            Structured dictionary with customer_id, candidate_count, feasible_count,
            excluded_count, recommendations, excluded_candidates, decision_method, and laya status.
        """
        # 1. Validation of inputs
        if not customer_id or not isinstance(customer_id, str):
            raise ValueError(f"Invalid customer_id: '{customer_id}'. Must be a non-empty string.")

        if not isinstance(top_k, int) or top_k <= 0:
            raise ValueError(f"Invalid top_k: {top_k}. Must be a positive integer.")

        # Mandatory Laya guard: Laya cannot be bypassed in the primary recommendation path
        if not use_laya:
            raise ValueError(
                "Laya decision layer is mandatory for recommendations and cannot be bypassed by setting use_laya=False."
            )

        # 2. Check if customer exists in database
        self._validate_customer_exists(customer_id)

        # 3. Candidate Generation & Recommendation Scoring
        try:
            scored_candidates: List[ScoredCandidate] = self.recommender.rank_candidates(
                customer_id=customer_id,
                candidates=injected_candidates,
                candidate_limit=candidate_limit,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to generate and score candidates for {customer_id}: {e}") from e

        # Handle case where customer has no candidates
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
                "laya_status": "SKIPPED_NO_CANDIDATES",
                "laya_selected_product": None,
                "laya_revalidation": None,
                "laya_fallback_reason": None,
                "message": f"No candidate products found for customer {customer_id}.",
            }

        # 4. Deterministic Policy Evaluation (Authoritative Pre-Filter)
        evaluated_candidates = []
        feasible_candidates = []
        excluded_candidates = []

        for candidate in scored_candidates:
            cand_dict = candidate.to_dict()
            prod_id = candidate.product_id

            try:
                policy_eval = evaluate_product(
                    product_id=prod_id,
                    reward_context=reward_context,
                    promotion_context=promotion_context,
                    express_context=express_context,
                )
            except ValueError as ve:
                # Missing operational catalogue record fail-safe: mark as EXCLUDE
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
            }

            evaluated_candidates.append(item_summary)

            if policy_eval["decision"] == "PASS":
                feasible_candidates.append(item_summary)
            else:
                excluded_candidates.append(item_summary)

        # Handle case where all candidates failed policy constraints
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
                "laya_selected_product": None,
                "laya_revalidation": None,
                "laya_fallback_reason": None,
            }

        # 5. Mandatory Laya Decision Layer Invocation
        # Laya compares already policy-feasible candidates to select the Next-Best-Offer.
        laya_selected_product: Optional[Dict[str, Any]] = None
        laya_revalidation: Optional[Dict[str, Any]] = None
        laya_status: str = "DISABLED"
        laya_fallback_reason: Optional[str] = None
        decision_method: str = "DETERMINISTIC"

        if use_laya:
            try:
                # Laya may select ONLY from already policy-feasible candidates
                laya_result = self.laya_adapter.choose(feasible_candidates)
                candidate_chosen = laya_result["selected"]

                # 6. Revalidation: Deterministic policy engine is strictly authoritative!
                # Selected product must be revalidated against policy constraints.
                reval = evaluate_product(
                    product_id=candidate_chosen["product_id"],
                    reward_context=reward_context,
                    promotion_context=promotion_context,
                    express_context=express_context,
                )
                laya_revalidation = reval

                if reval["decision"] != "PASS":
                    # Infeasible selection rejected by authoritative policy engine
                    laya_status = "REVALIDATION_FAILED"
                    laya_fallback_reason = (
                        f"Laya selected product {candidate_chosen['product_id']} failed "
                        f"authoritative policy revalidation: {', '.join(reval['reasons'])}"
                    )
                    status = "LAYA_SELECTION_INFEASIBLE"
                    decision_method = "POLICY_REJECTED"

                    infeasible_item = {
                        **candidate_chosen,
                        "policy_decision": "EXCLUDE",
                        "policy_reasons": reval["reasons"],
                    }
                    return {
                        "status": status,
                        "customer_id": customer_id,
                        "candidate_count": len(evaluated_candidates),
                        "feasible_count": len(feasible_candidates),
                        "excluded_count": len(excluded_candidates) + 1,
                        "top_k_requested": top_k,
                        "recommendations": [],
                        "feasible_candidates": feasible_candidates,
                        "excluded_candidates": excluded_candidates + [infeasible_item],
                        "all_evaluated_candidates": evaluated_candidates,
                        "decision_method": decision_method,
                        "laya_status": laya_status,
                        "laya_selected_product": None,
                        "laya_revalidation": laya_revalidation,
                        "laya_fallback_reason": laya_fallback_reason,
                    }

                # Laya selection passed authoritative revalidation
                laya_selected_product = candidate_chosen
                laya_status = "SUCCESS"
                decision_method = "LAYA"

            except ValueError as ve:
                # Malformed output from Laya
                laya_status = "MALFORMED_OUTPUT"
                laya_fallback_reason = f"Laya returned malformed output: {ve}"
                status = "LAYA_FAILED"
                decision_method = "FAILED"
                return {
                    "status": status,
                    "customer_id": customer_id,
                    "candidate_count": len(evaluated_candidates),
                    "feasible_count": len(feasible_candidates),
                    "excluded_count": len(excluded_candidates),
                    "top_k_requested": top_k,
                    "recommendations": [],
                    "feasible_candidates": feasible_candidates,
                    "excluded_candidates": excluded_candidates,
                    "all_evaluated_candidates": evaluated_candidates,
                    "decision_method": decision_method,
                    "laya_status": laya_status,
                    "laya_selected_product": None,
                    "laya_revalidation": None,
                    "laya_fallback_reason": laya_fallback_reason,
                }
            except RuntimeError as re:
                # Laya unavailable (disabled, uninstalled, or router runtime failure)
                laya_status = "UNAVAILABLE"
                laya_fallback_reason = str(re)
                status = "LAYA_UNAVAILABLE"
                decision_method = "FAILED"
                return {
                    "status": status,
                    "customer_id": customer_id,
                    "candidate_count": len(evaluated_candidates),
                    "feasible_count": len(feasible_candidates),
                    "excluded_count": len(excluded_candidates),
                    "top_k_requested": top_k,
                    "recommendations": [],
                    "feasible_candidates": feasible_candidates,
                    "excluded_candidates": excluded_candidates,
                    "all_evaluated_candidates": evaluated_candidates,
                    "decision_method": decision_method,
                    "laya_status": laya_status,
                    "laya_selected_product": None,
                    "laya_revalidation": None,
                    "laya_fallback_reason": laya_fallback_reason,
                }

        # 7. Final Recommendation Assembly
        if laya_selected_product is not None:
            # Place Laya-selected offer at index 0 (Next-Best-Offer)
            remaining_feasible = [
                c for c in feasible_candidates
                if c["product_id"] != laya_selected_product["product_id"]
            ]
            remaining_feasible.sort(
                key=lambda x: (-x["recommendation_score"], x["product_id"])
            )
            final_recommendations = [laya_selected_product] + remaining_feasible[: top_k - 1]
        else:
            # Pure deterministic ranking
            feasible_candidates.sort(
                key=lambda x: (-x["recommendation_score"], x["product_id"])
            )
            final_recommendations = feasible_candidates[:top_k]
            decision_method = "DETERMINISTIC"

        # Final audit check: Ensure ABSOLUTELY ZERO excluded products reach final_recommendations
        for rec in final_recommendations:
            if rec["policy_decision"] != "PASS":
                raise RuntimeError(
                    f"CRITICAL CONSTRAINT VIOLATION: Excluded product {rec['product_id']} "
                    f"breached into final recommendations."
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
            "laya_selected_product": laya_selected_product,
            "laya_revalidation": laya_revalidation,
            "laya_fallback_reason": laya_fallback_reason,
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
    use_laya: bool = True,
) -> Dict[str, Any]:
    """Convenience function to run the decision module."""
    module = DecisionModule()
    return module.decide(
        customer_id=customer_id,
        top_k=top_k,
        reward_context=reward_context,
        promotion_context=promotion_context,
        express_context=express_context,
        use_laya=use_laya,
    )
