"""Typed inputs and outputs for the MCP multi-agent decision workflow."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class CustomerInput(BaseModel):
    customer_id: str = Field(min_length=1, max_length=50)


class CustomerProfile(BaseModel):
    customer_id: str
    customer_segment: str
    age_group: str
    location: str
    membership_tier: str
    reward_points: int
    preferred_category: str
    customer_status: str
    total_orders: int
    total_spend: float
    last_purchase_date: str
    average_order_value: float


class Interaction(BaseModel):
    product_id: str
    interaction_count: int
    last_interaction_date: str
    purchase_frequency: int
    total_quantity: int
    total_spend: float
    category_preference_score: float
    recency_score: float


class CustomerContext(BaseModel):
    customer: CustomerProfile
    interactions: list[Interaction]


class PurchaseHistoryInput(CustomerInput):
    limit: int = Field(default=25, ge=1, le=100)


class PurchaseHistoryItem(BaseModel):
    transaction_id: str
    transaction_date: str
    product_id: str
    quantity: int
    final_amount: float
    order_status: str


class PurchaseHistoryOutput(BaseModel):
    customer_id: str
    transactions: list[PurchaseHistoryItem]


class ProductDetailsInput(BaseModel):
    product_id: str = Field(min_length=1, max_length=50)


class ProductDetailsOutput(BaseModel):
    product_id: str
    product_name: str
    category: str
    subcategory: str
    brand: str
    unit_price: float
    product_rating: float
    product_status: str


class EvaluationOutput(BaseModel):
    source: str
    recommendation_metrics: list[dict[str, Any]]
    ml_classification_metrics: dict[str, Any]


class RecommendationInput(BaseModel):
    customer_id: str = Field(min_length=1, max_length=50)
    limit: int = Field(default=20, ge=1, le=50)


class ScoredCandidate(BaseModel):
    product_id: str
    product_name: str
    category: str
    subcategory: str
    brand: str
    unit_price: float
    product_rating: float
    product_popularity: float
    product_status: str
    recommendation_score: float
    score_breakdown: dict[str, Any]


class RecommendationOutput(BaseModel):
    customer_id: str
    candidate_count: int
    candidates: list[ScoredCandidate]


class InventoryInput(BaseModel):
    product_id: str = Field(min_length=1, max_length=50)


class InventoryDetails(BaseModel):
    product_id: str
    product_status: str
    available_stock: float | None
    inventory_status: str | None
    gross_margin_pct: float | None
    shipping_days: int | None
    reward_eligible: bool | None
    promotion_eligible: bool | None
    reorder_point: int | None = None
    max_discount_pct: float | None = None
    data_freshness_status: str | None = None
    verification_status: Literal["verified", "missing", "failed"]
    error: str | None = None


class PolicyInput(BaseModel):
    product_id: str = Field(min_length=1, max_length=50)
    reward_context: bool = False
    promotion_context: bool = False
    express_context: bool = False


class PolicyOutput(BaseModel):
    product_id: str
    decision: Literal["PASS", "EXCLUDE"]
    reasons: list[str]
    flags: list[str]


class DecisionCandidateInput(BaseModel):
    product_id: str = Field(min_length=1, max_length=50)
    product_name: str
    recommendation_score: float
    category: str | None = None
    subcategory: str | None = None
    brand: str | None = None
    gross_margin_pct: float | None = None
    available_stock: float | None = None
    inventory_status: str | None = None
    shipping_days: int | None = None
    reorder_point: int | None = None


class FinalizeCandidate(BaseModel):
    product_id: str = Field(min_length=1, max_length=50)
    product_name: str
    recommendation_score: float
    objective_scores: dict[str, Any] | None = None
    weighted_score: float | None = None
    rank: int | None = None


class FinalizeInput(BaseModel):
    candidates: list[FinalizeCandidate] = Field(max_length=50)
    reward_context: bool = False
    promotion_context: bool = False
    express_context: bool = False


class DecisionEngineInput(BaseModel):
    candidates: list[DecisionCandidateInput] = Field(min_length=1, max_length=50)
    express_context: bool = False


class DecisionEngineOutput(BaseModel):
    status: Literal["LAYA", "FALLBACK", "WEIGHTED_DECISION"]
    selected_product_id: str
    explanation: str
    confidence: float | None = None
    weights: dict[str, float] = Field(default_factory=dict)
    objective_scores: dict[str, dict[str, Any]] = Field(default_factory=dict)
    ranked_candidates: list[dict[str, Any]] = Field(default_factory=list)
    fallback_reason: str | None = None


LayaInput = DecisionEngineInput
LayaOutput = DecisionEngineOutput


class ValidateFinalInput(PolicyInput):
    pass


class ValidateFinalOutput(PolicyOutput):
    pass


class SaveDecisionInput(FinalizeInput):
    customer_id: str = Field(min_length=1, max_length=50)


class SaveDecisionOutput(BaseModel):
    decision_id: str
    status: Literal["saved"]


class FinalRecommendation(BaseModel):
    product_id: str
    product_name: str
    recommendation_score: float
    policy_decision: Literal["PASS"]
    objective_scores: dict[str, Any] | None = None
    weighted_score: float | None = None
    rank: int | None = None


class FinalExclusion(BaseModel):
    product_id: str
    product_name: str
    recommendation_score: float
    policy_decision: Literal["EXCLUDE"]
    policy_reasons: list[str]


class FinalizeOutput(BaseModel):
    status: Literal["SUCCESS", "ALL_CANDIDATES_EXCLUDED"]
    recommendations: list[FinalRecommendation]
    excluded_candidates: list[FinalExclusion]
