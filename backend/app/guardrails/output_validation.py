"""
Output Validation Guardrails.
Enforces the strict invariant: No infeasible or excluded candidate can ever be returned.
"""

from typing import Any, Dict, List


def validate_final_recommendations(recommendations: List[Dict[str, Any]]) -> None:
    """
    Enforces the zero-defect policy guarantee on final recommendation outputs.
    Raises RuntimeError if any recommended item fails the policy decision.
    """
    for rec in recommendations:
        decision = rec.get("policy_decision")
        if decision != "PASS":
            prod_id = rec.get("product_id", "UNKNOWN")
            raise RuntimeError(
                f"GUARDRAIL BREACH: Excluded product '{prod_id}' "
                f"(decision='{decision}') detected in final recommendations."
            )
