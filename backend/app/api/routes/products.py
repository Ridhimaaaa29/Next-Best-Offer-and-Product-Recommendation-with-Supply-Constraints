"""Compatibility product detail endpoint backed by the operational catalogue."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.routes.catalogue import _catalogue_payload
from backend.app.db.models import OperationalCatalogue, Product
from backend.app.db.session import get_db

router = APIRouter(tags=["Products"])


@router.get(
    "/products/{product_id}",
    summary="Get Product Operational Details",
)
def get_product(product_id: str, db: Session = Depends(get_db)):
    row = db.execute(
        select(Product, OperationalCatalogue)
        .outerjoin(OperationalCatalogue, Product.product_id == OperationalCatalogue.product_id)
        .where(Product.product_id == product_id)
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product not found: {product_id}")
    return _catalogue_payload(row[0], row[1])
