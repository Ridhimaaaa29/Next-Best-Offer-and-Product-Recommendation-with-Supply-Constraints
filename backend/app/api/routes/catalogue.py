"""Read-only operational catalogue endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.schemas.common import ErrorResponse
from backend.app.db.models import OperationalCatalogue, Product
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

