"""
Decision Engine Schemas for Policy & Optimization Decisions.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class DecisionEvaluationRequest(BaseModel):
    customer_id: str = Field(..., description="Target customer identifier")
    product_ids: List[str] = Field(..., description="List of candidate product IDs to evaluate")
    reward_context: bool = Field(default=False)
    promotion_context: bool = Field(default=False)
    express_context: bool = Field(default=False)

    model_config = ConfigDict(extra="forbid")


class DecisionProductResult(BaseModel):
    product_id: str
    decision: str = Field(..., description="PASS or EXCLUDE")
    reasons: List[str] = Field(default_factory=list)
    flags: List[str] = Field(default_factory=list)


class DecisionEvaluationResponse(BaseModel):
    customer_id: str
    evaluated_count: int
    feasible_count: int
    excluded_count: int
    results: List[DecisionProductResult]
