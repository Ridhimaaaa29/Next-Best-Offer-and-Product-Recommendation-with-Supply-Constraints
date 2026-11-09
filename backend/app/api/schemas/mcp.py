"""
Pydantic Schemas for MCP Workflow API.
Project: Next-Best-Offer and Product Recommendation with Supply Constraints
"""

from pydantic import BaseModel, ConfigDict, Field


class MCPWorkflowRequest(BaseModel):
    customer_id: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Target customer identifier (e.g. CUST_0001)",
        examples=["CUST_0001"],
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Maximum number of recommendations to return (1-50)",
        examples=[5],
    )
    reward_context: bool = Field(
        default=False,
        description="Enforce reward eligibility policy constraint",
    )
    promotion_context: bool = Field(
        default=False,
        description="Enforce promotion eligibility policy constraint",
    )
    express_context: bool = Field(
        default=False,
        description="Enforce express shipping lead-time policy constraint",
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "customer_id": "CUST_0001",
                "top_k": 5,
                "reward_context": False,
                "promotion_context": False,
                "express_context": False,
            }
        },
    )
