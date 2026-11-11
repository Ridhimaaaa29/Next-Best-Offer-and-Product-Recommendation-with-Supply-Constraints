"""Decisions Router — weighted multi-objective decision status and evaluation."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.api.schemas.common import ErrorResponse
from backend.app.api.schemas.decision import (
    DecisionEvaluationRequest,
    DecisionEvaluationResponse,
    DecisionProductResult,
)
from backend.app.db.session import get_db
from backend.app.decision.laya_adapter import LayaAdapter
from backend.app.recommendation.decision_module import DecisionModule
from backend.app.recommendation.policy_engine import evaluate_product
from backend.app.services.audit_service import AuditService


class DecisionOptimizationRequest(BaseModel):
    customer_id: str = Field(min_length=1, max_length=50)
    top_k: int = Field(default=5, ge=1, le=50)
    reward_context: bool = False
    promotion_context: bool = False
    express_context: bool = False


class DecisionOptimizationResponse(BaseModel):
    status: str
    decision_id: str | None = None
    laya_available: bool
    engine_available: bool
    decision_method: str
    laya_status: str | None = None
    selected_product: dict | None
    feasible_candidates: list[dict]
    decision_weights: dict[str, float] | None = None
    objective_scores: dict[str, Any] = Field(default_factory=dict)
    final_ranking: list[dict[str, Any]] = Field(default_factory=list)
    decision_explanation: str | None = None
    fallback_used: bool = False
    fallback_reason: str | None = None
    final_validation: dict | None = None


router = APIRouter(tags=["Decisions"])


@router.get("/decisions/status")
def decision_engine_status() -> dict[str, Any]:
    """Return lightweight Laya readiness and fallback configuration without loading model weights."""
    return LayaAdapter().status_info()


@router.get("/laya/status")
def legacy_decision_status() -> dict[str, Any]:
    """Lightweight Laya status check (enabled vs installed vs loaded, zero eager model init)."""
    return LayaAdapter().status_info()


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


@router.post("/decisions/optimize", response_model=DecisionOptimizationResponse)
def optimize_decision(
    request: DecisionOptimizationRequest,
    db: Session = Depends(get_db),
) -> DecisionOptimizationResponse:
    """Compare only policy-feasible candidates with Laya inference and weighted fallback."""
    adapter = LayaAdapter()
    try:
        decision_module = DecisionModule(session=db, laya_adapter=adapter)
        raw = decision_module.decide(
            customer_id=request.customer_id,
            top_k=request.top_k,
            reward_context=request.reward_context,
            promotion_context=request.promotion_context,
            express_context=request.express_context,
            use_laya=True,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Decision execution failed: {error}",
        ) from error

    try:
        audit_id = AuditService(db).log_decision_audit(raw)
    except Exception as audit_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Decision completed but audit persistence failed: {audit_err}",
        ) from audit_err

    feasible: list[dict] = raw.get("feasible_candidates") or [
        item for item in raw.get("all_evaluated_candidates", []) if item.get("policy_decision") == "PASS"
    ]

    return DecisionOptimizationResponse(
        status=raw["status"],
        decision_id=audit_id,
        laya_available=adapter.available,
        engine_available=adapter.available,
        decision_method=raw.get("decision_method", "LAYA"),
        laya_status=raw.get("laya_status"),
        selected_product=raw.get("selected_product"),
        feasible_candidates=feasible,
        decision_weights=raw.get("decision_weights"),
        objective_scores=raw.get("objective_scores", {}),
        final_ranking=raw.get("final_ranking", []),
        decision_explanation=raw.get("decision_explanation"),
        fallback_used=bool(raw.get("fallback_used", False)),
        fallback_reason=raw.get("fallback_reason"),
        final_validation=raw.get("final_validation"),
    )


@router.post("/decisions/laya", response_model=DecisionOptimizationResponse)
def laya_decision(
    request: DecisionOptimizationRequest,
    db: Session = Depends(get_db),
) -> DecisionOptimizationResponse:
    """Execute real Laya decision inference over policy-feasible candidates."""
    return optimize_decision(request=request, db=db)
