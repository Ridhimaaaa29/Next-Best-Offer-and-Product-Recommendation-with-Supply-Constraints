"""
Domain Margin Policy & Constraints.
RULE_MAR_001: Gross margin must be at least 10%.
"""

from typing import Tuple, Optional


def evaluate_margin(gross_margin_pct: float, min_margin: float = 0.10) -> Tuple[bool, Optional[str]]:
    """
    Evaluates gross profit margin:
    - Margin < 10% -> EXCLUDE
    """
    if gross_margin_pct < min_margin:
        return False, f"Gross margin ({gross_margin_pct:.2%}) is below the {min_margin:.0%} minimum."
    return True, None
