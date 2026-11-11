from unittest.mock import MagicMock
import re

import pytest

from backend.app.recommendation import candidate_generator


def _mock_connection(preferred_category, candidate_rows):
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = (preferred_category,) if preferred_category is not None else None
    cursor.fetchall.return_value = candidate_rows
    connection.__enter__.return_value = connection
    return connection, cursor


def _row(pid, category="Electronics", popularity=0.8, rating=4.5):
    return (pid, f"Product {pid}", category, "Audio", "BrandX", 59.99, rating, popularity, "active")


def test_candidates_match_customer_preferred_category(monkeypatch):
    rows = [_row("PROD_0001", "Electronics"), _row("PROD_0003", "Electronics")]
    conn, _ = _mock_connection("Electronics", rows)
    monkeypatch.setattr(candidate_generator.psycopg, "connect", lambda _: conn)

    candidates = candidate_generator.generate_candidates("CUST_0001")

    assert candidates
    assert all(candidate["category"] == "Electronics" for candidate in candidates)


def test_previously_interacted_products_are_excluded(monkeypatch):
    # SQL excludes rows in customer_product_interactions via NOT EXISTS
    rows = [_row("PROD_UNSEEN_1"), _row("PROD_UNSEEN_2")]
    conn, cursor = _mock_connection("Electronics", rows)
    monkeypatch.setattr(candidate_generator.psycopg, "connect", lambda _: conn)

    candidates = candidate_generator.generate_candidates("CUST_0001")
    sql, _ = cursor.execute.call_args_list[1].args
    assert "NOT IN" in sql
    assert {c["product_id"] for c in candidates} == {"PROD_UNSEEN_1", "PROD_UNSEEN_2"}


def test_candidates_are_ordered_by_popularity_then_rating(monkeypatch):
    rows = [
        _row("PROD_A", popularity=0.95, rating=4.2),
        _row("PROD_B", popularity=0.85, rating=4.9),
        _row("PROD_C", popularity=0.85, rating=4.1),
    ]
    conn, _ = _mock_connection("Electronics", rows)
    monkeypatch.setattr(candidate_generator.psycopg, "connect", lambda _: conn)

    candidates = candidate_generator.generate_candidates("CUST_0001")

    for current, following in zip(candidates, candidates[1:]):
        assert current["product_popularity"] >= following["product_popularity"]
        if current["product_popularity"] == following["product_popularity"]:
            assert current["product_rating"] >= following["product_rating"]


def test_sql_includes_status_filter(monkeypatch):
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

    _ = candidate_generator.generate_candidates("CUST_0001")
    candidate_sql, _ = cursor.execute.call_args_list[1].args
    normalized_sql = re.sub(r"\s+", " ", candidate_sql)
    assert "p.product_status = 'active'" in normalized_sql
    assert "ORDER BY p.product_popularity DESC" in normalized_sql
    assert "p.product_rating DESC" in normalized_sql


def test_unknown_customer_raises_value_error(monkeypatch):
    conn, _ = _mock_connection(None, [])
    monkeypatch.setattr(candidate_generator.psycopg, "connect", lambda _: conn)

    with pytest.raises(ValueError, match="Customer not found"):
        candidate_generator.generate_candidates("CUST_NON_EXISTENT_99999")


def test_empty_candidate_pool_returns_empty_list(monkeypatch):
    connection, _ = _mock_connection("Electronics", [])
    monkeypatch.setattr(candidate_generator.psycopg, "connect", lambda _: connection)

    candidates = candidate_generator.generate_candidates("CUST_EMPTY_POOL")
    assert candidates == []
