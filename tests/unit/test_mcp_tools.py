"""
Focused unit tests for MCP server tools and workflow safety invariants.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from backend.app.mcp.schemas import (
    DecisionCandidateInput,
    DecisionEngineInput,
    DecisionEngineOutput,
    FinalExclusion,
    FinalizeCandidate,
    FinalizeInput,
    FinalizeOutput,
    FinalRecommendation,
    InventoryDetails,
    PolicyInput,
    PolicyOutput,
)
from backend.app.mcp.workflow import (
    _REQUIRED_TOOLS,
    SharedWorkflowState,
    _apply_inventory_safety,
    _result,
)

POLICY_ENGINE_PATH = "backend.app.mcp.server.evaluate_product"
LAYA_ADAPTER_PATH = "backend.app.mcp.server.LayaAdapter"


def _make_policy_result(
    product_id: str,
    decision: str = "PASS",
    reasons: list[str] | None = None,
    flags: list[str] | None = None,
) -> dict:
    return {
        "product_id": product_id,
        "decision": decision,
        "reasons": reasons or [],
        "flags": flags or [],
    }


def _make_decision_candidate(product_id: str, score: float = 0.9) -> DecisionCandidateInput:
    return DecisionCandidateInput(
        product_id=product_id,
        product_name=f"Product {product_id}",
        recommendation_score=score,
        gross_margin_pct=0.45,
        available_stock=25,
        inventory_status="available",
        shipping_days=2,
        reorder_point=10,
    )


def test_evaluate_policy_is_registered_on_server():
    import backend.app.mcp.server as server_module

    registered_names = [tool.name for tool in server_module.server._tool_manager._tools.values()]
    assert "evaluate_policy" in registered_names


def test_evaluate_policy_pass_and_exclude_and_flags():
    from backend.app.mcp.server import evaluate_policy

    with patch(POLICY_ENGINE_PATH, return_value=_make_policy_result("PROD_001")) as mock_eval:
        output = evaluate_policy(PolicyInput(product_id="PROD_001"))
    assert output.decision == "PASS"
    mock_eval.assert_called_once()

    with patch(
        POLICY_ENGINE_PATH,
        return_value=_make_policy_result("PROD_002", decision="EXCLUDE", reasons=["Out of stock."]),
    ):
        output_ex = evaluate_policy(PolicyInput(product_id="PROD_002"))
    assert output_ex.decision == "EXCLUDE"
    assert output_ex.reasons == ["Out of stock."]

    with patch(
        POLICY_ENGINE_PATH,
        return_value=_make_policy_result("PROD_003", flags=["Shipping time (10 days) exceeds the 7-day express threshold."]),
    ):
        output_flag = evaluate_policy(PolicyInput(product_id="PROD_003", express_context=True))
    assert len(output_flag.flags) == 1


def test_evaluate_policy_propagates_errors():
    from backend.app.mcp.server import evaluate_policy

    with patch(POLICY_ENGINE_PATH, side_effect=ValueError("Product not found: PROD_MISSING")):
        with pytest.raises(ValueError, match="Product not found"):
            evaluate_policy(PolicyInput(product_id="PROD_MISSING"))


def test_policy_output_schema_validation():
    assert PolicyOutput(product_id="P", decision="PASS", reasons=[], flags=[]).decision == "PASS"
    with pytest.raises(ValidationError):
        PolicyOutput(product_id="P", decision="MAYBE", reasons=[], flags=[])


def test_run_laya_decision_registered_and_executes():
    import backend.app.mcp.server as server_module

    registered_names = [tool.name for tool in server_module.server._tool_manager._tools.values()]
    assert "run_laya_decision" in registered_names

    mock_adapter = MagicMock()
    mock_adapter.choose.return_value = {
        "selected": {"product_id": "PROD_A", "product_name": "Product PROD_A", "recommendation_score": 0.90},
        "selected_product_id": "PROD_A",
        "explanation": "Selected by Laya from shortlist.",
        "confidence": 0.91,
    }
    with patch(LAYA_ADAPTER_PATH, return_value=mock_adapter):
        output = server_module.run_laya_decision(
            DecisionEngineInput(
                candidates=[
                    _make_decision_candidate("PROD_A", 0.90),
                    _make_decision_candidate("PROD_B", 0.80),
                ]
            )
        )
    assert isinstance(output, DecisionEngineOutput)
    assert output.status == "LAYA"
    assert output.selected_product_id == "PROD_A"
    assert set(output.weights) == {"relevance", "margin", "diversity", "friction"}


def test_run_laya_decision_returns_weighted_fallback_when_unavailable():
    mock_adapter = MagicMock()
    mock_adapter.choose.side_effect = RuntimeError("Laya is disabled in configuration.")

    with patch(LAYA_ADAPTER_PATH, return_value=mock_adapter):
        from backend.app.mcp.server import run_laya_decision

        output = run_laya_decision(
            DecisionEngineInput(
                candidates=[
                    _make_decision_candidate("PROD_A", 0.9),
                    _make_decision_candidate("PROD_B", 0.7),
                ]
            )
        )

    assert output.status == "FALLBACK"
    assert output.selected_product_id == "PROD_A"
    assert "disabled" in (output.fallback_reason or "").lower()


def _build_state(candidates=None, policy=None, inventory=None):
    state = SharedWorkflowState(
        customer_id="CUST_TEST",
        top_k=5,
        reward_context=False,
        promotion_context=False,
        express_context=False,
    )
    if candidates is not None:
        state.recommendations = MagicMock()
        state.recommendations.candidates = candidates
    if policy is not None:
        state.policy = policy
    if inventory is not None:
        state.inventory = inventory
    return state


def test_inventory_safety_blocks_failed_unknown_zero_or_stale_inventory():
    base_rec = FinalRecommendation(
        product_id="PROD_A",
        product_name="A",
        recommendation_score=0.9,
        policy_decision="PASS",
    )
    for bad_inv in [
        InventoryDetails(
            product_id="PROD_A",
            product_status="active",
            available_stock=None,
            inventory_status=None,
            gross_margin_pct=None,
            shipping_days=None,
            reward_eligible=None,
            promotion_eligible=None,
            data_freshness_status=None,
            verification_status="failed",
            error="DB timeout",
        ),
        InventoryDetails(
            product_id="PROD_A",
            product_status="active",
            available_stock=20,
            inventory_status="available",
            gross_margin_pct=0.40,
            shipping_days=2,
            reward_eligible=True,
            promotion_eligible=True,
            data_freshness_status="stale",
            verification_status="verified",
        ),
        InventoryDetails(
            product_id="PROD_A",
            product_status="active",
            available_stock=20,
            inventory_status="available",
            gross_margin_pct=0.40,
            shipping_days=2,
            reward_eligible=True,
            promotion_eligible=True,
            data_freshness_status=None,
            verification_status="verified",
        ),
        InventoryDetails(
            product_id="PROD_A",
            product_status="active",
            available_stock=10,
            inventory_status="unknown",
            gross_margin_pct=0.40,
            shipping_days=2,
            reward_eligible=True,
            promotion_eligible=True,
            data_freshness_status="verified_fresh",
            verification_status="verified",
        ),
    ]:
        state = _build_state(
            policy={"PROD_A": PolicyOutput(product_id="PROD_A", decision="PASS", reasons=[], flags=[])},
            inventory={"PROD_A": bad_inv},
        )
        state.final = FinalizeOutput(status="SUCCESS", recommendations=[base_rec], excluded_candidates=[])
        safe = _apply_inventory_safety(state)
        assert safe.status == "ALL_CANDIDATES_EXCLUDED"
        assert safe.recommendations == []
        assert len(safe.excluded_candidates) == 1

    good_state = _build_state(
        policy={"PROD_A": PolicyOutput(product_id="PROD_A", decision="PASS", reasons=[], flags=[])},
        inventory={
            "PROD_A": InventoryDetails(
                product_id="PROD_A",
                product_status="active",
                available_stock=15,
                inventory_status="available",
                gross_margin_pct=0.40,
                shipping_days=2,
                reward_eligible=True,
                promotion_eligible=True,
                data_freshness_status="verified_fresh",
                verification_status="verified",
            )
        },
    )
    good_state.final = FinalizeOutput(status="SUCCESS", recommendations=[base_rec], excluded_candidates=[])
    safe_ok = _apply_inventory_safety(good_state)
    assert safe_ok.status == "SUCCESS"
    assert len(safe_ok.recommendations) == 1


def test_result_exposes_laya_provenance_and_required_tools():
    assert {
        "get_customer_context",
        "generate_recommendations",
        "get_inventory_details",
        "evaluate_policy",
        "run_laya_decision",
        "finalize_decision",
    }.issubset(_REQUIRED_TOOLS)

    state = _build_state()
    state.selected_product_id = "PROD_X"
    state.laya_selected_product_id = "PROD_X"
    state.laya_status = "SUCCESS"
    state.decision_method = "LAYA"
    state.decision_engine_status = "LAYA_PRIMARY"
    state.decision_weights = {"relevance": 0.45, "margin": 0.25, "diversity": 0.15, "friction": 0.15}
    state.final = FinalizeOutput(
        status="SUCCESS",
        recommendations=[
            FinalRecommendation(
                product_id="PROD_X",
                product_name="X",
                recommendation_score=0.88,
                policy_decision="PASS",
                weighted_score=0.79,
                rank=1,
            )
        ],
        excluded_candidates=[],
    )

    result = _result(state, [])
    assert result.status == "SUCCESS"
    assert result.selected_product_id == "PROD_X"
    assert result.laya_selected_product_id == "PROD_X"
    assert result.laya_status == "SUCCESS"
    assert result.decision_method == "LAYA"
    assert result.error is None
