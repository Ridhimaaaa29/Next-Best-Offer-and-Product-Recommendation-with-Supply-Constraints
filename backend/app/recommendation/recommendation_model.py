"""
Recommendation and Scoring Component (Day 3 Step 1)
Project: Next-Best-Offer and Product Recommendation with Supply Constraints

Provides transparent, deterministic, and explainable customer-product scoring
using customer interaction signals, preferred category affinity, product popularity,
and product rating from the synthetic MVP PostgreSQL (Neon) dataset.

Strict Architectural Principles:
1. Candidate Scoring Only: Does NOT filter by operational constraints or supply feasibility.
2. Separation of Concerns: Does NOT override or bypass policy_engine.py.
3. No Target/Holdout Leakage: Uses only historical interactions and catalog statistics.
4. Explainable: Exposes individual score components and human-readable reason codes.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.db.session import get_db_context
from backend.app.recommendation.candidate_generator import generate_candidates
from backend.app.recommendation.customer_context import get_customer_context



@dataclass
class ScoreExplanation:
    """Breakdown of individual scoring factors for explainability."""
    category_affinity_score: float
    popularity_score: float
    rating_score: float
    interaction_bonus: float
    composite_score: float
    reason_codes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category_affinity_score": round(self.category_affinity_score, 4),
            "popularity_score": round(self.popularity_score, 4),
            "rating_score": round(self.rating_score, 4),
            "interaction_bonus": round(self.interaction_bonus, 4),
            "composite_score": round(self.composite_score, 4),
            "reason_codes": self.reason_codes,
        }


@dataclass
class ScoredCandidate:
    """A candidate product scored by the recommendation model."""
    product_id: str
    product_name: str
    category: str
    subcategory: str
    brand: str
    unit_price: float
    product_rating: float
    product_popularity: float
    product_status: str
    score: float
    explanation: ScoreExplanation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "category": self.category,
            "subcategory": self.subcategory,
            "brand": self.brand,
            "unit_price": round(float(self.unit_price), 2),
            "product_rating": round(float(self.product_rating), 2),
            "product_popularity": round(float(self.product_popularity), 4),
            "product_status": self.product_status,
            "score": round(self.score, 4),
            "explanation": self.explanation.to_dict(),
        }


class RecommendationModel:
    """
    Explainable Weighted Affinity Recommender.

    Computes composite score S(c, p) in [0.0, 1.0]:
        S(c, p) = w_cat * S_cat(c, p) + w_pop * S_pop(p) + w_rat * S_rat(p) + w_int * S_int(c, p)

    Weights:
        - w_cat = 0.40 (Category affinity derived from customer context)
        - w_pop = 0.30 (Normalized product popularity)
        - w_rat = 0.20 (Normalized product rating 1-5 -> 0-1)
        - w_int = 0.10 (Prior customer interaction engagement / frequency)
    """

    def __init__(
        self,
        use_ml: bool = True,
        weight_category: float = 0.40,
        weight_popularity: float = 0.30,
        weight_rating: float = 0.20,
        weight_interaction: float = 0.10,
        session: Optional[Session] = None,
    ):
        total_weight = weight_category + weight_popularity + weight_rating + weight_interaction
        if not (0.999 <= total_weight <= 1.001):
            raise ValueError(f"Weights must sum to 1.0, got {total_weight}")

        self.w_cat = weight_category
        self.w_pop = weight_popularity
        self.w_rat = weight_rating
        self.w_int = weight_interaction
        self.use_ml = use_ml
        self.session = session

        # Load ML model artifact if requested and available
        self.ml_pipeline = None
        self.ml_threshold = 0.50
        self.ml_model_name = None

        if self.use_ml:
            model_path = settings.model_artifact_path
            if model_path.exists():
                try:
                    import joblib
                    artifact = joblib.load(model_path)
                    self.ml_pipeline = artifact.get("pipeline")
                    self.ml_threshold = artifact.get("optimal_threshold", 0.50)
                    self.ml_model_name = artifact.get("model_name", "ML Model")
                except Exception:
                    self.ml_pipeline = None  # Graceful fallback to heuristic


    def score_product(
        self,
        product: Dict[str, Any],
        customer: Dict[str, Any],
        customer_interactions: List[Dict[str, Any]],
    ) -> ScoredCandidate:
        """Score a single candidate product against a specific customer context."""
        reasons = []

        # 1. Category Affinity S_cat
        candidate_category = product.get("category", "")
        preferred_category = customer.get("preferred_category", "")

        # Lookup if customer has category_preference_score in interactions for this category
        cat_scores = [
            float(i["category_preference_score"])
            for i in customer_interactions
            if i.get("category_preference_score") is not None
        ]
        avg_cat_pref = (sum(cat_scores) / len(cat_scores)) if cat_scores else 0.70

        if candidate_category == preferred_category:
            s_cat = avg_cat_pref
            reasons.append(f"Matches customer preferred category '{preferred_category}' (affinity={s_cat:.2f})")
        else:
            s_cat = avg_cat_pref * 0.30
            reasons.append(f"Cross-category discovery candidate '{candidate_category}'")

        # 2. Product Popularity S_pop
        raw_pop = product.get("product_popularity", 0.0)
        s_pop = float(raw_pop) if raw_pop is not None else 0.0
        s_pop = max(0.0, min(1.0, s_pop))
        if s_pop >= 0.80:
            reasons.append(f"High catalog popularity score ({s_pop:.2f})")

        # 3. Product Rating S_rat
        raw_rating = product.get("product_rating", 0.0)
        s_rat = (float(raw_rating) / 5.0) if raw_rating is not None else 0.0
        s_rat = max(0.0, min(1.0, s_rat))
        if s_rat >= 0.85:
            reasons.append(f"Top customer review rating ({float(raw_rating):.1f}/5.0)")

        # 4. Customer Engagement / Interaction Bonus S_int
        # Evaluate how active the customer is in general (normalized by benchmark 10 orders)
        total_orders = customer.get("total_orders", 0) or 0
        total_orders_float = float(total_orders) if isinstance(total_orders, (int, float, Decimal)) else 0.0
        s_int = min(1.0, total_orders_float / 15.0)
        if s_int >= 0.70:
            reasons.append(f"Frequent shopper bonus (lifetime orders={int(total_orders_float)})")

        # Composite score calculation (Heuristic)
        composite = (
            self.w_cat * s_cat +
            self.w_pop * s_pop +
            self.w_rat * s_rat +
            self.w_int * s_int
        )
        composite = max(0.0, min(1.0, composite))

        # Check if ML propensity pipeline is available
        final_score = composite
        if self.use_ml and self.ml_pipeline is not None:
            try:
                import pandas as pd
                # Find matching product interaction from customer_interactions
                matching_int = next((i for i in customer_interactions if i.get("product_id") == product.get("product_id")), {})
                # Prepare single-row DataFrame for pipeline
                row_dict = {
                    "reward_points": customer.get("reward_points", 0),
                    "hist_total_orders": int(total_orders_float),
                    "hist_total_spend": float(customer.get("total_spend", 0.0) or 0.0),
                    "hist_aov": float(customer.get("average_order_value", 0.0) or 0.0),
                    "unit_price": float(product.get("unit_price", 0.0)),
                    "unit_cost": float(product.get("unit_cost", 0.0) or (float(product.get("unit_price", 0.0)) * 0.6)),
                    "product_rating": float(product.get("product_rating", 0.0)),
                    "product_popularity": float(product.get("product_popularity", 0.0)),
                    "hist_product_popularity": float(product.get("product_popularity", 0.0)),
                    "hist_interaction_count": int(matching_int.get("interaction_count", 0)),
                    "hist_total_quantity": int(matching_int.get("total_quantity", 0)),
                    "hist_total_spend_interaction": float(matching_int.get("total_spend", 0.0) or 0.0),
                    "hist_recency_days": float(matching_int.get("recency_days", 365.0) if "recency_days" in matching_int else 365.0),
                    "is_preferred_category": 1 if candidate_category == preferred_category else 0,
                    "membership_tier": customer.get("membership_tier", "Standard"),
                    "category": candidate_category,
                    "subcategory": product.get("subcategory", "General"),
                }
                feature_df = pd.DataFrame([row_dict])
                prob = float(self.ml_pipeline.predict_proba(feature_df)[:, 1][0])
                final_score = prob
                reasons.append(f"ML Conversion Propensity: {prob:.4f} ({self.ml_model_name})")
            except Exception:
                final_score = composite  # Fail-safe fallback

        explanation = ScoreExplanation(
            category_affinity_score=s_cat,
            popularity_score=s_pop,
            rating_score=s_rat,
            interaction_bonus=s_int,
            composite_score=final_score,
            reason_codes=reasons,
        )

        return ScoredCandidate(
            product_id=product["product_id"],
            product_name=product["product_name"],
            category=product["category"],
            subcategory=product["subcategory"],
            brand=product["brand"],
            unit_price=float(product["unit_price"]),
            product_rating=float(product["product_rating"]),
            product_popularity=float(product["product_popularity"]),
            product_status=product["product_status"],
            score=final_score,
            explanation=explanation,
        )

    def rank_candidates(
        self,
        customer_id: str,
        candidates: Optional[List[Dict[str, Any]]] = None,
        candidate_limit: int = 20,
    ) -> List[ScoredCandidate]:
        """
        Generate (if not provided) and rank candidate products for a customer.

        Does NOT filter out operationally infeasible products; policy filtering
        is strictly performed by the downstream policy engine / decision module.
        """
        if self.session is not None:
            context = get_customer_context(customer_id, self.session)
            customer = context["customer"]
            interactions = context["interactions"]
        else:
            with get_db_context() as session:
                context = get_customer_context(customer_id, session)
                customer = context["customer"]
                interactions = context["interactions"]

        if candidates is None:
            candidates = generate_candidates(customer_id=customer_id, limit=candidate_limit)

        scored = [
            self.score_product(
                product=candidate,
                customer=customer,
                customer_interactions=interactions,
            )
            for candidate in candidates
        ]

        # Rank deterministically by composite score descending, then product_id ascending for stable ties
        scored.sort(key=lambda x: (-x.score, x.product_id))
        return scored


def score_customer_candidates(
    customer_id: str,
    limit: int = 20,
) -> Dict[str, Any]:
    """Convenience helper to retrieve context, generate candidates, and return ranked scored candidates."""
    model = RecommendationModel()
    with get_db_context() as session:
        context = get_customer_context(customer_id, session)
    customer = context["customer"]
    ranked_candidates = model.rank_candidates(customer_id=customer_id, candidate_limit=limit)

    return {
        "customer_id": customer_id,
        "preferred_category": customer["preferred_category"],
        "customer_segment": customer["customer_segment"],
        "candidate_count": len(ranked_candidates),
        "ranked_candidates": [c.to_dict() for c in ranked_candidates],
    }
