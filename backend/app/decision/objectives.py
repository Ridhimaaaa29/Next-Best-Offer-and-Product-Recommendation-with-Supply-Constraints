"""
Decision Optimization Objectives.
Defines multi-objective score aggregation (Customer Affinity vs Business Margin).
"""

from typing import Dict, Any


def compute_composite_objective(
    recommendation_score: float,
    gross_margin_pct: float,
    weight_score: float = 0.80,
    weight_margin: float = 0.20,
) -> float:
    """
    Computes weighted objective combining conversion propensity with gross margin.
    Default: 80% propensity score, 20% margin.
    """
    return round(weight_score * recommendation_score + weight_margin * gross_margin_pct, 4)
