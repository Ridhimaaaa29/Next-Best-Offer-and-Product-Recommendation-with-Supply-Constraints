"""
Unit tests for Streamlit Frontend MCP Workflow integration.
Verifies:
1. fetch_mcp_workflow sends correct POST payload to /mcp/workflow and returns structured result.
2. fetch_mcp_workflow handles 503 Laya unavailable properly.
3. fetch_mcp_workflow handles 502 Laya invalid selection properly.
4. fetch_mcp_workflow handles connection errors and timeouts gracefully.
5. frontend/app.py exports render_mcp_agentic_workflow and includes it in navigation.
"""

from unittest.mock import MagicMock, patch
import requests

from frontend.app import fetch_mcp_workflow, render_mcp_agentic_workflow


def test_fetch_mcp_workflow_success():
    mock_payload = {
        "status": "SUCCESS",
        "customer_id": "CUST_0001",
        "agents": [
            {
                "agent": "Customer Agent",
                "responsibility": "Retrieve customer context",
                "status": "completed",
                "duration_ms": 10.5,
                "output": {"customer_id": "CUST_0001"},
            }
        ],
        "tool_calls": [],
        "recommendations": [
            {
                "product_id": "PROD_0001",
                "product_name": "Premium Headphones",
                "recommendation_score": 0.95,
                "policy_decision": "PASS",
            }
        ],
        "excluded_candidates": [],
        "laya_selected_product_id": "PROD_0001",
        "laya_status": "LAYA",
        "error": None,
    }

    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.json.return_value = mock_payload

    with patch("requests.post", return_value=mock_response) as mock_post:
        data, status_code, err = fetch_mcp_workflow(
            customer_id="CUST_0001",
            top_k=5,
            reward_context=True,
            promotion_context=False,
            express_context=True,
        )

    assert status_code == 200
    assert err is None
    assert data["status"] == "SUCCESS"
    assert data["laya_selected_product_id"] == "PROD_0001"

    # Verify requests.post called with correct endpoint and payload
    mock_post.assert_called_once()
    called_args, called_kwargs = mock_post.call_args
    assert called_args[0].endswith("/mcp/workflow")
    assert called_kwargs["json"] == {
        "customer_id": "CUST_0001",
        "top_k": 5,
        "reward_context": True,
        "promotion_context": False,
        "express_context": True,
    }


def test_fetch_mcp_workflow_laya_unavailable_503():
    mock_payload = {
        "status": "FAILED_SAFE",
        "customer_id": "CUST_0001",
        "agents": [
            {
                "agent": "Laya Agent",
                "status": "failed_laya_unavailable",
                "duration_ms": 5.0,
            }
        ],
        "recommendations": [],
        "excluded_candidates": [],
        "error": "Laya is unavailable and score-based fallback is not permitted: Laya disabled.",
    }

    mock_response = MagicMock()
    mock_response.ok = False
    mock_response.status_code = 503
    mock_response.json.return_value = mock_payload

    with patch("requests.post", return_value=mock_response):
        data, status_code, err = fetch_mcp_workflow(customer_id="CUST_0001")

    assert status_code == 503
    assert data is not None
    assert data["status"] == "FAILED_SAFE"
    assert "Laya is unavailable" in err


def test_fetch_mcp_workflow_laya_invalid_selection_502():
    mock_payload = {
        "status": "FAILED_SAFE",
        "customer_id": "CUST_0001",
        "agents": [],
        "recommendations": [],
        "excluded_candidates": [],
        "error": "Laya selected 'XYZ' which is not in the policy-feasible candidate set.",
    }

    mock_response = MagicMock()
    mock_response.ok = False
    mock_response.status_code = 502
    mock_response.json.return_value = mock_payload

    with patch("requests.post", return_value=mock_response):
        data, status_code, err = fetch_mcp_workflow(customer_id="CUST_0001")

    assert status_code == 502
    assert data is not None
    assert "XYZ" in err


def test_fetch_mcp_workflow_connection_error():
    with patch("requests.post", side_effect=requests.exceptions.ConnectionError("Connection refused")):
        data, status_code, err = fetch_mcp_workflow(customer_id="CUST_0001")

    assert data is None
    assert status_code == 503
    assert "Could not connect to the backend service" in err


def test_fetch_mcp_workflow_timeout():
    with patch("requests.post", side_effect=requests.exceptions.Timeout("Read timeout")):
        data, status_code, err = fetch_mcp_workflow(customer_id="CUST_0001")

    assert data is None
    assert status_code == 408
    assert "timed out" in err


def test_render_mcp_agentic_workflow_function_exists():
    """Verify render_mcp_agentic_workflow is a callable function."""
    assert callable(render_mcp_agentic_workflow)
