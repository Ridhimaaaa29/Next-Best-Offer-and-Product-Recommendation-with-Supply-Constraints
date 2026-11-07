"""
Domain Feasibility Orchestrator.
Delegates to deterministic policy engine evaluations.
"""

from typing import Dict, Any, List
from backend.app.recommendation.policy_engine import evaluate_product


def check_product_feasibility(
    product_id: str,
    reward_context: bool = False,
    promotion_context: bool = False,
    express_context: bool = False,
) -> Dict[str, Any]:
    """
    Evaluates whether a product meets all operational feasibility hard constraints.
    """
    return evaluate_product(
        product_id=product_id,
        reward_context=reward_context,
        promotion_context=promotion_context,
        express_context=express_context,
    )
