"""
Domain Eligibility Policy & Constraints.
RULE_REW_001 & RULE_PRO_001: Context-specific reward & promotion rules.
"""

from typing import Tuple, Optional


def evaluate_reward_eligibility(reward_eligible: bool, reward_context: bool) -> Tuple[bool, Optional[str]]:
    if reward_context and not reward_eligible:
        return False, "Product is not reward eligible."
    return True, None


def evaluate_promotion_eligibility(promotion_eligible: bool, promotion_context: bool) -> Tuple[bool, Optional[str]]:
    if promotion_context and not promotion_eligible:
        return False, "Product is not promotion eligible."
    return True, None
