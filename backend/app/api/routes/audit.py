"""Decision history and approval endpoints."""

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.services.audit_service import AuditService

router = APIRouter(tags=["Decision History"])


class ApprovalRequest(BaseModel):
    approval_status: str = Field(pattern="^(APPROVED|REJECTED|PENDING)$")


class ManualAuditRequest(BaseModel):
    customer_id: str = Field(min_length=1, max_length=50)
    status: str = Field(default="SUCCESS", min_length=1, max_length=50)
    selected_product_id: str | None = Field(default=None, max_length=50)
    ranking_method: str = Field(default="MANUAL_GOVERNANCE_AUDIT", min_length=1, max_length=100)
    approval_status: str = Field(default="APPROVED", pattern="^(APPROVED|REJECTED|PENDING)$")
    candidate_products: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    excluded_candidates: list[dict[str, Any]] = Field(default_factory=list)
    decision_weights: dict[str, float] | None = None
    objective_scores: dict[str, Any] = Field(default_factory=dict)
    final_validation: dict[str, Any] | None = None
    decision_explanation: str | None = None
    fallback_used: bool = False
    fallback_reason: str | None = None


def _payload(record: Any) -> dict[str, Any]:
    feasible_products = json.loads(record.feasible_products)
    first_item = feasible_products[0] if feasible_products else {}
    objective_scores = {
        str(item["product_id"]): item.get("objective_scores")
        for item in feasible_products
        if isinstance(item, dict) and item.get("product_id") and item.get("objective_scores")
    }
    final_ranking = [
        {
            "rank": item.get("rank", idx + 1),
            "product_id": item.get("product_id"),
            "product_name": item.get("product_name"),
            "weighted_score": item.get("weighted_score"),
            "recommendation_score": item.get("recommendation_score"),
            "objective_scores": item.get("objective_scores") or {},
        }
        for idx, item in enumerate(feasible_products)
        if isinstance(item, dict)
    ]
    return {
        "decision_id": record.decision_id,
        "customer_id": record.customer_id,
        "status": record.status,
        "candidate_products": json.loads(record.candidate_products),
        "feasible_products": feasible_products,
        "excluded_products": json.loads(record.excluded_products),
        "selected_product_id": record.selected_product_id,
        "ranking_method": record.ranking_method,
        "fallback_used": bool(first_item.get("fallback_used", bool(record.fallback_reason)))
        if isinstance(first_item, dict)
        else bool(record.fallback_reason),
        "fallback_reason": record.fallback_reason,
        "configured_weights": first_item.get("decision_weights") if isinstance(first_item, dict) else None,
        "objective_scores": objective_scores,
        "final_ranking": final_ranking,
        "final_validation": first_item.get("final_validation") if isinstance(first_item, dict) else None,
        "decision_explanation": first_item.get("decision_explanation") if isinstance(first_item, dict) else None,
        "approval_status": record.approval_status,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }


@router.get("/decisions/history")
def decision_history(
    customer_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    return [_payload(record) for record in AuditService(db).list_decisions(customer_id, limit)]


@router.post("/decisions/history", status_code=status.HTTP_201_CREATED)
def create_decision_audit(
    request: ManualAuditRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Persist an operator-initiated or workflow decision audit record in PostgreSQL."""
    try:
        record = AuditService(db).create_manual_audit(request.model_dump())
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to persist decision audit record: {exc}",
        ) from exc
    return _payload(record)


@router.patch("/decisions/history/{decision_id}/approval")
def update_decision_approval(
    decision_id: str,
    request: ApprovalRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    record = AuditService(db).update_approval(decision_id, request.approval_status)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision audit not found.")
    return _payload(record)
