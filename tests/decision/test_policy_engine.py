from unittest.mock import MagicMock

import pytest

from backend.app.recommendation import policy_engine


def _mock_connection(row):
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = row
    connection.__enter__.return_value = connection
    return connection


def _patch_product(monkeypatch, row):
    connection = _mock_connection(row)
    monkeypatch.setattr(policy_engine.psycopg, "connect", lambda _: connection)


def _product_row(
    product_id="PROD_TEST",
    product_status="active",
    available_stock=10,
    inventory_status="available",
    gross_margin_pct=0.20,
    shipping_days=3,
    reward_eligible=True,
    promotion_eligible=True,
):
    return (
        product_id,
        product_status,
        available_stock,
        inventory_status,
        gross_margin_pct,
        shipping_days,
        reward_eligible,
        promotion_eligible,
    )


def test_active_product_with_valid_stock_and_margin_passes(monkeypatch):
    _patch_product(monkeypatch, _product_row())

    result = policy_engine.evaluate_product("PROD_TEST")

    assert result == {
        "product_id": "PROD_TEST",
        "decision": "PASS",
        "reasons": [],
        "flags": [],
    }


def test_discontinued_product_is_excluded(monkeypatch):
    _patch_product(
        monkeypatch,
        _product_row(product_status="discontinued"),
    )

    result = policy_engine.evaluate_product("PROD_TEST")

    assert result["product_id"] == "PROD_TEST"
    assert result["decision"] == "EXCLUDE"
    assert result["reasons"] == [
        "Product status is 'discontinued', not active."
    ]
    assert result["flags"] == []


@pytest.mark.parametrize("available_stock", [0, -1])
def test_zero_and_negative_stock_are_excluded(monkeypatch, available_stock):
    _patch_product(
        monkeypatch,
        _product_row(available_stock=available_stock),
    )

    result = policy_engine.evaluate_product("PROD_TEST")

    assert result["product_id"] == "PROD_TEST"
    assert result["decision"] == "EXCLUDE"
    assert result["reasons"] == ["Product is out of stock."]
    assert result["flags"] == []


def test_unknown_inventory_is_excluded(monkeypatch):
    _patch_product(
        monkeypatch,
        _product_row(available_stock=None),
    )

    result = policy_engine.evaluate_product("PROD_TEST")

    assert result["product_id"] == "PROD_TEST"
    assert result["decision"] == "EXCLUDE"
    assert result["reasons"] == ["Inventory availability is unknown."]
    assert result["flags"] == []


@pytest.mark.parametrize(
    ("gross_margin_pct", "expected_decision", "expected_reasons"),
    [
        (0.09, "EXCLUDE", ["Gross margin (9.00%) is below the 10% minimum."]),
        (0.10, "PASS", []),
    ],
)
def test_margin_boundary_evaluation(
    monkeypatch,
    gross_margin_pct,
    expected_decision,
    expected_reasons,
):
    _patch_product(
        monkeypatch,
        _product_row(gross_margin_pct=gross_margin_pct),
    )

    result = policy_engine.evaluate_product("PROD_TEST")

    assert result["product_id"] == "PROD_TEST"
    assert result["decision"] == expected_decision
    assert result["reasons"] == expected_reasons
    assert result["flags"] == []


def test_reward_eligibility_enforced_only_in_reward_context(monkeypatch):
    _patch_product(
        monkeypatch,
        _product_row(reward_eligible=False),
    )

    without_reward_context = policy_engine.evaluate_product("PROD_TEST")
    with_reward_context = policy_engine.evaluate_product(
        "PROD_TEST",
        reward_context=True,
    )

    assert without_reward_context["product_id"] == "PROD_TEST"
    assert without_reward_context["decision"] == "PASS"
    assert without_reward_context["reasons"] == []
    assert without_reward_context["flags"] == []
    assert with_reward_context["product_id"] == "PROD_TEST"
    assert with_reward_context["decision"] == "EXCLUDE"
    assert with_reward_context["reasons"] == ["Product is not reward eligible."]
    assert with_reward_context["flags"] == []


def test_promotion_eligibility_enforced_only_in_promotion_context(monkeypatch):
    _patch_product(
        monkeypatch,
        _product_row(promotion_eligible=False),
    )

    without_promotion_context = policy_engine.evaluate_product("PROD_TEST")
    with_promotion_context = policy_engine.evaluate_product(
        "PROD_TEST",
        promotion_context=True,
    )

    assert without_promotion_context["product_id"] == "PROD_TEST"
    assert without_promotion_context["decision"] == "PASS"
    assert without_promotion_context["reasons"] == []
    assert without_promotion_context["flags"] == []
    assert with_promotion_context["product_id"] == "PROD_TEST"
    assert with_promotion_context["decision"] == "EXCLUDE"
    assert with_promotion_context["reasons"] == [
        "Product is not promotion eligible."
    ]
    assert with_promotion_context["flags"] == []


def test_express_shipping_over_seven_days_sets_flag_without_exclusion(monkeypatch):
    _patch_product(
        monkeypatch,
        _product_row(shipping_days=8),
    )

    result = policy_engine.evaluate_product(
        "PROD_TEST",
        express_context=True,
    )

    assert result["product_id"] == "PROD_TEST"
    assert result["decision"] == "PASS"
    assert result["reasons"] == []
    assert result["flags"] == [
        "Shipping time (8 days) exceeds the 7-day express threshold."
    ]


def test_missing_operational_catalogue_raises_expected_exception(monkeypatch):
    _patch_product(monkeypatch, None)

    with pytest.raises(
        ValueError,
        match="^Product or operational catalogue record not found: PROD_MISSING$",
    ):
        policy_engine.evaluate_product("PROD_MISSING")


def test_multiple_policy_failures_accumulate_all_reasons(monkeypatch):
    _patch_product(
        monkeypatch,
        _product_row(
            product_status="discontinued",
            available_stock=0,
            gross_margin_pct=0.05,
            reward_eligible=False,
            promotion_eligible=False,
        ),
    )

    result = policy_engine.evaluate_product(
        "PROD_TEST",
        reward_context=True,
        promotion_context=True,
    )

    assert result["product_id"] == "PROD_TEST"
    assert result["decision"] == "EXCLUDE"
    assert result["reasons"] == [
        "Product status is 'discontinued', not active.",
        "Product is out of stock.",
        "Gross margin (5.00%) is below the 10% minimum.",
        "Product is not reward eligible.",
        "Product is not promotion eligible.",
    ]
    assert result["flags"] == []


def test_unknown_inventory_status_is_excluded(monkeypatch):
    _patch_product(
        monkeypatch,
        (
            "PROD_TEST",
            "active",
            12,
            "unknown",
            0.30,
            3,
            True,
            True,
            "verified_fresh",
            0.20,
        ),
    )

    result = policy_engine.evaluate_product("PROD_TEST")

    assert result["decision"] == "EXCLUDE"
    assert "Inventory availability is unknown." in result["reasons"]


@pytest.mark.parametrize("freshness_status", ["stale", "unverified", None])
def test_stale_or_missing_operational_freshness_is_excluded(monkeypatch, freshness_status):
    _patch_product(
        monkeypatch,
        (
            "PROD_TEST",
            "active",
            12,
            "available",
            0.30,
            3,
            True,
            True,
            freshness_status,
            0.20,
        ),
    )

    result = policy_engine.evaluate_product("PROD_TEST")

    assert result["decision"] == "EXCLUDE"
    assert any("stale or unverified" in reason for reason in result["reasons"])


def test_discount_limit_policy_enforced(monkeypatch):
    row = (
        "PROD_TEST",
        "active",
        12,
        "available",
        0.30,
        3,
        True,
        True,
        "verified_fresh",
        0.15,
    )
    _patch_product(monkeypatch, row)
    allowed = policy_engine.evaluate_product("PROD_TEST", requested_discount_pct=0.10)
    assert allowed["decision"] == "PASS"

    _patch_product(monkeypatch, row)
    rejected = policy_engine.evaluate_product("PROD_TEST", requested_discount_pct=0.25)
    assert rejected["decision"] == "EXCLUDE"
    assert any("exceeds maximum permitted limit" in reason for reason in rejected["reasons"])
