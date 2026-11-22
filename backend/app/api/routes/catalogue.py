"""Read-only operational catalogue endpoints + atomic dispatch with audit."""

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.schemas.common import ErrorResponse
from backend.app.db.models import DecisionAudit, OperationalCatalogue, Product
from backend.app.db.session import get_db

router = APIRouter(tags=["Catalogue"])


def _catalogue_payload(product: Product, operational: OperationalCatalogue | None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "product_id": product.product_id,
        "product_name": product.product_name,
        "category": product.category,
        "subcategory": product.subcategory,
        "brand": product.brand,
        "unit_price": float(product.unit_price),
        "product_rating": float(product.product_rating),
        "product_popularity": float(product.product_popularity),
        "product_status": product.product_status,
    }
    if operational is None:
        result.update(
            {
                "available_stock": None,
                "inventory_status": "unknown",
                "reorder_point": None,
                "gross_margin_pct": None,
                "supplier_lead_days": None,
                "warehouse_id": None,
                "fulfilment_class": None,
                "shipping_days": None,
                "reward_eligible": None,
                "promotion_eligible": None,
                "data_freshness_status": "unverified",
            }
        )
        return result
    result.update(
        {
            "available_stock": float(operational.available_stock) if operational.available_stock is not None else None,
            "inventory_status": operational.inventory_status,
            "reorder_point": operational.reorder_point,
            "gross_margin_pct": float(operational.gross_margin_pct),
            "supplier_lead_days": operational.supplier_lead_days,
            "warehouse_id": operational.warehouse_id,
            "fulfilment_class": operational.fulfilment_class,
            "shipping_days": operational.shipping_days,
            "reward_eligible": operational.reward_eligible,
            "promotion_eligible": operational.promotion_eligible,
            "data_freshness_status": operational.data_freshness_status,
        }
    )
    return result


@router.get("/catalogue", summary="List operational catalogue")
def list_catalogue(
    inventory_status: str | None = Query(default=None),
    product_status: str | None = Query(default=None),
    margin_below: float | None = Query(default=None, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    query = (
        select(Product, OperationalCatalogue)
        .outerjoin(OperationalCatalogue, Product.product_id == OperationalCatalogue.product_id)
        .order_by(Product.product_id)
        .limit(limit)
    )
    if product_status:
        query = query.where(Product.product_status == product_status)
    if inventory_status:
        query = query.where(OperationalCatalogue.inventory_status == inventory_status)
    if margin_below is not None:
        query = query.where(OperationalCatalogue.gross_margin_pct < margin_below)
    return [_catalogue_payload(product, operational) for product, operational in db.execute(query).all()]


@router.get(
    "/catalogue/{product_id}",
    responses={404: {"model": ErrorResponse}},
    summary="Get operational product details",
)
def get_catalogue_product(product_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    row = db.execute(
        select(Product, OperationalCatalogue)
        .outerjoin(OperationalCatalogue, Product.product_id == OperationalCatalogue.product_id)
        .where(Product.product_id == product_id)
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product not found: {product_id}")
    return _catalogue_payload(row[0], row[1])


class DispatchRequest(BaseModel):
    """Request body for atomic dispatch with optional audit creation."""

    quantity: int = Field(default=1, ge=1, le=100, description="Units to dispatch")
    # Optional audit fields — when customer_id is provided, an audit record is
    # written in the SAME transaction as the inventory deduction.
    customer_id: str | None = Field(default=None, description="Customer for whom the dispatch is made")
    ranking_method: str = Field(default="NBO_DISPATCH", description="Decision ranking method used")
    candidate_products: list[str] = Field(default_factory=list, description="All candidate product IDs considered")
    feasible_products: list[str] = Field(default_factory=list, description="Policy-feasible product IDs")
    excluded_products: list[str] = Field(default_factory=list, description="Policy-excluded product IDs")
    selected_product_id: str | None = Field(default=None, description="Selected product (may differ from dispatched)")
    decision_explanation: str | None = Field(default=None, description="Human-readable decision rationale")
    fallback_used: bool = Field(default=False, description="Whether a fallback method was used")
    fallback_reason: str | None = Field(default=None, description="Reason for fallback, if applicable")


@router.post(
    "/catalogue/{product_id}/dispatch",
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
    summary="Dispatch product and atomically deduct inventory stock with optional audit record",
)
def dispatch_product(
    product_id: str,
    body: DispatchRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Atomically deduct available_stock and optionally create a DecisionAudit record.

    Both the inventory update and the audit INSERT happen inside a single DB
    transaction protected by a row-level lock (SELECT … FOR UPDATE).  If either
    operation fails the whole transaction is rolled back — stock is never
    decremented without a corresponding audit record and vice-versa.

    If ``customer_id`` is omitted from the request body the audit record is
    skipped while the inventory deduction still executes atomically.
    """
    try:
        # ── 1. Acquire row-level lock on the operational catalogue row ──────
        op_row = db.execute(
            select(OperationalCatalogue)
            .where(OperationalCatalogue.product_id == product_id)
            .with_for_update()
        ).scalar_one_or_none()

        if op_row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product not found in operational catalogue: {product_id}",
            )

        # ── 2. Validate stock (lock is held) ─────────────────────────────────
        current_stock = float(op_row.available_stock) if op_row.available_stock is not None else 0
        if current_stock < body.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Insufficient stock for {product_id}: "
                    f"available={current_stock}, requested={body.quantity}"
                ),
            )

        # ── 3. Deduct stock and update status ─────────────────────────────────
        new_stock = current_stock - body.quantity
        op_row.available_stock = new_stock
        if new_stock <= 0:
            op_row.inventory_status = "out_of_stock"
        elif new_stock <= (op_row.reorder_point or 15):
            op_row.inventory_status = "low_stock"

        # ── 4. Optionally write audit record in the SAME session ──────────────
        decision_id: str | None = None
        if body.customer_id:
            now = datetime.now(timezone.utc)
            decision_id = str(uuid.uuid4())
            audit_row = DecisionAudit(
                decision_id=decision_id,
                customer_id=body.customer_id,
                status="DISPATCHED",
                candidate_products=json.dumps(body.candidate_products),
                feasible_products=json.dumps(body.feasible_products),
                excluded_products=json.dumps(body.excluded_products),
                selected_product_id=body.selected_product_id or product_id,
                ranking_method=body.ranking_method,
                fallback_reason=(
                    body.fallback_reason
                    if body.fallback_used
                    else (body.decision_explanation or None)
                ),
                approval_status="APPROVED",
                created_at=now,
                updated_at=now,
            )
            db.add(audit_row)

        # ── 5. Single commit — both inventory and audit land together ─────────
        db.commit()
        db.refresh(op_row)

        product_row = db.execute(
            select(Product).where(Product.product_id == product_id)
        ).scalar_one_or_none()

        return {
            "dispatched": True,
            "product_id": product_id,
            "quantity_dispatched": body.quantity,
            "stock_before": current_stock,
            "stock_after": new_stock,
            "inventory_status": op_row.inventory_status,
            "product_name": product_row.product_name if product_row else product_id,
            "decision_id": decision_id,
            "audit_created": decision_id is not None,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dispatch transaction failed: {str(exc)}",
        ) from exc
