"""
Decisions Standalone Router (Placeholder).
Status: NOT YET IMPLEMENTED / PLANNED FOR FUTURE ITERATION.
Decision logic is currently integrated directly via `/api/v1/recommend`.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.api.schemas.common import ErrorResponse
from backend.app.api.schemas.decision import (
    DecisionEvaluationRequest,
    DecisionEvaluationResponse,
    DecisionProductResult,
)
from backend.app.db.session import get_db
from backend.app.recommendation.policy_engine import evaluate_product
from backend.app.recommendation.decision_module import DecisionModule
from backend.app.decision.laya_adapter import LayaAdapter
from pydantic import BaseModel, Field


class LayaDecisionRequest(BaseModel):
    customer_id: str = Field(min_length=1, max_length=50)
    top_k: int = Field(default=5, ge=1, le=50)
    reward_context: bool = False
    promotion_context: bool = False
    express_context: bool = False


class LayaDecisionResponse(BaseModel):
    status: str
    laya_available: bool
    selected_product: dict | None
    feasible_candidates: list[dict]
    fallback_reason: str | None
    final_validation: dict | None

router = APIRouter(tags=["Decisions"])


@router.get("/laya/status")
def laya_status() -> dict[str, str | bool | None]:
    """Report whether the optional local Laya runtime is enabled."""
    adapter = LayaAdapter()
    return {
        "enabled": adapter.enabled,
        "available": adapter.enabled,
        "reason": adapter.reason,
    }


@router.post(
    "/decisions/evaluate",
    response_model=DecisionEvaluationResponse,
    responses={
        501: {"model": ErrorResponse, "description": "Endpoint not implemented yet"},
    },
    summary="Evaluate Arbitrary Candidates against Policy (Placeholder)",
)
def evaluate_candidates(request: DecisionEvaluationRequest):
    """
    Placeholder endpoint for standalone candidate evaluation.
    Currently, decision and policy evaluation runs synchronously in `/api/v1/recommend`.
    """
    results: list[DecisionProductResult] = []
    for product_id in request.product_ids:
        try:
            result = evaluate_product(
                product_id=product_id,
                reward_context=request.reward_context,
                promotion_context=request.promotion_context,
                express_context=request.express_context,
            )
        except ValueError as error:
            result = {
                "product_id": product_id,
                "decision": "EXCLUDE",
                "reasons": [f"Product could not be verified: {error}"],
                "flags": [],
            }
        results.append(DecisionProductResult(**result))
    return DecisionEvaluationResponse(
        customer_id=request.customer_id,
        evaluated_count=len(results),
        feasible_count=sum(item.decision == "PASS" for item in results),
        excluded_count=sum(item.decision == "EXCLUDE" for item in results),
        results=results,
    )


@router.post("/decisions/laya", response_model=LayaDecisionResponse)
def laya_decision(request: LayaDecisionRequest) -> LayaDecisionResponse:
    """Compare only policy-feasible candidates with optional Laya."""
    try:
        raw = DecisionModule().decide(
            customer_id=request.customer_id,
            top_k=request.top_k,
            reward_context=request.reward_context,
            promotion_context=request.promotion_context,
            express_context=request.express_context,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    feasible = [
        item for item in raw.get("all_evaluated_candidates", []) if item.get("policy_decision") == "PASS"
    ]
    adapter = LayaAdapter()
    fallback_reason: str | None = None
    selected: dict | None = None
    if feasible:
        try:
            selected = adapter.choose(feasible)["selected"]
        except (RuntimeError, ValueError) as error:
            fallback_reason = str(error)
            selected = sorted(
                feasible,
                key=lambda item: (-item.get("recommendation_score", 0.0), item.get("product_id", "")),
            )[0]
    if selected is not None:
        validation = evaluate_product(
            selected["product_id"],
            reward_context=request.reward_context,
            promotion_context=request.promotion_context,
            express_context=request.express_context,
        )
        if validation["decision"] != "PASS":
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Final decision failed policy revalidation.")
    else:
        validation = None
    return LayaDecisionResponse(
        status="SUCCESS" if selected else "ALL_CANDIDATES_EXCLUDED",
        laya_available=adapter.enabled,
        selected_product=selected,
        feasible_candidates=feasible,
        fallback_reason=fallback_reason,
        final_validation=validation,
    )
