"""
Database Repositories for Direct Table Access.
Preserves existing SQLAlchemy models and Neon database mappings without changing schema.
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.db.models import (
    Customer,
    CustomerProductInteraction,
    OperationalCatalogue,
    Product,
)


class CustomerRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, customer_id: str) -> Optional[Customer]:
        return self.session.query(Customer).filter(Customer.customer_id == customer_id).first()

    def get_customer_context(self, customer_id: str) -> dict:
        customer = self.session.execute(
            select(
                Customer.customer_id,
                Customer.customer_segment,
                Customer.age_group,
                Customer.location,
                Customer.membership_tier,
                Customer.reward_points,
                Customer.preferred_category,
                Customer.customer_status,
                Customer.total_orders,
                Customer.total_spend,
                Customer.last_purchase_date,
                Customer.average_order_value,
            ).where(Customer.customer_id == customer_id)
        ).mappings().one_or_none()

        if customer is None:
            raise ValueError(f"Customer not found: {customer_id}")

        return dict(customer)

    def get_interaction_history(self, customer_id: str) -> List[dict]:
        rows = self.session.execute(
            select(
                CustomerProductInteraction.customer_id,
                CustomerProductInteraction.product_id,
                CustomerProductInteraction.interaction_count,
                CustomerProductInteraction.last_interaction_date,
                CustomerProductInteraction.purchase_frequency,
                CustomerProductInteraction.total_quantity,
                CustomerProductInteraction.total_spend,
                CustomerProductInteraction.category_preference_score,
                CustomerProductInteraction.recency_score,
            )
            .where(CustomerProductInteraction.customer_id == customer_id)
            .order_by(CustomerProductInteraction.recency_score.desc())
        ).mappings().all()

        return [dict(row) for row in rows]


class ProductRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, product_id: str) -> Optional[Product]:
        return self.session.query(Product).filter(Product.product_id == product_id).first()

    def get_by_category(self, category: str, limit: int = 50) -> List[Product]:
        return self.session.query(Product).filter(Product.category == category).limit(limit).all()

    def get_preferred_category(self, customer_id: str) -> str:
        preferred_category = self.session.execute(
            select(Customer.preferred_category).where(
                Customer.customer_id == customer_id
            )
        ).scalar_one_or_none()

        if preferred_category is None:
            raise ValueError(f"Customer not found: {customer_id}")

        return preferred_category

    def get_candidates_for_customer(
        self,
        customer_id: str,
        limit: int = 20,
    ) -> List[dict]:
        preferred_category = self.get_preferred_category(customer_id)
        interacted_product_ids = select(
            CustomerProductInteraction.product_id
        ).where(
            CustomerProductInteraction.customer_id == customer_id
        )

        rows = self.session.execute(
            select(
                Product.product_id,
                Product.product_name,
                Product.category,
                Product.subcategory,
                Product.brand,
                Product.unit_price,
                Product.product_rating,
                Product.product_popularity,
                Product.product_status,
            )
            .where(
                Product.category == preferred_category,
                Product.product_id.not_in(interacted_product_ids),
            )
            .order_by(
                Product.product_popularity.desc(),
                Product.product_rating.desc(),
            )
            .limit(limit)
        ).mappings().all()

        return [dict(row) for row in rows]


class OperationalCatalogueRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_product_id(self, product_id: str) -> Optional[OperationalCatalogue]:
        return self.session.query(OperationalCatalogue).filter(OperationalCatalogue.product_id == product_id).first()

    def get_product_policy_data(self, product_id: str) -> Optional[dict]:
        row = self.session.execute(
            select(
                Product.product_id,
                Product.product_status,
                OperationalCatalogue.available_stock,
                OperationalCatalogue.inventory_status,
                OperationalCatalogue.gross_margin_pct,
                OperationalCatalogue.shipping_days,
                OperationalCatalogue.reward_eligible,
                OperationalCatalogue.promotion_eligible,
                OperationalCatalogue.reorder_point,
                OperationalCatalogue.max_discount_pct,
                OperationalCatalogue.data_freshness_status,
            )
            .join(
                OperationalCatalogue,
                Product.product_id == OperationalCatalogue.product_id,
            )
            .where(Product.product_id == product_id)
        ).mappings().one_or_none()

        return dict(row) if row is not None else None

    def get_products_policy_map(self, product_ids: List[str]) -> dict[str, dict]:
        if not product_ids:
            return {}
        rows = self.session.execute(
            select(
                Product.product_id,
                Product.product_status,
                OperationalCatalogue.available_stock,
                OperationalCatalogue.inventory_status,
                OperationalCatalogue.gross_margin_pct,
                OperationalCatalogue.shipping_days,
                OperationalCatalogue.reward_eligible,
                OperationalCatalogue.promotion_eligible,
                OperationalCatalogue.reorder_point,
                OperationalCatalogue.max_discount_pct,
                OperationalCatalogue.data_freshness_status,
            )
            .join(
                OperationalCatalogue,
                Product.product_id == OperationalCatalogue.product_id,
            )
            .where(Product.product_id.in_(product_ids))
        ).mappings().all()

        return {str(row["product_id"]): dict(row) for row in rows}
