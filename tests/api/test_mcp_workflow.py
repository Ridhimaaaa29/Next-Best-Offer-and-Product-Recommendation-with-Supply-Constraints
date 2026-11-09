"""
API Unit & Integration Tests for MCP Workflow Endpoint (POST /mcp/workflow).
Verifies:
1. Valid MCP workflow request returns 200 and full structured MCPWorkflowResult.
2. Endpoint is accessible at both /mcp/workflow and /api/v1/mcp/workflow.
3. Laya unavailable failure returns 503 and preserves execution trace.
4. Laya invalid candidate selection returns 502 and preserves execution trace.
5. Laya selection failing post-selection revalidation returns 502.
6. Validation errors (missing customer_id, empty string, out-of-range top_k, extra fields) return 422.
7. Unexpected exceptions return 500 without leaking stack traces or credentials.
8. Sensitive credentials or database connection strings are never leaked in error messages.
"""

from unittest.mock import AsyncMock, patch

from backend.app.mcp.schemas import (
    FinalExclusion,
    FinalRecommendation,
)
from backend.app.mcp.workflow import (
    AgentExecution,
    MCPToolTrace,
    MCPWorkflowResult,
)

WORKFLOW_RUN_PATH = "backend.app.api.routes.mcp._run_workflow"


def _make_sample_success_result(customer_id: str = "CUST_0001") -> MCPWorkflowResult:
    return MCPWorkflowResult(
        status="SUCCESS",
        customer_id=customer_id,
        agents=[
            AgentExecution(
                agent="Customer Agent",
                responsibility="Retrieve customer profile",
                status="completed",
                duration_ms=12.5,
                output={"customer_id": customer_id},
            ),
            AgentExecution(
                agent="Recommendation Agent",
                responsibility="Generate scored candidates",
                status="completed",
                duration_ms=45.2,
                output={"candidate_count": 2},
            ),
            AgentExecution(
                agent="Inventory Agent",
                responsibility="Verify inventory",
                status="completed",
                duration_ms=20.1,
                output={"verified": 2},
            ),
            AgentExecution(
                agent="Policy Agent",
                responsibility="Authoritative policy evaluation",
                status="completed",
                duration_ms=15.0,
                output={"pass": 2, "excluded": 0},
            ),
            AgentExecution(
                agent="Laya Agent",
                responsibility="Select Next-Best-Offer",
                status="completed",
                duration_ms=80.3,
                output={"selected_product_id": "PROD_001"},
            ),
            AgentExecution(
                agent="Decision Agent",
                responsibility="Revalidate selection and finalize",
                status="completed",
                duration_ms=18.4,
                output={"recommendations": 1},
            ),
        ],
        tool_calls=[
            MCPToolTrace(
                tool="get_customer_context",
                arguments={"request": {"customer_id": customer_id}},
                status="success",
                duration_ms=12.0,
                result={"customer": {"customer_id": customer_id}},
            ),
            MCPToolTrace(
                tool="run_laya_decision",
                arguments={"request": {"candidates": [{"product_id": "PROD_001"}]}},
                status="success",
                duration_ms=78.0,
                result={"status": "LAYA", "selected_product_id": "PROD_001"},
            ),
        ],
        recommendations=[
            FinalRecommendation(
                product_id="PROD_001",
                product_name="Noise Cancelling Headphones",
                recommendation_score=0.92,
                policy_decision="PASS",
            )
        ],
        excluded_candidates=[
            FinalExclusion(
                product_id="PROD_002",
                product_name="Out of Stock Wireless Charger",
                recommendation_score=0.75,
                policy_decision="EXCLUDE",
                policy_reasons=["Product is out of stock."],
            )
        ],
        laya_selected_product_id="PROD_001",
        laya_status="LAYA",
        error=None,
    )


def test_mcp_workflow_success(client):
    """Happy path: valid request returns 200 and complete structured result."""
    mock_result = _make_sample_success_result("CUST_0001")

    with patch(WORKFLOW_RUN_PATH, new=AsyncMock(return_value=mock_result)) as mock_run:
        payload = {
            "customer_id": "CUST_0001",
            "top_k": 5,
            "reward_context": False,
            "promotion_context": False,
            "express_context": False,
        }
        response = client.post("/mcp/workflow", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["customer_id"] == "CUST_0001"
    assert data["laya_selected_product_id"] == "PROD_001"
    assert data["laya_status"] == "LAYA"
    assert len(data["recommendations"]) == 1
    assert data["recommendations"][0]["product_id"] == "PROD_001"
    assert len(data["excluded_candidates"]) == 1
    assert len(data["agents"]) == 6
    assert len(data["tool_calls"]) == 2
    assert data["error"] is None

    mock_run.assert_called_once_with(
        customer_id="CUST_0001",
        top_k=5,
        reward_context=False,
        promotion_context=False,
        express_context=False,
    )


def test_mcp_workflow_accessible_at_api_prefix(client):
    """Endpoint must be accessible at /api/v1/mcp/workflow conforming to prefix convention."""
    mock_result = _make_sample_success_result("CUST_0002")

    with patch(WORKFLOW_RUN_PATH, new=AsyncMock(return_value=mock_result)):
        payload = {"customer_id": "CUST_0002"}
        response = client.post("/api/v1/mcp/workflow", json=payload)

    assert response.status_code == 200
    assert response.json()["customer_id"] == "CUST_0002"


def test_mcp_workflow_laya_unavailable_returns_503(client):
    """When Laya is disabled or unavailable, returns 503 and preserves failure trace."""
    mock_result = MCPWorkflowResult(
        status="FAILED_SAFE",
        customer_id="CUST_0001",
        agents=[
            AgentExecution(
                agent="Laya Agent",
                responsibility="Select Next-Best-Offer",
                status="failed_laya_unavailable",
                duration_ms=5.0,
                error="Laya is disabled in configuration.",
            )
        ],
        tool_calls=[],
        recommendations=[],
        excluded_candidates=[],
        laya_selected_product_id=None,
        laya_status=None,
        error="Laya is unavailable and score-based fallback is not permitted: Laya is disabled in configuration.",
    )

    with patch(WORKFLOW_RUN_PATH, new=AsyncMock(return_value=mock_result)):
        response = client.post("/mcp/workflow", json={"customer_id": "CUST_0001"})

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "FAILED_SAFE"
    assert "Laya is unavailable" in data["error"]
    assert len(data["agents"]) == 1
    assert data["agents"][0]["status"] == "failed_laya_unavailable"


def test_mcp_workflow_laya_invalid_selection_returns_502(client):
    """When Laya chooses an invalid product ID, returns 502 Bad Gateway."""
    mock_result = MCPWorkflowResult(
        status="FAILED_SAFE",
        customer_id="CUST_0001",
        agents=[
            AgentExecution(
                agent="Laya Agent",
                responsibility="Select Next-Best-Offer",
                status="failed_invalid_selection",
                duration_ms=40.0,
                error="Selected candidate not in feasible set.",
            )
        ],
        tool_calls=[],
        recommendations=[],
        excluded_candidates=[],
        laya_selected_product_id=None,
        laya_status=None,
        error="Laya selected 'UNKNOWN_PROD' which is not in the policy-feasible candidate set.",
    )

    with patch(WORKFLOW_RUN_PATH, new=AsyncMock(return_value=mock_result)):
        response = client.post("/mcp/workflow", json={"customer_id": "CUST_0001"})

    assert response.status_code == 502
    data = response.json()
    assert data["status"] == "FAILED_SAFE"
    assert "UNKNOWN_PROD" in data["error"]


def test_mcp_workflow_laya_infeasible_revalidation_returns_502(client):
    """When Laya's selected candidate fails post-selection policy revalidation, returns 502."""
    mock_result = MCPWorkflowResult(
        status="FAILED_SAFE",
        customer_id="CUST_0001",
        agents=[
            AgentExecution(
                agent="Decision Agent",
                responsibility="Revalidate Laya-selected candidate",
                status="laya_selection_infeasible",
                duration_ms=25.0,
                error="Failed post-selection revalidation",
            )
        ],
        tool_calls=[],
        recommendations=[],
        excluded_candidates=[],
        laya_selected_product_id="PROD_FAIL",
        laya_status="LAYA",
        error="Laya-selected product 'PROD_FAIL' failed post-selection policy revalidation or inventory check.",
    )

    with patch(WORKFLOW_RUN_PATH, new=AsyncMock(return_value=mock_result)):
        response = client.post("/mcp/workflow", json={"customer_id": "CUST_0001"})

    assert response.status_code == 502
    data = response.json()
    assert data["status"] == "FAILED_SAFE"
    assert "failed post-selection policy revalidation" in data["error"]


def test_mcp_workflow_validation_errors(client):
    """Validates 422 responses on invalid request payloads."""
    # Missing customer_id
    res = client.post("/mcp/workflow", json={"top_k": 5})
    assert res.status_code == 422

    # Empty customer_id
    res = client.post("/mcp/workflow", json={"customer_id": ""})
    assert res.status_code == 422

    # top_k < 1
    res = client.post("/mcp/workflow", json={"customer_id": "CUST_0001", "top_k": 0})
    assert res.status_code == 422

    # top_k > 50
    res = client.post("/mcp/workflow", json={"customer_id": "CUST_0001", "top_k": 51})
    assert res.status_code == 422

    # Extra forbidden field
    res = client.post(
        "/mcp/workflow",
        json={"customer_id": "CUST_0001", "unknown_field": "disallowed"},
    )
    assert res.status_code == 422


def test_mcp_workflow_unexpected_exception_returns_500(client):
    """Unhandled internal exceptions return 500 without leaking stack traces."""
    with patch(
        WORKFLOW_RUN_PATH,
        new=AsyncMock(side_effect=RuntimeError("Internal system failure: postgres connection reset")),
    ):
        response = client.post("/mcp/workflow", json={"customer_id": "CUST_0001"})

    assert response.status_code == 500
    data = response.json()
    assert "detail" in data
    # Ensure raw internal details and stack trace are sanitized
    assert "Traceback" not in data["detail"]
    assert "postgres connection reset" not in data["detail"]


def test_mcp_workflow_sanitizes_credentials_in_workflow_error(client):
    """Ensures connection strings or secrets in workflow errors are sanitized."""
    mock_result = MCPWorkflowResult(
        status="FAILED_SAFE",
        customer_id="CUST_0001",
        agents=[
            AgentExecution(
                agent="Inventory Agent",
                responsibility="Verify inventory",
                status="failed",
                duration_ms=10.0,
                error="DB fail with postgresql://neondb_owner:secret_pw@host/db",
            )
        ],
        tool_calls=[],
        recommendations=[],
        excluded_candidates=[],
        error="Connection failed: postgresql://neondb_owner:secret_pw@host/db",
    )

    with patch(WORKFLOW_RUN_PATH, new=AsyncMock(return_value=mock_result)):
        response = client.post("/mcp/workflow", json={"customer_id": "CUST_0001"})

    data = response.json()
    assert "secret_pw" not in str(data)
    assert "postgresql://" not in str(data)
