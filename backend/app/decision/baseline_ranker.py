"""
Baseline Ranker for Decision Optimization.
Ranks candidates deterministically using score DESC and product_id ASC tie-breaker.
"""

from typing import List, Dict, Any


def rank_feasible_candidates(feasible_candidates: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Sorts feasible candidates strictly by recommendation_score DESC, product_id ASC.
    Returns top_k recommendations.
    """
    sorted_candidates = sorted(
        feasible_candidates,
        key=lambda x: (-x.get("recommendation_score", 0.0), x.get("product_id", "")),
    )
    return sorted_candidates[:top_k]
