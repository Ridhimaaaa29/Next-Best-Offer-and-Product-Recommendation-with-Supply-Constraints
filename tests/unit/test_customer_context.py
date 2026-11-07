from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.models import Customer, CustomerProductInteraction
from backend.app.db.session import Base
from backend.app.recommendation.customer_context import get_customer_context


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False)()

    session.add_all(
        [
            Customer(
                customer_id="CUST_TEST",
                customer_segment="Regular",
                age_group="25-34",
                location="Test City",
                membership_tier="Gold",
                reward_points=100,
                preferred_category="Electronics",
                customer_status="active",
                total_orders=3,
                total_spend=Decimal("120.00"),
                last_purchase_date=date(2026, 1, 15),
                average_order_value=Decimal("40.00"),
            ),
            Customer(
                customer_id="CUST_EMPTY_HISTORY",
                customer_segment="Regular",
                age_group="25-34",
                location="Test City",
                membership_tier="Standard",
                reward_points=0,
                preferred_category="Electronics",
                customer_status="active",
                total_orders=0,
                total_spend=Decimal("0.00"),
                last_purchase_date=date(2026, 1, 1),
                average_order_value=Decimal("0.00"),
            ),
        ]
    )
    session.add_all(
        [
            CustomerProductInteraction(
                customer_id="CUST_TEST",
                product_id="PROD_1",
                interaction_count=3,
                last_interaction_date=datetime(2026, 1, 10, 10, 0),
                purchase_frequency=2,
                total_quantity=4,
                total_spend=Decimal("200.00"),
                category_preference_score=Decimal("0.9000"),
                recency_score=Decimal("0.8000"),
            ),
            CustomerProductInteraction(
                customer_id="CUST_TEST",
                product_id="PROD_2",
                interaction_count=1,
                last_interaction_date=datetime(2025, 12, 20, 10, 0),
                purchase_frequency=1,
                total_quantity=1,
                total_spend=Decimal("15.00"),
                category_preference_score=Decimal("0.7000"),
                recency_score=Decimal("0.4000"),
            ),
        ]
    )
    session.commit()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_existing_customer_context_contains_expected_fields_and_types(db_session):
    context = get_customer_context("CUST_TEST", db_session)

    customer = context["customer"]
    interactions = context["interactions"]

    assert set(context) == {"customer", "interactions"}
    assert set(customer) == {
        "customer_id",
        "customer_segment",
        "age_group",
        "location",
        "membership_tier",
        "reward_points",
        "preferred_category",
        "customer_status",
        "total_orders",
        "total_spend",
        "last_purchase_date",
        "average_order_value",
    }
    assert customer["customer_id"] == "CUST_TEST"
    assert customer["total_spend"] == Decimal("120.00")
    assert customer["last_purchase_date"] == date(2026, 1, 15)
    assert customer["average_order_value"] == Decimal("40.00")
    assert isinstance(customer["customer_segment"], str)
    assert isinstance(customer["reward_points"], int)
    assert isinstance(customer["total_orders"], int)
    assert isinstance(customer["total_spend"], Decimal)
    assert isinstance(customer["last_purchase_date"], date)
    assert isinstance(customer["average_order_value"], Decimal)

    assert [item["product_id"] for item in interactions] == ["PROD_1", "PROD_2"]
    assert [item["recency_score"] for item in interactions] == [
        Decimal("0.8000"),
        Decimal("0.4000"),
    ]
    for interaction in interactions:
        assert isinstance(interaction["customer_id"], str)
        assert isinstance(interaction["product_id"], str)
        assert isinstance(interaction["interaction_count"], int)
        assert isinstance(interaction["last_interaction_date"], datetime)
        assert isinstance(interaction["purchase_frequency"], int)
        assert isinstance(interaction["total_quantity"], int)
        assert isinstance(interaction["total_spend"], Decimal)
        assert isinstance(interaction["category_preference_score"], Decimal)
        assert isinstance(interaction["recency_score"], Decimal)


def test_unknown_customer_raises_value_error(db_session):
    with pytest.raises(ValueError, match="^Customer not found: CUST_MISSING$"):
        get_customer_context("CUST_MISSING", db_session)


def test_customer_with_empty_interaction_history_returns_empty_list(db_session):
    context = get_customer_context("CUST_EMPTY_HISTORY", db_session)

    assert context["customer"]["customer_id"] == "CUST_EMPTY_HISTORY"
    assert context["interactions"] == []
