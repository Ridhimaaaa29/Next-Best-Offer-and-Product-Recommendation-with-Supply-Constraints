"""
Integration & API tests for weighted decision routes and PostgreSQL/SQLAlchemy DecisionAudit persistence.
Tests:
- GET /api/v1/decisions/status & /laya/status alias
- POST /api/v1/recommend DB persistence + weighted scores + fallback persistence
- POST /api/v1/decisions/optimize DB persistence
- POST /api/v1/decisions/history, GET /api/v1/decisions/history, PATCH /approval
- 6-stage MCP _run_workflow end-to-end execution with mocked MCPClient tools and fallback handling
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.models import DecisionAudit
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.mcp.schemas import (
    CustomerContext,
    CustomerProfile,
    DecisionEngineOutput,
    FinalizeOutput,
    FinalRecommendation,
    InventoryDetails,
    PolicyOutput,
    RecommendationOutput,
    ScoredCandidate,
)
from backend.app.mcp.workflow import _run_workflow


@pytest.fixture
def audit_client():
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


def _sample_decision_output(fallback_used: bool = False) -> dict:
    obj = {
        "recommendation_relevance": 0.90,
        "margin_contribution": 0.65,
        "product_diversity": 0.85,
        "operational_friction": 0.12,
        "operational_suitability": 0.88,
        "weighted_score": 0.677,
        "rank": 1,
    }
    rec = {
        "product_id": "PROD_0010",
        "product_name": "Studio Headphones",
        "category": "Electronics",
        "subcategory": "Audio",
        "brand": "AudioMax",
        "unit_price": 199.99,
        "product_rating": 4.8,
        "product_popularity": 0.91,
        "product_status": "active",
        "recommendation_score": 0.90,
        "policy_decision": "PASS",
        "policy_reasons": [],
        "score_explanation": {
            "category_affinity_score": 0.9,
            "popularity_score": 0.91,
            "rating_score": 0.96,
            "interaction_bonus": 0.8,
            "composite_score": 0.90,
            "reason_codes": ["ML propensity 0.90"],
        },
        "objective_scores": {} if fallback_used else obj,
        "weighted_score": None if fallback_used else 0.677,
        "rank": 1,
    }
    return {
        "status": "SUCCESS",
        "customer_id": "CUST_0001",
        "candidate_count": 2,
        "feasible_count": 1,
        "excluded_count": 1,
        "top_k_requested": 5,
        "recommendations": [rec],
        "feasible_candidates": [rec],
        "excluded_candidates": [
            {
                "product_id": "PROD_0002",
                "product_name": "Depleted Speaker",
                "category": "Electronics",
                "recommendation_score": 0.85,
                "policy_decision": "EXCLUDE",
                "policy_reasons": ["Product is out of stock."],
            }
        ],
        "all_evaluated_candidates": [rec],
        "decision_method": "WEIGHTED_DECISION_FALLBACK" if fallback_used else "LAYA",
        "laya_status": "FALLBACK" if fallback_used else "SUCCESS",
        "decision_engine_status": "FALLBACK" if fallback_used else "LAYA_PRIMARY",
        "laya_selected_product": None if fallback_used else rec,
        "selected_product": rec,
        "decision_weights": None if fallback_used else {"relevance": 0.45, "margin": 0.25, "diversity": 0.15, "friction": 0.15},
        "objective_scores": {} if fallback_used else {"PROD_0010": obj},
        "final_ranking": [{"rank": 1, "product_id": "PROD_0010", "weighted_score": rec["weighted_score"]}],
        "final_validation": {"decision": "PASS", "reasons": [], "flags": []},
        "decision_explanation": "Fallback baseline applied." if fallback_used else "Weighted engine selected PROD_0010.",
        "fallback_used": fallback_used,
        "fallback_reason": "Engine failure injected" if fallback_used else None,
    }


def test_decisions_status_and_alias(audit_client):
    client, _ = audit_client
    res = client.get("/api/v1/decisions/status")
    alias = client.get("/api/v1/laya/status")

    assert res.status_code == 200
    assert alias.status_code == 200
    payload = res.json()
    assert payload == alias.json()
    assert payload["engine"] == "laya"
    assert payload["vega_disabled"] is True
    assert payload["preload"] is False
    assert payload["fallback_engine"] == "lightweight_weighted_decision_engine"


def test_recommend_and_optimize_persist_audits_and_history_endpoints(audit_client):
    client, _ = audit_client

    with patch("backend.app.api.routes.recommendations.DecisionModule") as mock_dm:
        mock_dm.return_value.decide.return_value = _sample_decision_output(fallback_used=False)
        res = client.post("/api/v1/recommend", json={"customer_id": "CUST_0001", "top_k": 5})

    assert res.status_code == 200
    body = res.json()
    decision_id = body["decision_id"]
    assert decision_id
    assert body["decision_method"] == "LAYA"
    assert body["laya_status"] == "SUCCESS"
    assert body["fallback_used"] is False
    assert body["recommendations"][0]["weighted_score"] == 0.677

    # Fallback run also persisted with fallback_reason
    with patch("backend.app.api.routes.recommendations.DecisionModule") as mock_dm:
        mock_dm.return_value.decide.return_value = _sample_decision_output(fallback_used=True)
        res_fb = client.post("/api/v1/recommend", json={"customer_id": "CUST_0001", "top_k": 5})
    assert res_fb.status_code == 200
    fb_body = res_fb.json()
    assert fb_body["fallback_used"] is True
    assert fb_body["fallback_reason"] == "Engine failure injected"

    # Manual audit POST
    manual_res = client.post(
        "/api/v1/decisions/history",
        json={
            "customer_id": "CUST_0001",
            "status": "SUCCESS",
            "selected_product_id": "PROD_0010",
            "ranking_method": "MANUAL_GOVERNANCE_AUDIT",
            "approval_status": "APPROVED",
            "recommendations": [{"product_id": "PROD_0010", "product_name": "Studio Headphones", "weighted_score": 0.677}],
        },
    )
    assert manual_res.status_code == 201
    manual_id = manual_res.json()["decision_id"]
    assert manual_res.json()["approval_status"] == "APPROVED"

    # Query GET /decisions/history and verify records & metadata
    hist_res = client.get("/api/v1/decisions/history", params={"customer_id": "CUST_0001", "limit": 10})
    assert hist_res.status_code == 200
    ids = {row["decision_id"] for row in hist_res.json()}
    assert {decision_id, fb_body["decision_id"], manual_id}.issubset(ids)

    # Approve via PATCH
    patch_res = client.patch(
        f"/api/v1/decisions/history/{decision_id}/approval",
        json={"approval_status": "APPROVED"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["approval_status"] == "APPROVED"

    # Optimize endpoint
    with patch("backend.app.api.routes.decisions.DecisionModule") as mock_opt_dm:
        mock_opt_dm.return_value.decide.return_value = _sample_decision_output(fallback_used=False)
        opt_res = client.post("/api/v1/decisions/optimize", json={"customer_id": "CUST_0001", "top_k": 5})
    assert opt_res.status_code == 200
    assert opt_res.json()["decision_id"]


def test_mcp_six_stage_workflow_runs_with_fallback_on_engine_error():
    class FakeMCPClient:
        def __init__(self, fail_decision_tool: bool = False):
            self.fail_decision_tool = fail_decision_tool
            self.server_tools = {
                "get_customer_context",
                "generate_recommendations",
                "get_inventory_details",
                "evaluate_policy",
                "run_laya_decision",
                "finalize_decision",
            }
            self.traces = []

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def call_tool(self, name, arg, out_cls):
            if name == "get_customer_context":
                return CustomerContext(
                    customer=CustomerProfile(
                        customer_id="CUST_0001",
                        customer_segment="High-Value Enthusiast",
                        age_group="25-34",
                        location="Austin, TX",
                        membership_tier="Gold",
                        reward_points=500,
                        preferred_category="Electronics",
                        average_order_value=140.0,
                        total_orders=5,
                        total_spend=700.0,
                        last_purchase_date="2026-06-01T00:00:00",
                        customer_status="active",
                    ),
                    interactions=[],
                )
            if name == "generate_recommendations":
                return RecommendationOutput(
                    customer_id="CUST_0001",
                    candidate_count=2,
                    candidates=[
                        ScoredCandidate(
                            product_id="PROD_PASS",
                            product_name="Valid Item",
                            category="Electronics",
                            subcategory="Audio",
                            brand="BrandA",
                            unit_price=120.0,
                            product_rating=4.6,
                            product_popularity=0.8,
                            product_status="active",
                            recommendation_score=0.90,
                            score_breakdown={},
                        ),
                        ScoredCandidate(
                            product_id="PROD_FAIL",
                            product_name="Zero Stock Item",
                            category="Electronics",
                            subcategory="Audio",
                            brand="BrandA",
                            unit_price=80.0,
                            product_rating=4.2,
                            product_popularity=0.7,
                            product_status="active",
                            recommendation_score=0.95,
                            score_breakdown={},
                        ),
                    ],
                )
            if name == "get_inventory_details":
                if arg.product_id == "PROD_PASS":
                    return InventoryDetails(
                        product_id="PROD_PASS",
                        product_status="active",
                        available_stock=15,
                        inventory_status="available",
                        gross_margin_pct=0.45,
                        shipping_days=2,
                        reward_eligible=True,
                        promotion_eligible=True,
                        data_freshness_status="verified_fresh",
                        verification_status="verified",
                    )
                return InventoryDetails(
                    product_id="PROD_FAIL",
                    product_status="active",
                    available_stock=0,
                    inventory_status="out_of_stock",
                    gross_margin_pct=0.45,
                    shipping_days=2,
                    reward_eligible=True,
                    promotion_eligible=True,
                    data_freshness_status="verified_fresh",
                    verification_status="verified",
                )
            if name == "evaluate_policy":
                if arg.product_id == "PROD_PASS":
                    return PolicyOutput(product_id="PROD_PASS", decision="PASS", reasons=[], flags=[])
                return PolicyOutput(product_id="PROD_FAIL", decision="EXCLUDE", reasons=["Product is out of stock."], flags=[])
            if name == "run_laya_decision":
                if self.fail_decision_tool:
                    from backend.app.mcp.client import MCPToolError

                    raise MCPToolError("Injected Laya tool timeout")
                assert [c.product_id for c in arg.candidates] == ["PROD_PASS"]
                return DecisionEngineOutput(
                    status="LAYA",
                    selected_product_id="PROD_PASS",
                    explanation="Laya picked PROD_PASS.",
                    weights={"relevance": 0.45, "margin": 0.25, "diversity": 0.15, "friction": 0.15},
                    objective_scores={"PROD_PASS": {"weighted_score": 0.72, "rank": 1}},
                    ranked_candidates=[{"product_id": "PROD_PASS", "product_name": "Valid Item", "recommendation_score": 0.90, "weighted_score": 0.72, "rank": 1}],
                )
            if name == "finalize_decision":
                return FinalizeOutput(
                    status="SUCCESS",
                    recommendations=[
                        FinalRecommendation(
                            product_id=c.product_id,
                            product_name=c.product_name,
                            recommendation_score=c.recommendation_score,
                            policy_decision="PASS",
                            weighted_score=c.weighted_score,
                            rank=c.rank,
                        )
                        for c in arg.candidates
                    ],
                    excluded_candidates=[],
                )
            raise AssertionError(f"Unexpected tool call: {name}")

    with patch("backend.app.mcp.workflow.MCPClient", return_value=FakeMCPClient(fail_decision_tool=False)):
        res = asyncio.run(_run_workflow("CUST_0001", top_k=5, reward_context=False, promotion_context=False, express_context=False))
    assert res.status == "SUCCESS"
    assert [a.agent for a in res.agents] == [
        "Customer Agent",
        "Recommendation Agent",
        "Inventory Agent",
        "Policy Agent",
        "Decision Agent",
        "Final Decision Agent",
    ]
    assert res.selected_product_id == "PROD_PASS"
    assert res.laya_selected_product_id == "PROD_PASS"
    assert res.decision_method == "LAYA"
    assert res.fallback_used is False
    assert [e.product_id for e in res.excluded_candidates] == ["PROD_FAIL"]

    with patch("backend.app.mcp.workflow.MCPClient", return_value=FakeMCPClient(fail_decision_tool=True)):
        res_fb = asyncio.run(_run_workflow("CUST_0001", top_k=5, reward_context=False, promotion_context=False, express_context=False))
    assert res_fb.status == "SUCCESS"
    assert res_fb.fallback_used is True
    assert res_fb.decision_method == "WEIGHTED_DECISION_FALLBACK"
    assert "Injected Laya tool timeout" in (res_fb.fallback_reason or "")
    assert res_fb.selected_product_id == "PROD_PASS"


def test_in_process_mcp_client_connects_over_memory_transport():
    from backend.app.mcp.client import MCPClient

    async def _check():
        async with MCPClient(transport="memory") as client:
            return client.server_tools

    tools = asyncio.run(_check())
    assert {
        "get_customer_context",
        "generate_recommendations",
        "get_inventory_details",
        "evaluate_policy",
        "run_laya_decision",
        "finalize_decision",
    }.issubset(set(tools))


def test_environment_aware_local_vs_production_decision_status_and_health(audit_client):
    import os
    from backend.app.decision.laya_adapter import LayaAdapter

    client, _ = audit_client
    LayaAdapter.reset_shared_instance()

    # 1. Production / Render Free (APP_ENV=production -> Laya disabled by default)
    with (
        patch.dict(os.environ, {"APP_ENV": "production"}, clear=False),
        patch("backend.app.api.routes.health.check_database_connection", return_value=True),
    ):
        os.environ.pop("LAYA_ENABLED", None)
        status_res = client.get("/api/v1/decisions/status")
        health_res = client.get("/api/v1/health")
    assert status_res.status_code == 200
    st_prod = status_res.json()
    assert st_prod["app_env"] == "production"
    assert st_prod["laya_available"] is False
    assert st_prod["loaded"] is False
    assert st_prod["decision_provider"] == "lightweight_weighted_decision_engine"
    assert "512 mb" in (st_prod["reason"] or "").lower()

    assert health_res.status_code == 200
    h_prod = health_res.json()
    assert h_prod["app_env"] == "production"
    assert h_prod["laya_available"] is False
    assert h_prod["laya_loaded"] is False
    assert h_prod["decision_provider"] == "lightweight_weighted_decision_engine"

    # 2. Local environment (APP_ENV=local -> Laya available lazily)
    with (
        patch.dict(os.environ, {"APP_ENV": "local", "LAYA_ENABLED": "true"}, clear=False),
        patch("backend.app.api.routes.health.check_database_connection", return_value=True),
    ):
        status_local = client.get("/api/v1/decisions/status")
        health_local = client.get("/api/v1/health")
    assert status_local.json()["laya_available"] is True
    assert status_local.json()["decision_provider"] == "laya"
    assert status_local.json()["loaded"] is False
    assert health_local.json()["laya_available"] is True
    assert health_local.json()["decision_provider"] == "laya"

    # 3. AWS full-featured environment (APP_ENV=aws -> Laya enabled even without LAYA_ENABLED override)
    with (
        patch.dict(os.environ, {"APP_ENV": "aws", "LAYA_PRELOAD_ON_STARTUP": "true"}, clear=False),
        patch("backend.app.api.routes.health.check_database_connection", return_value=True),
    ):
        os.environ.pop("LAYA_ENABLED", None)
        status_aws = client.get("/api/v1/decisions/status")
        health_aws = client.get("/api/v1/health")
    assert status_aws.status_code == 200
    st_aws = status_aws.json()
    assert st_aws["app_env"] == "aws"
    assert st_aws["laya_available"] is True
    assert st_aws["preload"] is True
    assert st_aws["decision_provider"] == "laya"
    assert health_aws.json()["app_env"] == "aws"
    assert health_aws.json()["laya_available"] is True


def test_lifespan_preloads_laya_when_enabled():
    import asyncio
    import os
    from backend.app.main import app, lifespan

    with (
        patch.dict(os.environ, {"APP_ENV": "aws", "LAYA_ENABLED": "true", "LAYA_PRELOAD_ON_STARTUP": "true"}, clear=False),
        patch("backend.app.main.LayaAdapter.warmup", return_value={"warmed": True, "loaded": True}) as mock_warmup,
    ):
        async def _run():
            async with lifespan(app):
                return True

        assert asyncio.run(_run()) is True
        mock_warmup.assert_called_once()
