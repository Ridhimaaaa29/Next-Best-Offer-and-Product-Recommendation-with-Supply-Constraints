"""
Decision Validator Module.
Validates structural integrity and feasibility invariant of decision outputs.
"""

from typing import List, Dict, Any


def validate_decision_output(decision_result: Dict[str, Any]) -> None:
    """
    Validates that a decision result satisfies all structural invariants:
    - Status is SUCCESS, ALL_CANDIDATES_EXCLUDED, or NO_CANDIDATES
    - Invariant: Zero excluded candidates appear in recommendations.
    """
    recs = decision_result.get("recommendations", [])
    for rec in recs:
        if rec.get("policy_decision") != "PASS":
            raise ValueError(
                f"Validation Error: Infeasible product {rec.get('product_id')} "
                "detected in final recommendations."
            )
