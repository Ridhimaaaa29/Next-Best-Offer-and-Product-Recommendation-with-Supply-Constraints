"""
Decision Optimization Objectives and Normalization Utilities.

Implements the transparent multi-objective formula over policy-feasible candidates:

    S_i = w_r * R_i + w_m * M_i + w_d * D_i - w_f * F_i

Where:
- R_i in [0, 1]: Recommendation relevance (Gradient Boosting propensity / affinity score).
- M_i in [0, 1]: Normalised gross margin contribution on the operational scale [0.10, 0.80].
- D_i in (0, 1]: Product diversity contribution based on subcategory and brand uniqueness.
- F_i in [0, 1]: Operational friction penalty from shipping lead time and low-stock risk.
- (w_r, w_m, w_d, w_f): Centrally configured weights normalised to sum to 1.0.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List


DECISION_FORMULA = "S_i = w_r * R_i + w_m * M_i + w_d * D_i - w_f * F_i"


def clamp01(value: float) -> float:
    """Clamp a numeric value into the closed unit interval [0.0, 1.0]."""
    return max(0.0, min(1.0, float(value)))


@dataclass(frozen=True)
class DecisionWeights:
    """Configurable, self-normalising multi-objective decision weights."""

    relevance: float = 0.45
    margin: float = 0.25
    diversity: float = 0.15
    friction: float = 0.15

    def normalized(self) -> Dict[str, float]:
        """Validate non-negative weights and normalise so all weights sum to 1.0."""
        raw = {
            "relevance": float(self.relevance),
            "margin": float(self.margin),
            "diversity": float(self.diversity),
            "friction": float(self.friction),
        }
        for name, val in raw.items():
            if val < 0:
                raise ValueError(f"Decision weight '{name}' cannot be negative (got {val}).")
        total = sum(raw.values())
        if total <= 0:
            raise ValueError("Sum of decision weights must be strictly positive.")
        return {name: round(val / total, 6) for name, val in raw.items()}


def normalize_relevance(recommendation_score: Any) -> float:
    """Normalise recommendation score to [0.0, 1.0]."""
    if recommendation_score is None:
        return 0.0
    return round(clamp01(float(recommendation_score)), 4)


def normalize_margin(
    gross_margin_pct: Any,
    min_margin: float = 0.10,
    max_margin: float = 0.80,
) -> float:
    """
    Normalise gross margin percentage onto [0.0, 1.0] across [min_margin, max_margin].
    Products at the 10% corporate margin floor score 0.0; >= 80% score 1.0.
    """
    if gross_margin_pct is None:
        return 0.0
    span = max(max_margin - min_margin, 1e-6)
    return round(clamp01((float(gross_margin_pct) - min_margin) / span), 4)


def compute_diversity_scores(candidates: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Compute within-pool diversity scores in (0.0, 1.0] by rewarding rarer subcategories
    and brands inside the feasible candidate set.
    """
    if not candidates:
        return {}
    subcat_counts = Counter(
        str(c.get("subcategory") or c.get("category") or "unknown").strip().lower()
        for c in candidates
    )
    brand_counts = Counter(
        str(c.get("brand") or "unknown").strip().lower()
        for c in candidates
    )

    scores: Dict[str, float] = {}
    for candidate in candidates:
        pid = str(candidate["product_id"])
        subcat = str(candidate.get("subcategory") or candidate.get("category") or "unknown").strip().lower()
        brand = str(candidate.get("brand") or "unknown").strip().lower()
        subcat_rarity = 1.0 / max(1, subcat_counts[subcat])
        brand_rarity = 1.0 / max(1, brand_counts[brand])
        scores[pid] = round(0.60 * subcat_rarity + 0.40 * brand_rarity, 4)
    return scores


def compute_operational_friction(
    candidate: Dict[str, Any],
    express_context: bool = False,
) -> tuple[float, float]:
    """
    Compute (operational_friction, operational_suitability) in [0.0, 1.0].
    Penalises longer shipping lead times and low-stock risk near reorder point.
    """
    shipping_days = candidate.get("shipping_days")
    if shipping_days is None:
        shipping_friction = 0.40
    else:
        shipping_friction = clamp01((float(shipping_days) - 1.0) / 9.0)

    stock = candidate.get("available_stock")
    reorder_point = float(candidate.get("reorder_point") or 15.0)
    inv_status = str(candidate.get("inventory_status") or "").strip().lower()

    stock_friction = 0.0
    if inv_status == "low_stock":
        stock_friction = 0.30
    elif stock is not None:
        buffer_threshold = max(reorder_point, 10.0)
        if float(stock) <= buffer_threshold:
            stock_friction = 0.30 * clamp01(1.0 - float(stock) / buffer_threshold)

    express_penalty = (
        0.20
        if express_context and shipping_days is not None and float(shipping_days) > 7
        else 0.0
    )

    friction = round(clamp01(0.75 * shipping_friction + stock_friction + express_penalty), 4)
    suitability = round(1.0 - friction, 4)
    return friction, suitability


def compute_composite_objective(
    recommendation_score: float,
    gross_margin_pct: float,
    weight_score: float = 0.80,
    weight_margin: float = 0.20,
    diversity_score: float = 0.0,
    weight_diversity: float = 0.0,
    friction_score: float = 0.0,
    weight_friction: float = 0.0,
) -> float:
    """Compute weighted objective score across normalised objectives."""
    return round(
        weight_score * recommendation_score
        + weight_margin * gross_margin_pct
        + weight_diversity * diversity_score
        - weight_friction * friction_score,
        4,
    )
