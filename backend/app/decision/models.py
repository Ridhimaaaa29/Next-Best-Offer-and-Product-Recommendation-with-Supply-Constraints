"""
Decision Engine Data Models & Container Classes.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class DecisionContext:
    customer_id: str
    top_k: int = 5
    reward_context: bool = False
    promotion_context: bool = False
    express_context: bool = False


@dataclass
class EvaluatedCandidate:
    product_id: str
    product_name: str
    category: str
    unit_price: float
    recommendation_score: float
    policy_decision: str
    policy_reasons: List[str] = field(default_factory=list)
    policy_flags: List[str] = field(default_factory=list)
    score_explanation: Dict[str, Any] = field(default_factory=dict)
