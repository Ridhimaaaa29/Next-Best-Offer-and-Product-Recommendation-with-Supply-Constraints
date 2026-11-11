"""
Pydantic v2 Request & Response Schemas for Recommendation API
Project: Next-Best-Offer and Product Recommendation with Supply Constraints
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from backend.app.api.schemas.common import ErrorResponse, HealthResponse


class ScoreExplanationSchema(BaseModel):
    category_affinity_score: float = Field(..., description="Category affinity score [0, 1]")
    popularity_score: float = Field(..., description="Product popularity score [0, 1]")
    rating_score: float = Field(..., description="Normalized product rating score [0, 1]")
    interaction_bonus: float = Field(..., description="Historical interaction engagement bonus [0, 1]")
    composite_score: float = Field(..., description="Final combined score [0, 1]")
    reason_codes: List[str] = Field(default_factory=list, description="Explainable reason codes")

    model_config = ConfigDict(extra="ignore")


class RecommendedProductSchema(BaseModel):
    product_id: str = Field(..., description="Unique product identifier")
    product_name: str = Field(..., description="Product name")
    category: str = Field(..., description="Product category")
    subcategory: str = Field(..., description="Product subcategory")
    brand: str = Field(..., description="Product brand")
    unit_price: float = Field(..., description="Unit price in USD")
    product_rating: float = Field(..., description="Customer rating (1-5)")
    product_popularity: float = Field(..., description="Normalized product popularity")
    product_status: str = Field(..., description="Product lifecycle status")
    recommendation_score: float = Field(..., description="Final composite / propensity score")
    policy_decision: str = Field(..., description="Policy decision: PASS")
    policy_reasons: List[str] = Field(default_factory=list, description="Policy reason codes")
    score_breakdown: ScoreExplanationSchema = Field(..., description="Detailed score component breakdown")
    objective_scores: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Normalized multi-objective scores (relevance, margin, diversity, operational_friction)",
    )
    weighted_score: Optional[float] = Field(
        default=None,
        description="Weighted composite decision score",
    )
    rank: Optional[int] = Field(default=None, description="Final decision rank (1 = top)")

    model_config = ConfigDict(extra="ignore")


class ExcludedCandidateSchema(BaseModel):
    product_id: str = Field(..., description="Unique product identifier")
    product_name: str = Field(..., description="Product name")
    category: str = Field(..., description="Product category")
    recommendation_score: float = Field(..., description="Recommendation score before exclusion")
    policy_decision: str = Field(..., description="Policy decision: EXCLUDE")
    policy_reasons: List[str] = Field(default_factory=list, description="Hard constraints that caused exclusion")

    model_config = ConfigDict(extra="ignore")


class RecommendationRequest(BaseModel):
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
    include_excluded: bool = Field(
        default=True,
        description="Include excluded candidates and their failure reasons in the response for auditability",
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
                "include_excluded": True,
            }
        },
    )


class RecommendationResponse(BaseModel):
    status: str = Field(..., description="Decision status: SUCCESS, ALL_CANDIDATES_EXCLUDED, or NO_CANDIDATES")
    customer_id: str = Field(..., description="Target customer identifier")
    decision_id: Optional[str] = Field(default=None, description="Persisted PostgreSQL DecisionAudit ID")
    candidate_count: int = Field(..., description="Total candidates generated")
    feasible_count: int = Field(..., description="Total candidates passing all policy constraints")
    excluded_count: int = Field(..., description="Total candidates excluded by policy constraints")
    decision_method: Optional[str] = Field(
        default="LAYA",
        description="Decision engine used: LAYA, WEIGHTED_DECISION_FALLBACK, DETERMINISTIC_FALLBACK, or NONE",
    )
    laya_status: Optional[str] = Field(
        default=None,
        description="Laya decision status: SUCCESS, FALLBACK, UNAVAILABLE, or SKIPPED_NO_FEASIBLE_CANDIDATES",
    )
    decision_engine_status: Optional[str] = Field(
        default=None,
        description="Execution state of the decision layer (LAYA_PRIMARY, FALLBACK, SKIPPED_*)",
    )
    decision_weights: Optional[Dict[str, float]] = Field(
        default=None,
        description="Normalized multi-objective weights used by the weighted decision engine",
    )
    objective_scores: Dict[str, Any] = Field(
        default_factory=dict,
        description="Per-product normalized objective scores",
    )
    final_ranking: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Final ranked candidate summary with weighted scores",
    )
    final_validation: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Authoritative post-selection policy revalidation result",
    )
    decision_explanation: Optional[str] = Field(
        default=None,
        description="Transparent business explanation of the selected offer",
    )
    fallback_used: bool = Field(
        default=False,
        description="True when deterministic baseline ranker fallback was invoked",
    )
    fallback_reason: Optional[str] = Field(
        default=None,
        description="Reason the deterministic fallback was used, if applicable",
    )
    recommendations: List[RecommendedProductSchema] = Field(
        default_factory=list,
        description="Ranked list of policy-feasible recommended products",
    )
    excluded_candidates: Optional[List[ExcludedCandidateSchema]] = Field(
        default=None,
        description="List of excluded candidates with constraint failure explanations",
    )

    model_config = ConfigDict(extra="ignore")
