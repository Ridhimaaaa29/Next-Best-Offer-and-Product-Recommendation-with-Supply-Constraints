"""
Decision Optimization Constraints.
Encapsulates hard deterministic constraints applied to candidate pools.
"""

from typing import List, Dict, Any


def filter_feasible_candidates(evaluated_candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Returns only candidates whose policy evaluation resulted in PASS.
    """
    return [c for c in evaluated_candidates if c.get("policy_decision") == "PASS"]


def extract_excluded_candidates(evaluated_candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Returns all candidates excluded by policy rules.
    """
    return [c for c in evaluated_candidates if c.get("policy_decision") != "PASS"]
