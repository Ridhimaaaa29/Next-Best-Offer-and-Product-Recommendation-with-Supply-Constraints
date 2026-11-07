"""Read-only customer intelligence endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.schemas.common import ErrorResponse
from backend.app.db.models import Customer, CustomerProductInteraction, Transaction
from backend.app.db.session import get_db

router = APIRouter(tags=["Customers"])


def _json_value(value: Any) -> Any:
    return value.isoformat() if hasattr(value, "isoformat") else value


def _customer_payload(customer: Customer) -> dict[str, Any]:
    return {
        "customer_id": customer.customer_id,
        "customer_segment": customer.customer_segment,
        "age_group": customer.age_group,
        "location": customer.location,
        "membership_tier": customer.membership_tier,
        "reward_points": customer.reward_points,
        "preferred_category": customer.preferred_category,
        "customer_status": customer.customer_status,
        "total_orders": customer.total_orders,
        "total_spend": float(customer.total_spend),
        "last_purchase_date": _json_value(customer.last_purchase_date),
        "average_order_value": float(customer.average_order_value),
    }


@router.get("/customers", summary="Search customers")
def search_customers(
    search: str = Query(default="", max_length=50),
    limit: int = Query(default=25, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    query = select(Customer).order_by(Customer.customer_id).limit(limit)
    if search:
        query = query.where(Customer.customer_id.ilike(f"%{search}%"))
    return [_customer_payload(customer) for customer in db.scalars(query).all()]


@router.get(
    "/customers/{customer_id}",
    responses={404: {"model": ErrorResponse}},
    summary="Get customer intelligence",
)
def get_customer(
    customer_id: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Customer not found: {customer_id}")
    interactions = db.scalars(
        select(CustomerProductInteraction)
        .where(CustomerProductInteraction.customer_id == customer_id)
        .order_by(CustomerProductInteraction.recency_score.desc())
    ).all()
    transactions = db.scalars(
        select(Transaction)
        .where(Transaction.customer_id == customer_id)
        .order_by(Transaction.transaction_date.desc())
        .limit(25)
    ).all()
    return {
        "customer": _customer_payload(customer),
        "interactions": [
            {
                "product_id": item.product_id,
                "interaction_count": item.interaction_count,
                "last_interaction_date": _json_value(item.last_interaction_date),
                "purchase_frequency": item.purchase_frequency,
                "total_quantity": item.total_quantity,
                "total_spend": float(item.total_spend),
                "category_preference_score": float(item.category_preference_score),
                "recency_score": float(item.recency_score),
            }
            for item in interactions
        ],
        "recent_transactions": [
            {
                "transaction_id": item.transaction_id,
                "product_id": item.product_id,
                "transaction_date": _json_value(item.transaction_date),
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
                "final_amount": float(item.final_amount),
                "order_status": item.order_status,
            }
            for item in transactions
        ],
    }
