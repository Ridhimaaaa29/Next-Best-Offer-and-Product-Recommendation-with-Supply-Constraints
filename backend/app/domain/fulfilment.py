"""
Domain Fulfillment & Lead Time Policy.
RULE_FUL_001: Express shipping context threshold (<= 7 days).
"""

from typing import Tuple, Optional


def evaluate_fulfilment(shipping_days: int, express_context: bool, max_express_days: int = 7) -> Tuple[bool, Optional[str]]:
    """
    Evaluates shipping lead time:
    In express context, shipping > 7 days generates an operational flag.
    """
    if express_context and shipping_days > max_express_days:
        return False, f"Shipping time ({shipping_days} days) exceeds the {max_express_days}-day express threshold."
    return True, None
