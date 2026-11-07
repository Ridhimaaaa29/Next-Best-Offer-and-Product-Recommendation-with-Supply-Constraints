"""
Security & Credential Masking Configuration.
Ensures secrets like DATABASE_URL, passwords, and tokens are never logged or leaked.
"""

import re
from typing import Optional


SECRET_URL_PATTERN = re.compile(r"://([^:]+):([^@]+)@")


def mask_connection_string(conn_str: Optional[str]) -> str:
    """Mask credentials in database URLs (e.g. postgresql://user:***@host:port/db)."""
    if not conn_str:
        return ""
    return SECRET_URL_PATTERN.sub(r"://\1:***@", conn_str)
