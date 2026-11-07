"""
Decision Evaluator Module.
Evaluates decision quality, constraint compliance rate, and objective values.
"""

from typing import List, Dict, Any


def evaluate_decision_quality(
    final_recommendations: List[Dict[str, Any]],
    excluded_candidates: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Computes feasibility metrics on decision results.
    """
    total = len(final_recommendations) + len(excluded_candidates)
    infeasible_in_final = sum(1 for r in final_recommendations if r.get("policy_decision") != "PASS")
    compliance_rate = 1.0 if infeasible_in_final == 0 else 0.0

    return {
        "total_evaluated": total,
        "recommended_count": len(final_recommendations),
        "excluded_count": len(excluded_candidates),
        "infeasible_in_final": infeasible_in_final,
        "policy_compliance_rate": compliance_rate,
    }
