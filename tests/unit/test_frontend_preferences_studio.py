"""Regression tests for Preferences Studio category options and customer personas."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
import streamlit as st

from frontend.app import (
    DEFAULT_CATEGORIES,
    render_preferences_studio,
    resolve_category_options,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CUSTOMERS_CSV = PROJECT_ROOT / "data" / "synthetic" / "customers.csv"
PRODUCTS_CSV = PROJECT_ROOT / "data" / "synthetic" / "products.csv"


def _load_csv_customers() -> list[dict]:
    return pd.read_csv(CUSTOMERS_CSV).to_dict(orient="records")


def _load_csv_catalogue() -> list[dict]:
    return pd.read_csv(PRODUCTS_CSV).to_dict(orient="records")


def _load_csv_customer_detail(customer_id: str) -> dict:
    df = pd.read_csv(CUSTOMERS_CSV)
    row = df[df["customer_id"] == customer_id].iloc[0].to_dict()
    return {"customer": row, "interactions": [], "recent_transactions": []}


def test_resolve_category_options_includes_all_authoritative_categories():
    catalogue = _load_csv_catalogue()
    options, defaults = resolve_category_options(
        catalogue, preferred_category="Health & Fitness"
    )
    for category in DEFAULT_CATEGORIES:
        assert category in options
    assert defaults == ["Health & Fitness"]


def test_resolve_category_options_handles_missing_and_unexpected_values():
    catalogue = _load_csv_catalogue()

    options_none, defaults_none = resolve_category_options(
        catalogue, preferred_category=None
    )
    assert defaults_none == [options_none[0]]

    options_nan, defaults_nan = resolve_category_options(
        catalogue, preferred_category=float("nan")
    )
    assert defaults_nan == [options_nan[0]]

    options_custom, defaults_custom = resolve_category_options(
        catalogue, preferred_category="Specialty Outdoors"
    )
    assert "Specialty Outdoors" in options_custom
    assert defaults_custom == ["Specialty Outdoors"]


def _run_preferences_studio_for_customer(customer_id: str) -> dict[str, object]:
    """Execute render_preferences_studio using real st.multiselect validation."""
    customers = _load_csv_customers()
    catalogue = _load_csv_catalogue()
    captured: dict[str, object] = {}
    real_multiselect = st.multiselect
    fake_session: dict[str, object] = {"selected_customer_id": customer_id}

    def _capturing_multiselect(label, options, default=None, *args, **kwargs):
        captured["label"] = label
        captured["options"] = list(options)
        captured["default"] = list(default) if default is not None else []
        # Invoke real Streamlit multiselect so StreamlitDefaultNotInOptionsError is enforced
        return real_multiselect(label, options, default=default, *args, **kwargs)

    with (
        patch("frontend.app.load_all_customers", return_value=customers),
        patch("frontend.app.load_catalogue", return_value=catalogue),
        patch("frontend.app.load_customer_detail", side_effect=_load_csv_customer_detail),
        patch.object(st, "session_state", fake_session),
        patch("streamlit.delta_generator.DeltaGenerator.selectbox", return_value=customer_id),
        patch.object(st, "multiselect", side_effect=_capturing_multiselect),
    ):
        render_preferences_studio()

    return captured


def test_preferences_studio_cust_0004_regression():
    """Regression test: CUST_0004 (Health & Fitness) renders without StreamlitDefaultNotInOptionsError."""
    captured = _run_preferences_studio_for_customer("CUST_0004")
    assert captured["default"] == ["Health & Fitness"]
    assert "Health & Fitness" in captured["options"]


@pytest.mark.parametrize("customer_id", [f"CUST_{i:04d}" for i in range(1, 11)])
def test_preferences_studio_loads_cust_0001_through_0010(customer_id: str):
    """Verify Preferences Studio renders cleanly for CUST_0001 through CUST_0010."""
    expected_pref = _load_csv_customer_detail(customer_id)["customer"]["preferred_category"]
    captured = _run_preferences_studio_for_customer(customer_id)
    assert captured["default"] == [expected_pref]
    assert expected_pref in captured["options"]
