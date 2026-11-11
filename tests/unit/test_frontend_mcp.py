"""
Unit tests for Streamlit Frontend MCP Workflow, Decision Status, and Governance Audit integration.
"""

from unittest.mock import MagicMock, patch
import requests

from frontend.app import (
    check_decision_engine_status,
    fetch_decision_history,
    fetch_mcp_workflow,
    render_mcp_agentic_workflow,
    submit_manual_audit,
)


def test_fetch_mcp_workflow_success():
    mock_payload = {
        "status": "SUCCESS",
        "customer_id": "CUST_0001",
        "decision_id": "audit_abc_123",
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
                "weighted_score": 0.88,
                "rank": 1,
            }
        ],
        "excluded_candidates": [],
        "selected_product_id": "PROD_0001",
        "decision_method": "WEIGHTED_DECISION",
        "fallback_used": False,
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
    assert data["selected_product_id"] == "PROD_0001"
    assert data["decision_method"] == "WEIGHTED_DECISION"
    assert data["decision_id"] == "audit_abc_123"

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


def test_fetch_mcp_workflow_503_and_502_errors():
    for code, msg in [
        (503, "MCP workflow completed but decision audit persistence failed"),
        (502, "Upstream MCP tool failed during workflow execution."),
    ]:
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = code
        mock_response.json.return_value = {"status": "FAILED_SAFE", "error": msg}

        with patch("requests.post", return_value=mock_response):
            data, status_code, err = fetch_mcp_workflow(customer_id="CUST_0001")

        assert status_code == code
        assert data is not None
        assert msg in err


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


def test_submit_manual_audit_persists_or_reports_real_failure():
    ok_res = MagicMock()
    ok_res.ok = True
    ok_res.status_code = 201
    ok_res.json.return_value = {"decision_id": "dec_999", "approval_status": "APPROVED"}

    with patch("requests.post", return_value=ok_res):
        saved, err = submit_manual_audit({"customer_id": "CUST_0001"})
    assert err is None
    assert saved["decision_id"] == "dec_999"

    fail_res = MagicMock()
    fail_res.ok = False
    fail_res.status_code = 503
    fail_res.json.return_value = {"detail": "DB unavailable"}
    with patch("requests.post", return_value=fail_res):
        saved, err = submit_manual_audit({"customer_id": "CUST_0001"})
    assert saved is None
    assert "DB unavailable" in err


def test_check_decision_engine_status_and_history():
    check_decision_engine_status.clear()
    status_res = MagicMock()
    status_res.ok = True
    status_res.json.return_value = {
        "configured": True,
        "enabled": True,
        "available": True,
        "weights": {"relevance": 0.45, "margin": 0.25, "diversity": 0.15, "friction": 0.15},
    }
    with patch("requests.get", return_value=status_res):
        status_data = check_decision_engine_status()
    assert status_data["available"] is True
    assert status_data["weights"]["relevance"] == 0.45

    hist_res = MagicMock()
    hist_res.ok = True
    hist_res.json.return_value = [{"decision_id": "dec_1", "selected_product_id": "PROD_0001"}]
    with patch("requests.get", return_value=hist_res):
        rows, err = fetch_decision_history("CUST_0001", limit=5)
    assert err is None
    assert len(rows) == 1


def test_render_mcp_agentic_workflow_function_exists():
    assert callable(render_mcp_agentic_workflow)
