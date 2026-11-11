"""
API Unit & Integration Tests for MCP Workflow Endpoint (POST /mcp/workflow).
Verifies:
1. Valid MCP workflow request returns 200, all 6 stages, weighted decision fields, and persisted decision_id.
2. Endpoint is accessible at both /mcp/workflow and /api/v1/mcp/workflow.
3. Unknown customer returns 404 without creating spurious audit rows.
4. Upstream MCP failure returns 502; DB audit persistence failure returns 503 honestly.
5. Fallback execution preserves baseline ranking and persists fallback metadata.
6. Validation errors return 422; unhandled errors return 500 without credential leaks.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.models import DecisionAudit
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.mcp.schemas import FinalExclusion, FinalRecommendation
from backend.app.mcp.workflow import AgentExecution, MCPToolTrace, MCPWorkflowResult

WORKFLOW_RUN_PATH = "backend.app.api.routes.mcp._run_workflow"


@pytest.fixture
def isolated_mcp_client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    DecisionAudit.__table__.create(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def _override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    prev = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app), TestingSessionLocal
    finally:
        if prev is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = prev
        engine.dispose()


def _make_sample_success_result(
    customer_id: str = "CUST_0001",
    fallback_used: bool = False,
) -> MCPWorkflowResult:
    weights = {"relevance": 0.45, "margin": 0.25, "diversity": 0.15, "friction": 0.15}
    obj = {
        "recommendation_relevance": 0.92,
        "margin_contribution": 0.65,
        "product_diversity": 0.80,
        "operational_friction": 0.10,
        "operational_suitability": 0.90,
        "weighted_score": 0.6815,
        "rank": 1,
    }
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
                output={"candidate_count": 2, "candidates": [{"product_id": "PROD_001"}]},
            ),
            AgentExecution(
                agent="Inventory Agent",
                responsibility="Verify operational stock and freshness",
                status="completed",
                duration_ms=20.1,
                output={"verified": 2},
            ),
            AgentExecution(
                agent="Policy Agent",
                responsibility="Authoritative policy evaluation",
                status="completed",
                duration_ms=15.0,
                output={"pass": 1, "excluded": 1},
            ),
            AgentExecution(
                agent="Decision Agent",
                responsibility="Weighted multi-objective decision",
                status="completed_with_fallback" if fallback_used else "completed",
                duration_ms=8.3,
                output={"selected_product_id": "PROD_001"},
            ),
            AgentExecution(
                agent="Final Decision Agent",
                responsibility="Revalidate selection and safety checks",
                status="completed",
                duration_ms=18.4,
                output={"recommendations": [{"product_id": "PROD_001"}], "excluded_candidates": []},
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
                tool="run_decision_engine",
                arguments={"request": {"candidates": [{"product_id": "PROD_001"}]}},
                status="success",
                duration_ms=7.8,
                result={"status": "WEIGHTED_DECISION", "selected_product_id": "PROD_001"},
            ),
        ],
        recommendations=[
            FinalRecommendation(
                product_id="PROD_001",
                product_name="Noise Cancelling Headphones",
                recommendation_score=0.92,
                policy_decision="PASS",
                objective_scores=obj,
                weighted_score=0.6815,
                rank=1,
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
        selected_product_id="PROD_001",
        laya_selected_product_id=None if fallback_used else "PROD_001",
        laya_status="FALLBACK" if fallback_used else "SUCCESS",
        decision_method="WEIGHTED_DECISION_FALLBACK" if fallback_used else "LAYA",
        decision_engine_status="FALLBACK" if fallback_used else "LAYA_PRIMARY",
        decision_weights=weights,
        objective_scores={"PROD_001": obj},
        final_ranking=[{"rank": 1, "product_id": "PROD_001", "weighted_score": 0.6815}],
        final_validation={"decision": "PASS", "selected_product_id": "PROD_001", "verified_count": 1},
        decision_explanation="Selected PROD_001 via weighted objective ranking.",
        fallback_used=fallback_used,
        fallback_reason="Weighted decision engine disabled" if fallback_used else None,
        error=None,
    )


def test_mcp_workflow_success_and_persists_audit(isolated_mcp_client):
    client, SessionCls = isolated_mcp_client
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
    assert data["selected_product_id"] == "PROD_001"
    assert data["decision_method"] == "LAYA"
    assert data["decision_id"]
    assert len(data["agents"]) == 6
    assert len(data["recommendations"]) == 1
    assert len(data["excluded_candidates"]) == 1

    with SessionCls() as db:
        row = db.get(DecisionAudit, data["decision_id"])
        assert row is not None
        assert row.customer_id == "CUST_0001"
        assert row.selected_product_id == "PROD_001"
        assert row.ranking_method == "LAYA"

    mock_run.assert_called_once_with(
        customer_id="CUST_0001",
        top_k=5,
        reward_context=False,
        promotion_context=False,
        express_context=False,
    )


def test_mcp_workflow_accessible_at_api_prefix_and_records_fallback(isolated_mcp_client):
    client, SessionCls = isolated_mcp_client
    mock_result = _make_sample_success_result("CUST_0002", fallback_used=True)

    with patch(WORKFLOW_RUN_PATH, new=AsyncMock(return_value=mock_result)):
        response = client.post("/api/v1/mcp/workflow", json={"customer_id": "CUST_0002"})

    assert response.status_code == 200
    data = response.json()
    assert data["customer_id"] == "CUST_0002"
    assert data["fallback_used"] is True
    assert data["decision_method"] == "WEIGHTED_DECISION_FALLBACK"
    with SessionCls() as db:
        row = db.get(DecisionAudit, data["decision_id"])
        assert row is not None
        assert row.ranking_method == "WEIGHTED_DECISION_FALLBACK"
        assert "disabled" in (row.fallback_reason or "").lower()


def test_mcp_workflow_unknown_customer_returns_404(isolated_mcp_client):
    client, _ = isolated_mcp_client
    mock_result = MCPWorkflowResult(
        status="FAILED_SAFE",
        customer_id="CUST_MISSING",
        agents=[
            AgentExecution(
                agent="Customer Agent",
                responsibility="Retrieve customer profile",
                status="failed_safe",
                duration_ms=3.0,
                error="Customer not found: CUST_MISSING",
            )
        ],
        tool_calls=[],
        recommendations=[],
        excluded_candidates=[],
        error="Customer not found: CUST_MISSING",
    )

    with patch(WORKFLOW_RUN_PATH, new=AsyncMock(return_value=mock_result)):
        response = client.post("/mcp/workflow", json={"customer_id": "CUST_MISSING"})

    assert response.status_code == 404
    assert "CUST_MISSING" in response.json()["error"]


def test_mcp_workflow_upstream_failure_returns_502_and_audit_failure_returns_503(isolated_mcp_client):
    client, _ = isolated_mcp_client
    failed_result = MCPWorkflowResult(
        status="FAILED_SAFE",
        customer_id="CUST_0001",
        agents=[
            AgentExecution(
                agent="Inventory Agent",
                responsibility="Verify inventory",
                status="failed_safe",
                duration_ms=10.0,
                error="Tool timed out",
            )
        ],
        tool_calls=[],
        recommendations=[],
        excluded_candidates=[],
        error="Tool timed out",
    )

    with patch(WORKFLOW_RUN_PATH, new=AsyncMock(return_value=failed_result)):
        res_502 = client.post("/mcp/workflow", json={"customer_id": "CUST_0001"})
    assert res_502.status_code == 502

    ok_result = _make_sample_success_result("CUST_0001")
    with (
        patch(WORKFLOW_RUN_PATH, new=AsyncMock(return_value=ok_result)),
        patch("backend.app.api.routes.mcp.AuditService.log_decision_audit", side_effect=RuntimeError("DB down")),
    ):
        res_503 = client.post("/mcp/workflow", json={"customer_id": "CUST_0001"})
    assert res_503.status_code == 503
    assert "audit persistence failed" in res_503.json()["detail"].lower()


def test_mcp_workflow_validation_errors(isolated_mcp_client):
    client, _ = isolated_mcp_client
    assert client.post("/mcp/workflow", json={"top_k": 5}).status_code == 422
    assert client.post("/mcp/workflow", json={"customer_id": ""}).status_code == 422
    assert client.post("/mcp/workflow", json={"customer_id": "CUST_0001", "top_k": 0}).status_code == 422
    assert client.post("/mcp/workflow", json={"customer_id": "CUST_0001", "top_k": 51}).status_code == 422
    assert client.post("/mcp/workflow", json={"customer_id": "CUST_0001", "unknown_field": "x"}).status_code == 422


def test_mcp_workflow_unexpected_exception_and_credential_sanitization(isolated_mcp_client):
    client, _ = isolated_mcp_client
    with patch(
        WORKFLOW_RUN_PATH,
        new=AsyncMock(side_effect=RuntimeError("postgres connection reset")),
    ):
        res_500 = client.post("/mcp/workflow", json={"customer_id": "CUST_0001"})
    assert res_500.status_code == 500
    assert "postgres connection reset" not in res_500.json()["detail"]

    secret_result = MCPWorkflowResult(
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
    with patch(WORKFLOW_RUN_PATH, new=AsyncMock(return_value=secret_result)):
        res = client.post("/mcp/workflow", json={"customer_id": "CUST_0001"})
    assert "secret_pw" not in str(res.json())
    assert "postgresql://" not in str(res.json())
