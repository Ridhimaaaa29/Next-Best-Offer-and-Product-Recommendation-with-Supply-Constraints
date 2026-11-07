from unittest.mock import MagicMock
import re

import pytest

from backend.app.recommendation import candidate_generator, customer_context
from backend.app.db.session import get_db_context


def _mock_connection(preferred_category, candidate_rows):
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = (preferred_category,)
    cursor.fetchall.return_value = candidate_rows
    connection.__enter__.return_value = connection
    return connection, cursor


def test_candidates_match_customer_preferred_category():
    customer_id = "CUST_0001"
    with get_db_context() as session:
        expected_category = customer_context.get_customer_context(
            customer_id, session
        )["customer"]["preferred_category"]

    candidates = candidate_generator.generate_candidates(customer_id)

    assert candidates
    assert all(candidate["category"] == expected_category for candidate in candidates)


def test_previously_interacted_products_are_excluded():
    customer_id = "CUST_0001"
    with get_db_context() as session:
        context = customer_context.get_customer_context(customer_id, session)
    interacted_product_ids = {
        interaction["product_id"] for interaction in context["interactions"]
    }

    candidates = candidate_generator.generate_candidates(customer_id)
    candidate_product_ids = {candidate["product_id"] for candidate in candidates}

    assert candidate_product_ids.isdisjoint(interacted_product_ids)


def test_candidates_are_ordered_by_popularity_then_rating():
    candidates = candidate_generator.generate_candidates("CUST_0001")

    for current, following in zip(candidates, candidates[1:]):
        assert current["product_popularity"] >= following["product_popularity"]
        if current["product_popularity"] == following["product_popularity"]:
            assert current["product_rating"] >= following["product_rating"]


def test_candidate_limit_is_applied_and_passed_to_sql(monkeypatch):
    connection, cursor = _mock_connection(
        "Electronics",
        [
            (
                "PROD_TEST",
                "Test Product",
                "Electronics",
                "Accessories",
                "Test Brand",
                10.0,
                4.0,
                0.5,
                "active",
            )
        ],
    )
    monkeypatch.setattr(candidate_generator.psycopg, "connect", lambda _: connection)

    candidates = candidate_generator.generate_candidates("CUST_0001", limit=5)

    assert len(candidates) <= 5
    assert len(cursor.execute.call_args_list) == 2
    candidate_sql, candidate_parameters = cursor.execute.call_args_list[1].args
    normalized_sql = re.sub(r"\s+", " ", candidate_sql)
    assert "ORDER BY p.product_popularity DESC" in normalized_sql
    assert "p.product_rating DESC" in normalized_sql
    assert candidate_parameters == ("Electronics", "CUST_0001", 5)


def test_unknown_customer_raises_value_error():
    with pytest.raises(ValueError, match="Customer not found"):
        candidate_generator.generate_candidates("CUST_NON_EXISTENT_99999")


def test_empty_candidate_pool_returns_empty_list(monkeypatch):
    connection, _ = _mock_connection("Electronics", [])
    monkeypatch.setattr(candidate_generator.psycopg, "connect", lambda _: connection)

    candidates = candidate_generator.generate_candidates("CUST_EMPTY_POOL")

    assert candidates == []