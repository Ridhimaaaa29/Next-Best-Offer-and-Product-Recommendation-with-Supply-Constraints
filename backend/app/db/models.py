"""
SQLAlchemy ORM Models representing the 7 Neon PostgreSQL Synthetic MVP Tables.
Project: Next-Best-Offer and Product Recommendation with Supply Constraints

Schema exactly matches the existing validated tables:
1. customers
2. products
3. transactions
4. baskets
5. customer_product_interactions
6. operational_catalogue
7. policy_rules
"""

from sqlalchemy import (
    Column,
    String,
    Integer,
    Numeric,
    Date,
    DateTime,
    Boolean,
    Text,
    ForeignKey,
    PrimaryKeyConstraint,
)
from sqlalchemy.orm import relationship
from backend.app.db.session import Base


class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(String(50), primary_key=True)
    customer_segment = Column(String(100), nullable=False)
    age_group = Column(String(50), nullable=False)
    location = Column(String(100), nullable=False)
    membership_tier = Column(String(50), nullable=False)
    reward_points = Column(Integer, nullable=False)
    preferred_category = Column(String(100), nullable=False)
    customer_status = Column(String(50), nullable=False)
    total_orders = Column(Integer, nullable=False)
    total_spend = Column(Numeric(12, 2), nullable=False)
    last_purchase_date = Column(Date, nullable=False)
    average_order_value = Column(Numeric(12, 2), nullable=False)


class Product(Base):
    __tablename__ = "products"

    product_id = Column(String(50), primary_key=True)
    product_name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    subcategory = Column(String(100), nullable=False)
    brand = Column(String(100), nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    unit_cost = Column(Numeric(12, 2), nullable=False)
    product_rating = Column(Numeric(4, 2), nullable=False)
    product_popularity = Column(Numeric(8, 4), nullable=False)
    product_status = Column(String(50), nullable=False)


class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(String(50), nullable=False)
    customer_id = Column(String(50), ForeignKey("customers.customer_id"), nullable=False)
    transaction_date = Column(DateTime, nullable=False)
    product_id = Column(String(50), ForeignKey("products.product_id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    discount_pct = Column(Numeric(6, 4), nullable=False)
    final_amount = Column(Numeric(12, 2), nullable=False)
    payment_method = Column(String(50), nullable=False)
    order_status = Column(String(50), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("transaction_id", "product_id"),
    )


class Basket(Base):
    __tablename__ = "baskets"

    basket_id = Column(String(50), nullable=False)
    transaction_id = Column(String(50), nullable=False)
    customer_id = Column(String(50), ForeignKey("customers.customer_id"), nullable=False)
    product_id = Column(String(50), ForeignKey("products.product_id"), nullable=False)
    quantity = Column(Integer, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("basket_id", "product_id"),
    )


class CustomerProductInteraction(Base):
    __tablename__ = "customer_product_interactions"

    customer_id = Column(String(50), ForeignKey("customers.customer_id"), nullable=False)
    product_id = Column(String(50), ForeignKey("products.product_id"), nullable=False)
    interaction_count = Column(Integer, nullable=False)
    last_interaction_date = Column(DateTime, nullable=False)
    purchase_frequency = Column(Integer, nullable=False)
    total_quantity = Column(Integer, nullable=False)
    total_spend = Column(Numeric(12, 2), nullable=False)
    category_preference_score = Column(Numeric(8, 4), nullable=False)
    recency_score = Column(Numeric(8, 4), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("customer_id", "product_id"),
    )


class OperationalCatalogue(Base):
    __tablename__ = "operational_catalogue"

    product_id = Column(String(50), ForeignKey("products.product_id"), primary_key=True)
    available_stock = Column(Numeric(12, 2), nullable=True)  # Nullable: None = unknown
    inventory_status = Column(String(50), nullable=False)
    reorder_point = Column(Integer, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    unit_cost = Column(Numeric(12, 2), nullable=False)
    gross_margin_pct = Column(Numeric(6, 4), nullable=False)
    supplier_id = Column(String(50), nullable=False)
    supplier_lead_days = Column(Integer, nullable=False)
    warehouse_id = Column(String(50), nullable=False)
    fulfilment_class = Column(String(50), nullable=False)
    shipping_days = Column(Integer, nullable=False)
    reward_eligible = Column(Boolean, nullable=False)
    max_discount_pct = Column(Numeric(6, 4), nullable=False)
    promotion_eligible = Column(Boolean, nullable=False)
    data_source = Column(String(100), nullable=False)
    last_updated_at = Column(DateTime, nullable=False)
    data_freshness_status = Column(String(50), nullable=False)


class PolicyRule(Base):
    __tablename__ = "policy_rules"

    rule_id = Column(String(50), primary_key=True)
    rule_name = Column(String(255), nullable=False)
    rule_type = Column(String(100), nullable=False)
    threshold = Column(Text, nullable=True)
    operator = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False)
    priority = Column(Integer, nullable=False)
    enabled = Column(Boolean, nullable=False)
    description = Column(Text, nullable=False)


class DecisionAudit(Base):
    """Persisted, read-only decision trace and business approval state."""

    __tablename__ = "decision_audits"

    decision_id = Column(String(64), primary_key=True)
    customer_id = Column(String(50), nullable=False, index=True)
    status = Column(String(50), nullable=False)
    candidate_products = Column(Text, nullable=False)
    feasible_products = Column(Text, nullable=False)
    excluded_products = Column(Text, nullable=False)
    selected_product_id = Column(String(50), nullable=True)
    ranking_method = Column(String(100), nullable=False)
    fallback_reason = Column(Text, nullable=True)
    approval_status = Column(String(30), nullable=False, default="PENDING")
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
