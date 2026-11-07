"""
Deterministic Decision Module (Day 3 Step 2)
Project: Next-Best-Offer and Product Recommendation with Supply Constraints

Integrates scored recommendation candidates from `recommendation_model.py`
with the deterministic business constraints in `policy_engine.py`.

Required Flow:
Customer ID
  -> Candidate Generation
  -> Recommendation Model Scoring (Preference / Affinity / Popularity / Rating)
  -> Policy Engine Evaluation (Stock > 0, Stock not NULL, Margin >= 10%, Active, Context rules)
  -> Remove EXCLUDE Candidates (Strict Infeasibility Pruning)
  -> Sort Feasible Candidates by Score (DESC) and product_id (ASC)
  -> Select Top-K Structured Recommendations

Strict Guarantees:
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

class DecisionModule:
    """
    Deterministic Decision Engine combining recommendation scoring and policy constraints.
    """

    def __init__(
        self,
        recommender: Optional[RecommendationModel] = None,
        session: Optional[Session] = None,
    ):
        self.recommender = recommender or RecommendationModel(session=session)
        self.session = session

    def decide(
        self,
        customer_id: str,
        top_k: int = 5,
        candidate_limit: int = 20,
        reward_context: bool = False,
        promotion_context: bool = False,
        express_context: bool = False,
        injected_candidates: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Execute deterministic decision workflow for a customer.

        Args:
            customer_id: Target customer ID (e.g. 'CUST_0001').
            top_k: Number of final recommendations to return (must be > 0).
            candidate_limit: Maximum candidates to generate.
            reward_context: Whether reward redemption eligibility applies.
            promotion_context: Whether promotion eligibility applies.
            express_context: Whether 7-day express delivery applies.
            injected_candidates: Optional list of raw candidate dictionaries for testing/audit.

        Returns:
            Structured dictionary with customer_id, candidate_count, feasible_count,
            excluded_count, recommendations, and excluded_candidates.
        """
        # 1. Validation of inputs
        if not customer_id or not isinstance(customer_id, str):
            raise ValueError(f"Invalid customer_id: '{customer_id}'. Must be a non-empty string.")

        if not isinstance(top_k, int) or top_k <= 0:
            raise ValueError(f"Invalid top_k: {top_k}. Must be a positive integer.")

        # 2. Check if customer exists in database
        self._validate_customer_exists(customer_id)

        # 3. Candidate Generation & Recommendation Scoring
        # The recommendation model scores preferences and does NOT filter supply constraints
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
                "recommendations": [],
                "excluded_candidates": [],
                "message": f"No candidate products found for customer {customer_id}.",
            }

        # 4. Deterministic Policy Evaluation
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

        # 5. Deterministic Ranking of Feasible Candidates
        # Strictly sort feasible candidates by recommendation_score DESC, product_id ASC (tie-breaker)
        feasible_candidates.sort(
            key=lambda x: (-x["recommendation_score"], x["product_id"])
        )

        # 6. Select Top-K Recommendations
        final_recommendations = feasible_candidates[:top_k]

        # Audit check: Ensure ABSOLUTELY ZERO excluded products reach final_recommendations
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
            "excluded_candidates": excluded_candidates,
            "all_evaluated_candidates": evaluated_candidates,
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
) -> Dict[str, Any]:
    """Convenience function to run the deterministic decision module."""
    module = DecisionModule()
    return module.decide(
        customer_id=customer_id,
        top_k=top_k,
        reward_context=reward_context,
        promotion_context=promotion_context,
        express_context=express_context,
    )
