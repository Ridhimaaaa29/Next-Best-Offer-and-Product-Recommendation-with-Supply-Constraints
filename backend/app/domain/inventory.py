"""
Domain Inventory Policy & Constraints.
RULE_STK_001 & RULE_STK_002: Available stock must be known and > 0.
"""

from typing import Optional, Tuple


def evaluate_inventory(available_stock: Optional[int]) -> Tuple[bool, Optional[str]]:
    """
    Evaluates stock constraints:
    - Known zero/negative inventory -> EXCLUDE
    - Unknown (NULL) inventory -> EXCLUDE (fail-safe)
    """
    if available_stock is None:
        return False, "Inventory availability is unknown."
    if available_stock <= 0:
        return False, "Product is out of stock."
    return True, None
