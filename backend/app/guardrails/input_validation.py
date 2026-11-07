"""
Input Validation Guardrails.
Guarantees clean, non-injected, properly bounded inputs before execution.
"""

import re
from typing import Optional


CUSTOMER_ID_REGEX = re.compile(r"^[A-Za-z0-9_-]{1,50}$")


def validate_customer_id(customer_id: str) -> str:
    """Validate customer ID matches safe alphanumeric string format."""
    if not customer_id or not isinstance(customer_id, str):
        raise ValueError("Customer ID must be a non-empty string.")
    cleaned = customer_id.strip()
    if not CUSTOMER_ID_REGEX.match(cleaned):
        raise ValueError(f"Invalid customer ID format: '{customer_id}'")
    return cleaned


def validate_top_k(top_k: int, min_val: int = 1, max_val: int = 50) -> int:
    """Validate top_k is within allowed operational limits."""
    if not isinstance(top_k, int) or top_k < min_val or top_k > max_val:
        raise ValueError(f"top_k must be an integer between {min_val} and {max_val}, got {top_k}")
    return top_k
