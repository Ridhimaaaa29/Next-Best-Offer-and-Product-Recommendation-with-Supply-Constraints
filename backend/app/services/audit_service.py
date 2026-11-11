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
    """Service for recording and querying persisted decision governance audits."""

    def __init__(self, session: Session | None = None) -> None:
        self.session = session

    def _enrich_feasible_records(
        self,
        decision_result: dict[str, Any],
    ) -> list[dict[str, Any]]:
        recommendations = list(decision_result.get("recommendations", []) or [])
        decision_weights = decision_result.get("decision_weights")
        objective_scores_map = decision_result.get("objective_scores") or {}
        final_validation = decision_result.get("final_validation")
        fallback_used = bool(decision_result.get("fallback_used", False))
        decision_explanation = decision_result.get("decision_explanation")

        enriched: list[dict[str, Any]] = []
        for idx, item in enumerate(recommendations):
            entry = dict(item)
            pid = str(entry.get("product_id", ""))
            if "rank" not in entry or entry["rank"] is None:
                entry["rank"] = idx + 1
            if "objective_scores" not in entry or entry["objective_scores"] is None:
                entry["objective_scores"] = objective_scores_map.get(pid) or {}
            if decision_weights is not None and "decision_weights" not in entry:
                entry["decision_weights"] = decision_weights
            if final_validation is not None and idx == 0 and "final_validation" not in entry:
                entry["final_validation"] = final_validation
            entry.setdefault("fallback_used", fallback_used)
            if decision_explanation and idx == 0 and "decision_explanation" not in entry:
                entry["decision_explanation"] = decision_explanation
            enriched.append(entry)
        return enriched

    def _build_audit_record(self, decision_result: dict[str, Any]) -> DecisionAudit:
        now = datetime.now(timezone.utc)
        selected_product_id = (
            (decision_result.get("selected_product") or {}).get("product_id")
            or decision_result.get("selected_product_id")
            or (decision_result.get("recommendations") or [{}])[0].get("product_id")
        )
        ranking_method = str(
            decision_result.get("decision_method")
            or decision_result.get("ranking_method")
            or "WEIGHTED_DECISION"
        )[:100]
        fallback_reason = decision_result.get("fallback_reason")
        if fallback_reason is None and decision_result.get("fallback_used"):
            fallback_reason = "Deterministic baseline ranker fallback applied."
        approval_status = str(decision_result.get("approval_status") or "PENDING")[:30]
        feasible_records = self._enrich_feasible_records(decision_result)
        candidate_records = list(
            decision_result.get("all_evaluated_candidates")
            or decision_result.get("candidate_products")
            or []
        )
        excluded_records = list(decision_result.get("excluded_candidates") or [])

        return DecisionAudit(
            decision_id=uuid4().hex,
            customer_id=str(decision_result["customer_id"])[:50],
            status=str(decision_result.get("status") or "SUCCESS")[:50],
            candidate_products=json.dumps(candidate_records, default=str),
            feasible_products=json.dumps(feasible_records, default=str),
            excluded_products=json.dumps(excluded_records, default=str),
            selected_product_id=str(selected_product_id)[:50] if selected_product_id else None,
            ranking_method=ranking_method,
            fallback_reason=str(fallback_reason) if fallback_reason is not None else None,
            approval_status=approval_status,
            created_at=now,
            updated_at=now,
        )

    def _commit_record(self, record: DecisionAudit) -> DecisionAudit:
        if self.session is None:
            raise RuntimeError("Database session is required to persist decision audit.")
        try:
            self.session.add(record)
            self.session.commit()
            self.session.refresh(record)
            return record
        except Exception as exc:
            self.session.rollback()
            logger.error(
                "Failed to persist decision audit",
                decision_id=record.decision_id,
                customer_id=record.customer_id,
                error=str(exc),
            )
            raise

    def log_decision_audit(self, decision_result: dict[str, Any]) -> str | None:
        logger.info(
            "Decision audit recorded",
            customer_id=decision_result.get("customer_id"),
            status=decision_result.get("status"),
            feasible_count=decision_result.get("feasible_count"),
            excluded_count=decision_result.get("excluded_count"),
            decision_method=decision_result.get("decision_method"),
            fallback_used=decision_result.get("fallback_used", False),
            recommended_product_ids=[
                item.get("product_id") for item in decision_result.get("recommendations", [])
            ],
        )
        if self.session is None:
            return None
        record = self._build_audit_record(decision_result)
        self._commit_record(record)
        return record.decision_id

    def create_manual_audit(self, audit_payload: dict[str, Any]) -> DecisionAudit:
        """Persist a manual or operator-initiated decision audit entry."""
        record = self._build_audit_record(audit_payload)
        return self._commit_record(record)

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
