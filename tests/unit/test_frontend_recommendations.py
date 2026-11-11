"""Unit and regression tests verifying removal of silent CSV recommendation fallback."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

import frontend.app as app_mod
from frontend.app import fetch_recommendations, render_recommendation_error


def _sample_customer() -> dict:
    return {
        "customer_id": "CUST_0001",
        "preferred_category": "Electronics",
        "membership_tier": "Gold",
        "reward_points": 1200,
        "total_spend": 1500.0,
        "total_orders": 5,
        "customer_segment": "Active",
    }


def _sample_catalogue() -> list[dict]:
    return [
        {
            "product_id": "PROD_0001",
            "product_name": "Wireless Headphones",
            "category": "Electronics",
            "subcategory": "Audio",
            "brand": "AudioMax",
            "unit_price": 199.99,
            "product_rating": 4.7,
            "product_popularity": 0.95,
            "available_stock": 20,
            "inventory_status": "in_stock",
            "gross_margin_pct": 0.45,
        }
    ]


def test_fetch_recommendations_success_preserves_backend_payload():
    backend_payload = {
        "status": "SUCCESS",
        "customer_id": "CUST_0001",
        "decision_id": "dec_123",
        "candidate_count": 5,
        "feasible_count": 3,
        "excluded_count": 2,
        "decision_method": "WEIGHTED_DECISION",
        "decision_engine_status": "SUCCESS",
        "recommendations": [
            {
                "product_id": "PROD_0001",
                "product_name": "Wireless Headphones",
                "category": "Electronics",
                "recommendation_score": 0.91,
                "policy_decision": "PASS",
            }
        ],
        "excluded_candidates": [],
    }
    mock_res = MagicMock()
    mock_res.ok = True
    mock_res.status_code = 200
    mock_res.json.return_value = backend_payload

    with patch("requests.post", return_value=mock_res) as mock_post:
        result = fetch_recommendations("CUST_0001", top_k=5, reward_context=True)

    mock_post.assert_called_once()
    assert mock_post.call_args.kwargs["timeout"] >= 60
    assert result == backend_payload
    assert result["status"] == "SUCCESS"
    assert result["decision_method"] == "WEIGHTED_DECISION"
    assert len(result["recommendations"]) == 1


@pytest.mark.parametrize(
    "status_code,engine_status,rec_status,expected_text",
    [
        (502, "FAILED", "FAILED_SAFE", "502"),
        (503, "UNAVAILABLE", "ERROR", "503"),
    ],
)
def test_fetch_recommendations_502_and_503_do_not_fallback(
    status_code: int,
    engine_status: str,
    rec_status: str,
    expected_text: str,
):
    mock_res = MagicMock()
    mock_res.ok = False
    mock_res.status_code = status_code
    mock_res.json.return_value = {
        "status": rec_status,
        "decision_engine_status": engine_status,
        "detail": "Decision evaluation failed",
    }

    with (
        patch("requests.post", return_value=mock_res),
        patch("frontend.app.load_catalogue", side_effect=AssertionError("CSV fallback must not run")),
    ):
        result = fetch_recommendations("CUST_0001", top_k=5)

    assert result["status"] == "ERROR"
    assert result["status"] != "SUCCESS"
    assert result["recommendations"] == []
    assert result["excluded_candidates"] == []
    assert result["error_type"] == "decision_or_workflow_failure"
    assert result["http_status"] == status_code
    assert expected_text in result["error"]


def test_fetch_recommendations_connection_error_does_not_fallback():
    with (
        patch("requests.post", side_effect=requests.exceptions.ConnectionError("Connection refused")),
        patch("frontend.app.load_catalogue", side_effect=AssertionError("CSV fallback must not run")),
    ):
        result = fetch_recommendations("CUST_0001", top_k=5)

    assert result["status"] == "ERROR"
    assert result["recommendations"] == []
    assert result["excluded_candidates"] == []
    assert result["error_type"] == "backend_unavailable"
    assert "unreachable" in result["error"].lower()


def test_fetch_recommendations_timeout_does_not_fallback():
    with (
        patch("requests.post", side_effect=requests.exceptions.Timeout("Timed out")),
        patch("frontend.app.load_catalogue", side_effect=AssertionError("CSV fallback must not run")),
    ):
        result = fetch_recommendations("CUST_0001", top_k=5)

    assert result["status"] == "ERROR"
    assert result["recommendations"] == []
    assert result["excluded_candidates"] == []
    assert result["error_type"] == "timeout"
    assert "timed out" in result["error"].lower()


@pytest.mark.parametrize(
    "json_behavior",
    [
        ValueError("Invalid JSON"),
        ["not", "a", "dict"],
        {"status": "SUCCESS"},
        {"recommendations": []},
    ],
)
def test_fetch_recommendations_malformed_response_returns_error(json_behavior):
    mock_res = MagicMock()
    mock_res.ok = True
    mock_res.status_code = 200
    if isinstance(json_behavior, Exception):
        mock_res.json.side_effect = json_behavior
    else:
        mock_res.json.return_value = json_behavior

    with (
        patch("requests.post", return_value=mock_res),
        patch("frontend.app.load_catalogue", side_effect=AssertionError("CSV fallback must not run")),
    ):
        result = fetch_recommendations("CUST_0001", top_k=5)

    assert result["status"] == "ERROR"
    assert result["recommendations"] == []
    assert result["error_type"] == "invalid_response"
    assert "invalid response" in result["error"].lower()


def test_render_recommendation_error_displays_banner_on_failure():
    err_payload = {
        "status": "ERROR",
        "recommendations": [],
        "error": "Backend recommendation service is unreachable.",
    }
    with patch.object(app_mod.st, "error") as mock_error:
        failed = render_recommendation_error(err_payload)

    assert failed is True
    mock_error.assert_called_once()
    assert "Backend recommendation service is unreachable." in mock_error.call_args[0][0]


@pytest.mark.parametrize(
    "page_fn_name",
    [
        "render_recommendations_discovery",
        "render_preferences_studio",
        "render_next_best_offer_centre",
        "render_inventory_policy_centre",
        "render_demo_playground",
        "render_ai_assistant",
    ],
)
def test_all_six_caller_pages_handle_backend_error_without_crashing(page_fn_name: str):
    cust = _sample_customer()
    catalogue = _sample_catalogue()
    err_payload = {
        "status": "ERROR",
        "customer_id": "CUST_0001",
        "candidate_count": 0,
        "feasible_count": 0,
        "excluded_count": 0,
        "recommendations": [],
        "excluded_candidates": [],
        "error": "Laya decision layer or workflow service is unavailable (HTTP 503).",
        "error_type": "laya_or_workflow_failure",
        "http_status": 503,
    }
    fake_session = {
        "selected_customer_id": "CUST_0001",
        "studio_rec_result": err_payload,
        "demo_result": err_payload,
        "assistant_messages": [{"role": "assistant", "content": "Ready"}],
    }

    with (
        patch.object(app_mod, "load_all_customers", return_value=[cust]),
        patch.object(app_mod, "load_customer_detail", return_value={"customer": cust, "interactions": [], "recent_transactions": []}),
        patch.object(app_mod, "load_catalogue", return_value=catalogue),
        patch.object(app_mod, "fetch_recommendations", return_value=err_payload) as mock_fetch,
        patch.object(app_mod.st, "session_state", fake_session),
        patch("streamlit.delta_generator.DeltaGenerator.selectbox", return_value="CUST_0001"),
        patch.object(app_mod.st, "error") as mock_error,
        patch.object(app_mod.st, "chat_input", return_value=None),
    ):
        getattr(app_mod, page_fn_name)()

    mock_error.assert_called()
    assert any("HTTP 503" in str(call.args[0]) for call in mock_error.call_args_list)
    if page_fn_name == "render_next_best_offer_centre":
        # Must not perform a second fallback retry when first call returned ERROR
        mock_fetch.assert_called_once()
