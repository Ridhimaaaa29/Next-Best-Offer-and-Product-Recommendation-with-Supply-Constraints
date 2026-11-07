"""Persisted decision audit service."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models import DecisionAudit
from backend.app.observability.logging import get_logger

logger = get_logger("app.services.audit")


class AuditService:
    def __init__(self, session: Session | None = None) -> None:
        self.session = session

    def log_decision_audit(self, decision_result: dict[str, Any]) -> str | None:
        logger.info(
            "Decision audit recorded",
            customer_id=decision_result.get("customer_id"),
            status=decision_result.get("status"),
            feasible_count=decision_result.get("feasible_count"),
            excluded_count=decision_result.get("excluded_count"),
            recommended_product_ids=[
                item.get("product_id") for item in decision_result.get("recommendations", [])
            ],
        )
        if self.session is None:
            return None
        now = datetime.now(timezone.utc)
        record = DecisionAudit(
            decision_id=uuid4().hex,
            customer_id=decision_result["customer_id"],
            status=decision_result["status"],
            candidate_products=json.dumps(
                decision_result.get("all_evaluated_candidates", []), default=str
            ),
            feasible_products=json.dumps(decision_result.get("recommendations", []), default=str),
            excluded_products=json.dumps(
                decision_result.get("excluded_candidates", []), default=str
            ),
            selected_product_id=(decision_result.get("recommendations") or [{}])[0].get(
                "product_id"
            ),
            ranking_method="ML propensity or deterministic heuristic",
            approval_status="PENDING",
            created_at=now,
            updated_at=now,
        )
        self.session.add(record)
        self.session.commit()
        return record.decision_id

    def list_decisions(
        self, customer_id: str | None = None, limit: int = 50
    ) -> list[DecisionAudit]:
        if self.session is None:
            return []
        query = select(DecisionAudit).order_by(DecisionAudit.created_at.desc()).limit(limit)
        if customer_id:
            query = query.where(DecisionAudit.customer_id == customer_id)
        return list(self.session.scalars(query))

    def update_approval(self, decision_id: str, approval_status: str) -> DecisionAudit | None:
        if self.session is None:
            return None
        record = self.session.get(DecisionAudit, decision_id)
        if record is None:
            return None
        record.approval_status = approval_status
        record.updated_at = datetime.now(timezone.utc)
        self.session.commit()
        return record
