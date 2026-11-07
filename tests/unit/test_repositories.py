from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.models import (
    Customer,
    CustomerProductInteraction,
    OperationalCatalogue,
    Product,
)
from backend.app.db.repositories import (
    CustomerRepository,
    OperationalCatalogueRepository,
    ProductRepository,
)
from backend.app.db.session import Base


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False)()

    session.add(
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
        )
    )
    session.add(
        Customer(
            customer_id="CUST_NO_CANDIDATES",
            customer_segment="Regular",
            age_group="25-34",
            location="Test City",
            membership_tier="Standard",
            reward_points=0,
            preferred_category="Garden",
            customer_status="active",
            total_orders=0,
            total_spend=Decimal("0.00"),
            last_purchase_date=date(2026, 1, 1),
            average_order_value=Decimal("0.00"),
        )
    )
    session.add_all(
        [
            Product(
                product_id="PROD_ELECTRONICS_1",
                product_name="Test Speaker",
                category="Electronics",
                subcategory="Audio",
                brand="TestBrand",
                unit_price=Decimal("50.00"),
                unit_cost=Decimal("30.00"),
                product_rating=Decimal("4.50"),
                product_popularity=Decimal("0.9000"),
                product_status="active",
            ),
            Product(
                product_id="PROD_ELECTRONICS_2",
                product_name="Test Cable",
                category="Electronics",
                subcategory="Accessories",
                brand="TestBrand",
                unit_price=Decimal("15.00"),
                unit_cost=Decimal("8.00"),
                product_rating=Decimal("4.00"),
                product_popularity=Decimal("0.7000"),
                product_status="active",
            ),
            Product(
                product_id="PROD_ELECTRONICS_3",
                product_name="Test Charger",
                category="Electronics",
                subcategory="Accessories",
                brand="OtherBrand",
                unit_price=Decimal("25.00"),
                unit_cost=Decimal("12.00"),
                product_rating=Decimal("4.20"),
                product_popularity=Decimal("0.6000"),
                product_status="active",
            ),
            Product(
                product_id="PROD_ELECTRONICS_4",
                product_name="Test Power Bank",
                category="Electronics",
                subcategory="Accessories",
                brand="OtherBrand",
                unit_price=Decimal("30.00"),
                unit_cost=Decimal("14.00"),
                product_rating=Decimal("4.80"),
                product_popularity=Decimal("0.6000"),
                product_status="active",
            ),
            Product(
                product_id="PROD_ELECTRONICS_5",
                product_name="Test Adapter",
                category="Electronics",
                subcategory="Accessories",
                brand="OtherBrand",
                unit_price=Decimal("18.00"),
                unit_cost=Decimal("9.00"),
                product_rating=Decimal("4.90"),
                product_popularity=Decimal("0.5000"),
                product_status="active",
            ),
            Product(
                product_id="PROD_HOME_1",
                product_name="Test Organizer",
                category="Home & Living",
                subcategory="Organization",
                brand="HomeBrand",
                unit_price=Decimal("20.00"),
                unit_cost=Decimal("10.00"),
                product_rating=Decimal("4.10"),
                product_popularity=Decimal("0.8000"),
                product_status="active",
            ),
        ]
    )
    session.add_all(
        [
            CustomerProductInteraction(
                customer_id="CUST_TEST",
                product_id="PROD_ELECTRONICS_1",
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
                product_id="PROD_ELECTRONICS_2",
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
    session.add(
        OperationalCatalogue(
            product_id="PROD_ELECTRONICS_1",
            available_stock=Decimal("10.00"),
            inventory_status="available",
            reorder_point=2,
            unit_price=Decimal("50.00"),
            unit_cost=Decimal("30.00"),
            gross_margin_pct=Decimal("0.4000"),
            supplier_id="SUPPLIER_TEST",
            supplier_lead_days=3,
            warehouse_id="WAREHOUSE_TEST",
            fulfilment_class="standard",
            shipping_days=4,
            reward_eligible=True,
            max_discount_pct=Decimal("0.1000"),
            promotion_eligible=True,
            data_source="test",
            last_updated_at=datetime(2026, 1, 15, 12, 0),
            data_freshness_status="current",
        )
    )
    session.add(
        OperationalCatalogue(
            product_id="PROD_ELECTRONICS_3",
            available_stock=None,
            inventory_status="unknown",
            reorder_point=2,
            unit_price=Decimal("25.00"),
            unit_cost=Decimal("12.00"),
            gross_margin_pct=Decimal("0.5200"),
            supplier_id="SUPPLIER_TEST",
            supplier_lead_days=3,
            warehouse_id="WAREHOUSE_TEST",
            fulfilment_class="standard",
            shipping_days=4,
            reward_eligible=False,
            max_discount_pct=Decimal("0.1000"),
            promotion_eligible=False,
            data_source="test",
            last_updated_at=datetime(2026, 1, 15, 12, 0),
            data_freshness_status="current",
        )
    )
    session.commit()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_customer_repository_get_by_id_returns_existing_customer(db_session):
    customer = CustomerRepository(db_session).get_by_id("CUST_TEST")

    assert isinstance(customer, Customer)
    assert customer.customer_id == "CUST_TEST"
    assert customer.preferred_category == "Electronics"
    assert customer.total_spend == Decimal("120.00")


def test_customer_repository_get_by_id_returns_none_for_missing_customer(db_session):
    assert CustomerRepository(db_session).get_by_id("CUST_MISSING") is None


def test_customer_repository_get_customer_context_preserves_contract(db_session):
    context = CustomerRepository(db_session).get_customer_context("CUST_TEST")

    assert set(context) == {
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
    assert context["customer_id"] == "CUST_TEST"
    assert context["customer_segment"] == "Regular"
    assert context["age_group"] == "25-34"
    assert context["location"] == "Test City"
    assert context["membership_tier"] == "Gold"
    assert context["reward_points"] == 100
    assert context["preferred_category"] == "Electronics"
    assert context["customer_status"] == "active"
    assert context["total_orders"] == 3
    assert context["total_spend"] == Decimal("120.00")
    assert context["last_purchase_date"] == date(2026, 1, 15)
    assert context["average_order_value"] == Decimal("40.00")
    assert isinstance(context["total_spend"], Decimal)
    assert isinstance(context["last_purchase_date"], date)
    assert isinstance(context["average_order_value"], Decimal)


def test_customer_repository_get_customer_context_raises_for_missing_customer(
    db_session,
):
    with pytest.raises(ValueError, match="^Customer not found: CUST_MISSING$"):
        CustomerRepository(db_session).get_customer_context("CUST_MISSING")


def test_customer_repository_get_interaction_history_orders_by_recency(
    db_session,
):
    interactions = CustomerRepository(db_session).get_interaction_history(
        "CUST_TEST"
    )

    assert len(interactions) == 2
    expected_fields = {
        "customer_id",
        "product_id",
        "interaction_count",
        "last_interaction_date",
        "purchase_frequency",
        "total_quantity",
        "total_spend",
        "category_preference_score",
        "recency_score",
    }
    assert all(set(interaction) == expected_fields for interaction in interactions)

    first, second = interactions
    assert first["customer_id"] == "CUST_TEST"
    assert first["product_id"] == "PROD_ELECTRONICS_1"
    assert first["interaction_count"] == 3
    assert first["last_interaction_date"] == datetime(2026, 1, 10, 10, 0)
    assert first["purchase_frequency"] == 2
    assert first["total_quantity"] == 4
    assert first["total_spend"] == Decimal("200.00")
    assert first["category_preference_score"] == Decimal("0.9000")
    assert first["recency_score"] == Decimal("0.8000")

    assert second["customer_id"] == "CUST_TEST"
    assert second["product_id"] == "PROD_ELECTRONICS_2"
    assert second["interaction_count"] == 1
    assert second["last_interaction_date"] == datetime(2025, 12, 20, 10, 0)
    assert second["purchase_frequency"] == 1
    assert second["total_quantity"] == 1
    assert second["total_spend"] == Decimal("15.00")
    assert second["category_preference_score"] == Decimal("0.7000")
    assert second["recency_score"] == Decimal("0.4000")

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

    assert [interaction["recency_score"] for interaction in interactions] == [
        Decimal("0.8000"),
        Decimal("0.4000"),
    ]


def test_customer_repository_get_interaction_history_returns_empty_for_no_history(
    db_session,
):
    assert (
        CustomerRepository(db_session).get_interaction_history("CUST_NO_HISTORY")
        == []
    )


def test_product_repository_get_by_id_returns_existing_product(db_session):
    product = ProductRepository(db_session).get_by_id("PROD_ELECTRONICS_1")

    assert isinstance(product, Product)
    assert product.product_id == "PROD_ELECTRONICS_1"
    assert product.category == "Electronics"
    assert product.product_rating == Decimal("4.50")


def test_product_repository_get_by_id_returns_none_for_missing_product(db_session):
    assert ProductRepository(db_session).get_by_id("PROD_MISSING") is None


def test_product_repository_get_by_category_filters_products(db_session):
    products = ProductRepository(db_session).get_by_category(
        "Electronics",
        limit=10,
    )

    assert len(products) == 5
    assert all(product.category == "Electronics" for product in products)


def test_product_repository_get_by_category_applies_limit(db_session):
    products = ProductRepository(db_session).get_by_category(
        "Electronics",
        limit=2,
    )

    assert len(products) == 2
    assert all(product.category == "Electronics" for product in products)


def test_product_repository_get_by_category_returns_empty_for_unknown_category(
    db_session,
):
    assert ProductRepository(db_session).get_by_category("Unknown", limit=10) == []


def test_product_repository_get_preferred_category_returns_existing_value(
    db_session,
):
    category = ProductRepository(db_session).get_preferred_category("CUST_TEST")

    assert category == "Electronics"
    assert isinstance(category, str)


def test_product_repository_get_preferred_category_raises_for_missing_customer(
    db_session,
):
    with pytest.raises(ValueError, match="^Customer not found: CUST_MISSING$"):
        ProductRepository(db_session).get_preferred_category("CUST_MISSING")


def test_product_repository_get_candidates_filters_category_and_interactions(
    db_session,
):
    candidates = ProductRepository(db_session).get_candidates_for_customer(
        "CUST_TEST"
    )

    assert candidates == [
        {
            "product_id": "PROD_ELECTRONICS_4",
            "product_name": "Test Power Bank",
            "category": "Electronics",
            "subcategory": "Accessories",
            "brand": "OtherBrand",
            "unit_price": Decimal("30.00"),
            "product_rating": Decimal("4.80"),
            "product_popularity": Decimal("0.6000"),
            "product_status": "active",
        },
        {
            "product_id": "PROD_ELECTRONICS_3",
            "product_name": "Test Charger",
            "category": "Electronics",
            "subcategory": "Accessories",
            "brand": "OtherBrand",
            "unit_price": Decimal("25.00"),
            "product_rating": Decimal("4.20"),
            "product_popularity": Decimal("0.6000"),
            "product_status": "active",
        },
        {
            "product_id": "PROD_ELECTRONICS_5",
            "product_name": "Test Adapter",
            "category": "Electronics",
            "subcategory": "Accessories",
            "brand": "OtherBrand",
            "unit_price": Decimal("18.00"),
            "product_rating": Decimal("4.90"),
            "product_popularity": Decimal("0.5000"),
            "product_status": "active",
        },
    ]
    assert all(candidate["category"] == "Electronics" for candidate in candidates)
    assert {
        candidate["product_id"] for candidate in candidates
    }.isdisjoint(
        {"PROD_ELECTRONICS_1", "PROD_ELECTRONICS_2"}
    )
    assert all(
        set(candidate)
        == {
            "product_id",
            "product_name",
            "category",
            "subcategory",
            "brand",
            "unit_price",
            "product_rating",
            "product_popularity",
            "product_status",
        }
        for candidate in candidates
    )
    for candidate in candidates:
        assert isinstance(candidate["product_id"], str)
        assert isinstance(candidate["product_name"], str)
        assert isinstance(candidate["category"], str)
        assert isinstance(candidate["subcategory"], str)
        assert isinstance(candidate["brand"], str)
        assert isinstance(candidate["unit_price"], Decimal)
        assert isinstance(candidate["product_rating"], Decimal)
        assert isinstance(candidate["product_popularity"], Decimal)
        assert isinstance(candidate["product_status"], str)


def test_product_repository_get_candidates_orders_by_popularity_descending(
    db_session,
):
    candidates = ProductRepository(db_session).get_candidates_for_customer(
        "CUST_TEST"
    )

    assert [candidate["product_id"] for candidate in candidates] == [
        "PROD_ELECTRONICS_4",
        "PROD_ELECTRONICS_3",
        "PROD_ELECTRONICS_5",
    ]
    popularities = [candidate["product_popularity"] for candidate in candidates]
    assert popularities == sorted(popularities, reverse=True)


def test_product_repository_get_candidates_orders_equal_popularity_by_rating(
    db_session,
):
    candidates = ProductRepository(db_session).get_candidates_for_customer(
        "CUST_TEST"
    )
    tied = [
        candidate
        for candidate in candidates
        if candidate["product_popularity"] == Decimal("0.6000")
    ]

    assert [candidate["product_id"] for candidate in tied] == [
        "PROD_ELECTRONICS_4",
        "PROD_ELECTRONICS_3",
    ]
    assert [candidate["product_rating"] for candidate in tied] == [
        Decimal("4.80"),
        Decimal("4.20"),
    ]


def test_product_repository_get_candidates_applies_limit(db_session):
    candidates = ProductRepository(db_session).get_candidates_for_customer(
        "CUST_TEST",
        limit=2,
    )

    assert len(candidates) == 2
    assert [candidate["product_id"] for candidate in candidates] == [
        "PROD_ELECTRONICS_4",
        "PROD_ELECTRONICS_3",
    ]


def test_product_repository_get_candidates_returns_empty_for_no_matches(
    db_session,
):
    assert (
        ProductRepository(db_session).get_candidates_for_customer(
            "CUST_NO_CANDIDATES"
        )
        == []
    )


def test_product_repository_get_candidates_raises_for_missing_customer(
    db_session,
):
    with pytest.raises(ValueError, match="^Customer not found: CUST_MISSING$"):
        ProductRepository(db_session).get_candidates_for_customer("CUST_MISSING")


def test_operational_catalogue_repository_get_by_product_id_returns_record(
    db_session,
):
    catalogue = OperationalCatalogueRepository(db_session).get_by_product_id(
        "PROD_ELECTRONICS_1"
    )

    assert isinstance(catalogue, OperationalCatalogue)
    assert catalogue.product_id == "PROD_ELECTRONICS_1"
    assert catalogue.available_stock == Decimal("10.00")
    assert catalogue.reward_eligible is True


def test_operational_catalogue_repository_get_by_product_id_returns_none_for_missing(
    db_session,
):
    assert (
        OperationalCatalogueRepository(db_session).get_by_product_id("PROD_MISSING")
        is None
    )


def test_operational_catalogue_repository_get_product_policy_data_returns_all_fields(
    db_session,
):
    policy_data = OperationalCatalogueRepository(
        db_session
    ).get_product_policy_data("PROD_ELECTRONICS_1")

    assert policy_data == {
        "product_id": "PROD_ELECTRONICS_1",
        "product_status": "active",
        "available_stock": Decimal("10.00"),
        "inventory_status": "available",
        "gross_margin_pct": Decimal("0.4000"),
        "shipping_days": 4,
        "reward_eligible": True,
        "promotion_eligible": True,
    }
    assert set(policy_data) == {
        "product_id",
        "product_status",
        "available_stock",
        "inventory_status",
        "gross_margin_pct",
        "shipping_days",
        "reward_eligible",
        "promotion_eligible",
    }
    assert isinstance(policy_data["product_id"], str)
    assert isinstance(policy_data["product_status"], str)
    assert isinstance(policy_data["available_stock"], Decimal)
    assert isinstance(policy_data["inventory_status"], str)
    assert isinstance(policy_data["gross_margin_pct"], Decimal)
    assert isinstance(policy_data["shipping_days"], int)
    assert isinstance(policy_data["reward_eligible"], bool)
    assert isinstance(policy_data["promotion_eligible"], bool)


def test_operational_catalogue_repository_get_product_policy_data_preserves_unknown_stock(
    db_session,
):
    policy_data = OperationalCatalogueRepository(
        db_session
    ).get_product_policy_data("PROD_ELECTRONICS_3")

    assert policy_data["product_id"] == "PROD_ELECTRONICS_3"
    assert policy_data["product_status"] == "active"
    assert policy_data["available_stock"] is None
    assert policy_data["inventory_status"] == "unknown"
    assert policy_data["gross_margin_pct"] == Decimal("0.5200")
    assert policy_data["shipping_days"] == 4
    assert policy_data["reward_eligible"] is False
    assert policy_data["promotion_eligible"] is False


def test_operational_catalogue_repository_get_product_policy_data_returns_none_for_missing_product(
    db_session,
):
    assert (
        OperationalCatalogueRepository(db_session).get_product_policy_data(
            "PROD_MISSING"
        )
        is None
    )


def test_operational_catalogue_repository_get_product_policy_data_preserves_inner_join(
    db_session,
):
    assert (
        OperationalCatalogueRepository(db_session).get_product_policy_data(
            "PROD_ELECTRONICS_2"
        )
        is None
    )
