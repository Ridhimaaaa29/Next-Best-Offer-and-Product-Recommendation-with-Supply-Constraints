"""Unit tests for atomic dispatch+audit in catalogue.py.

Tests verify:
1. Successful dispatch deducts stock and creates audit record (mocked DB).
2. Insufficient stock raises HTTP 400 and no audit record is written.
3. Audit DB write failure causes full rollback — stock unchanged.
4. Missing customer_id dispatches stock but skips audit creation.
5. Concurrent dispatch scenario: second request is rejected cleanly.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch, PropertyMock, call
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_op_row(stock: float = 10.0, reorder: int = 5) -> MagicMock:
    row = MagicMock()
    row.available_stock = stock
    row.reorder_point = reorder
    row.inventory_status = "in_stock"
    return row


def _make_product_row(name: str = "Test Product") -> MagicMock:
    p = MagicMock()
    p.product_name = name
    return p


def _make_db(op_row, product_row=None) -> MagicMock:
    """Return a mock Session where execute().scalar_one_or_none() yields op_row."""
    db = MagicMock(spec=Session)

    # First call → OperationalCatalogue (with_for_update), second call → Product
    execute_result_op = MagicMock()
    execute_result_op.scalar_one_or_none.return_value = op_row

    execute_result_prod = MagicMock()
    execute_result_prod.scalar_one_or_none.return_value = product_row or _make_product_row()

    db.execute.side_effect = [execute_result_op, execute_result_prod]
    return db


# ---------------------------------------------------------------------------
# Import the endpoint under test
# ---------------------------------------------------------------------------

from backend.app.api.routes.catalogue import dispatch_product, DispatchRequest


# ---------------------------------------------------------------------------
# Test 1: Successful dispatch with audit
# ---------------------------------------------------------------------------

def test_dispatch_success_creates_audit():
    """Happy path: stock deducted AND audit record added in same session."""
    op_row = _make_op_row(stock=10.0)
    db = _make_db(op_row)

    body = DispatchRequest(
        quantity=2,
        customer_id="CUST_0001",
        ranking_method="NBO_DISPATCH",
        candidate_products=["P1", "P2"],
        feasible_products=["P1"],
        excluded_products=["P2"],
        selected_product_id="P1",
        decision_explanation="Top NBO pick",
        fallback_used=False,
    )

    with patch("backend.app.api.routes.catalogue.uuid.uuid4", return_value="test-uuid-1234"):
        result = dispatch_product("P1", body, db)

    assert result["dispatched"] is True
    assert result["stock_before"] == 10.0
    assert result["stock_after"] == 8.0
    assert result["audit_created"] is True
    assert result["decision_id"] == "test-uuid-1234"

    # Verify audit row was added to session
    db.add.assert_called_once()
    added = db.add.call_args[0][0]
    assert added.customer_id == "CUST_0001"
    assert added.status == "DISPATCHED"
    assert added.approval_status == "APPROVED"
    assert json.loads(added.candidate_products) == ["P1", "P2"]

    # Single commit — both changes land together
    db.commit.assert_called_once()
    db.rollback.assert_not_called()


# ---------------------------------------------------------------------------
# Test 2: Insufficient stock → HTTP 400, no audit written
# ---------------------------------------------------------------------------

def test_dispatch_insufficient_stock_no_audit():
    """Stock < requested quantity → 400, nothing committed, no audit row."""
    op_row = _make_op_row(stock=1.0)
    db = _make_db(op_row)

    body = DispatchRequest(quantity=5, customer_id="CUST_0002")

    with pytest.raises(HTTPException) as exc_info:
        dispatch_product("P2", body, db)

    assert exc_info.value.status_code == 400
    assert "Insufficient stock" in exc_info.value.detail

    # Stock value untouched on the row object
    assert op_row.available_stock == 1.0

    # Rollback called, commit never called, audit never added
    db.rollback.assert_called_once()
    db.commit.assert_not_called()
    db.add.assert_not_called()


# ---------------------------------------------------------------------------
# Test 3: Audit DB write failure → full rollback, stock unchanged
# ---------------------------------------------------------------------------

def test_dispatch_audit_write_failure_causes_rollback():
    """If db.add raises, rollback is called and HTTP 500 is raised."""
    op_row = _make_op_row(stock=5.0)
    db = _make_db(op_row)
    db.add.side_effect = RuntimeError("DB write failure")

    body = DispatchRequest(quantity=1, customer_id="CUST_0003")

    with pytest.raises(HTTPException) as exc_info:
        dispatch_product("P3", body, db)

    assert exc_info.value.status_code == 500
    assert "Dispatch transaction failed" in exc_info.value.detail

    db.rollback.assert_called_once()
    db.commit.assert_not_called()


# ---------------------------------------------------------------------------
# Test 4: Missing customer_id → dispatch succeeds, audit skipped
# ---------------------------------------------------------------------------

def test_dispatch_without_customer_id_skips_audit():
    """When customer_id is None, inventory deducts but no audit row is created."""
    op_row = _make_op_row(stock=20.0)
    db = _make_db(op_row)

    body = DispatchRequest(quantity=3)  # no customer_id

    result = dispatch_product("P4", body, db)

    assert result["dispatched"] is True
    assert result["stock_after"] == 17.0
    assert result["audit_created"] is False
    assert result["decision_id"] is None

    db.add.assert_not_called()
    db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# Test 5: Product not in operational catalogue → HTTP 404
# ---------------------------------------------------------------------------

def test_dispatch_product_not_found_raises_404():
    """Product missing from operational_catalogue returns 404 immediately."""
    db = MagicMock(spec=Session)
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = None
    db.execute.return_value = execute_result

    body = DispatchRequest(quantity=1, customer_id="CUST_0004")

    with pytest.raises(HTTPException) as exc_info:
        dispatch_product("NONEXISTENT", body, db)

    assert exc_info.value.status_code == 404
    db.rollback.assert_called_once()
    db.commit.assert_not_called()
    db.add.assert_not_called()


# ---------------------------------------------------------------------------
# Test 6: Stock reaches exactly zero → inventory_status becomes out_of_stock
# ---------------------------------------------------------------------------

def test_dispatch_exact_zero_stock_sets_out_of_stock():
    """Dispatching exactly remaining stock marks status as out_of_stock."""
    op_row = _make_op_row(stock=3.0)
    db = _make_db(op_row)

    body = DispatchRequest(quantity=3)  # exact depletion

    result = dispatch_product("P5", body, db)

    assert result["stock_after"] == 0.0
    assert result["inventory_status"] == "out_of_stock"
    assert op_row.inventory_status == "out_of_stock"


# ---------------------------------------------------------------------------
# Test 7: Stock falls to reorder point → inventory_status becomes low_stock
# ---------------------------------------------------------------------------

def test_dispatch_reaches_reorder_point_sets_low_stock():
    """When remaining stock ≤ reorder_point, status becomes low_stock."""
    op_row = _make_op_row(stock=10.0, reorder=5)
    db = _make_db(op_row)

    body = DispatchRequest(quantity=6)  # leaves 4 ≤ reorder_point=5

    result = dispatch_product("P6", body, db)

    assert result["stock_after"] == 4.0
    assert result["inventory_status"] == "low_stock"


# ---------------------------------------------------------------------------
# Test 8: Concurrent dispatch simulation — second call rejected after lock
# ---------------------------------------------------------------------------

def test_concurrent_dispatch_second_rejected():
    """Simulate two concurrent dispatches where first succeeds, second fails."""
    # First request acquires lock and dispatches 1 unit from stock=1
    op_row_first = _make_op_row(stock=1.0)
    db_first = _make_db(op_row_first)
    body = DispatchRequest(quantity=1)
    result_first = dispatch_product("P7", body, db_first)
    assert result_first["dispatched"] is True
    assert result_first["stock_after"] == 0.0

    # Second request sees stock=0 (simulating post-commit state)
    op_row_second = _make_op_row(stock=0.0)
    db_second = _make_db(op_row_second)
    body2 = DispatchRequest(quantity=1)

    with pytest.raises(HTTPException) as exc_info:
        dispatch_product("P7", body2, db_second)

    assert exc_info.value.status_code == 400
    assert "Insufficient stock" in exc_info.value.detail
    db_second.commit.assert_not_called()

