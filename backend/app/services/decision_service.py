"""
Decision Service Orchestrator.
Wraps the DecisionModule to execute supply-constrained recommendation decisions.
"""

from typing import Dict, Any
from backend.app.recommendation.decision_module import DecisionModule


class DecisionService:
    def __init__(self):
        self.decision_module = DecisionModule()

    def decide(
        self,
        customer_id: str,
        top_k: int = 5,
        reward_context: bool = False,
        promotion_context: bool = False,
        express_context: bool = False,
    ) -> Dict[str, Any]:
        return self.decision_module.decide(
            customer_id=customer_id,
            top_k=top_k,
            reward_context=reward_context,
            promotion_context=promotion_context,
            express_context=express_context,
        )
