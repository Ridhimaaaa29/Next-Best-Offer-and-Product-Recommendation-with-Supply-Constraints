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


def _payload(record: Any) -> dict[str, Any]:
    return {
        "decision_id": record.decision_id,
        "customer_id": record.customer_id,
        "status": record.status,
        "candidate_products": json.loads(record.candidate_products),
        "feasible_products": json.loads(record.feasible_products),
        "excluded_products": json.loads(record.excluded_products),
        "selected_product_id": record.selected_product_id,
        "ranking_method": record.ranking_method,
        "fallback_reason": record.fallback_reason,
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
