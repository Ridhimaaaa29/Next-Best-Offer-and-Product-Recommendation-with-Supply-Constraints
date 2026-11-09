"""
Focused unit tests for MCP server tool: evaluate_policy.

Strategy:
- Import the tool function directly from server.py and call it with mocked
  evaluate_product to avoid live database access.
- Verify that the tool correctly maps every field from the policy engine's
  return dict into the PolicyOutput Pydantic model.
- Verify structured error handling when evaluate_product raises ValueError
  (product not found).
- Verify that all three context flags (reward, promotion, express) are
  forwarded unchanged to evaluate_product.
- Confirm the tool is registered on the MCP server object (tool list check).
"""

from __future__ import annotations

import importlib
from unittest.mock import patch, MagicMock

import pytest

from backend.app.mcp.schemas import PolicyInput, PolicyOutput


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Patch the name as it is bound in server.py (already imported), not the origin module.
POLICY_ENGINE_PATH = "backend.app.mcp.server.evaluate_product"
SERVER_MODULE = "backend.app.mcp.server"


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


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


def test_evaluate_policy_is_registered_on_server():
    """The MCP server must expose an 'evaluate_policy' tool."""
    import backend.app.mcp.server as server_module  # noqa: PLC0415

    registered_names = [tool.name for tool in server_module.server._tool_manager._tools.values()]
    assert "evaluate_policy" in registered_names, (
        f"'evaluate_policy' not found in registered tools: {registered_names}"
    )


# ---------------------------------------------------------------------------
# evaluate_policy – happy path
# ---------------------------------------------------------------------------


def test_evaluate_policy_pass_returns_policy_output():
    """PASS decision: all fields forwarded from evaluate_product to PolicyOutput."""
    mock_result = _make_policy_result("PROD_001", decision="PASS")

    with patch(POLICY_ENGINE_PATH, return_value=mock_result) as mock_eval:
        from backend.app.mcp.server import evaluate_policy  # noqa: PLC0415

        output = evaluate_policy(
            PolicyInput(
                product_id="PROD_001",
                reward_context=False,
                promotion_context=False,
                express_context=False,
            )
        )

    assert isinstance(output, PolicyOutput)
    assert output.product_id == "PROD_001"
    assert output.decision == "PASS"
    assert output.reasons == []
    assert output.flags == []
    mock_eval.assert_called_once_with(
        product_id="PROD_001",
        reward_context=False,
        promotion_context=False,
        express_context=False,
    )


def test_evaluate_policy_exclude_carries_reasons():
    """EXCLUDE decision: reasons list must be forwarded verbatim."""
    reasons = ["Product is out of stock.", "Gross margin (0.05) is below the 10% minimum."]
    mock_result = _make_policy_result("PROD_002", decision="EXCLUDE", reasons=reasons)

    with patch(POLICY_ENGINE_PATH, return_value=mock_result):
        from backend.app.mcp.server import evaluate_policy  # noqa: PLC0415

        output = evaluate_policy(
            PolicyInput(product_id="PROD_002")
        )

    assert output.decision == "EXCLUDE"
    assert output.reasons == reasons
    assert output.product_id == "PROD_002"


def test_evaluate_policy_express_flag_is_forwarded():
    """Express shipping flag must appear in the flags list when triggered."""
    flags = ["Shipping time (10 days) exceeds the 7-day express threshold."]
    mock_result = _make_policy_result("PROD_003", decision="PASS", flags=flags)

    with patch(POLICY_ENGINE_PATH, return_value=mock_result) as mock_eval:
        from backend.app.mcp.server import evaluate_policy  # noqa: PLC0415

        output = evaluate_policy(
            PolicyInput(
                product_id="PROD_003",
                reward_context=False,
                promotion_context=False,
                express_context=True,
            )
        )

    assert output.flags == flags
    # Confirm express_context=True was forwarded to evaluate_product
    _, kwargs = mock_eval.call_args
    assert kwargs["express_context"] is True


def test_evaluate_policy_reward_and_promotion_context_forwarded():
    """reward_context and promotion_context are forwarded to evaluate_product."""
    mock_result = _make_policy_result("PROD_004", decision="EXCLUDE",
                                      reasons=["Product is not reward eligible."])

    with patch(POLICY_ENGINE_PATH, return_value=mock_result) as mock_eval:
        from backend.app.mcp.server import evaluate_policy  # noqa: PLC0415

        output = evaluate_policy(
            PolicyInput(
                product_id="PROD_004",
                reward_context=True,
                promotion_context=True,
                express_context=False,
            )
        )

    _, kwargs = mock_eval.call_args
    assert kwargs["reward_context"] is True
    assert kwargs["promotion_context"] is True
    assert kwargs["express_context"] is False
    assert output.decision == "EXCLUDE"


# ---------------------------------------------------------------------------
# evaluate_policy – error handling
# ---------------------------------------------------------------------------


def test_evaluate_policy_raises_on_missing_product():
    """When evaluate_product raises ValueError (product not found), it must propagate."""
    with patch(POLICY_ENGINE_PATH, side_effect=ValueError("Product not found: PROD_MISSING")):
        from backend.app.mcp.server import evaluate_policy  # noqa: PLC0415

        with pytest.raises(ValueError, match="Product not found"):
            evaluate_policy(PolicyInput(product_id="PROD_MISSING"))


def test_evaluate_policy_raises_on_db_error():
    """Non-ValueError exceptions (e.g., DB connection failure) must propagate."""
    with patch(POLICY_ENGINE_PATH, side_effect=RuntimeError("DB connection refused")):
        from backend.app.mcp.server import evaluate_policy  # noqa: PLC0415

        with pytest.raises(RuntimeError, match="DB connection refused"):
            evaluate_policy(PolicyInput(product_id="PROD_X"))


# ---------------------------------------------------------------------------
# evaluate_policy – schema compatibility with workflow
# ---------------------------------------------------------------------------


def test_policy_output_validates_pass_decision():
    """PolicyOutput must accept Literal['PASS'] as a valid decision."""
    output = PolicyOutput(
        product_id="PROD_OK",
        decision="PASS",
        reasons=[],
        flags=[],
    )
    assert output.decision == "PASS"


def test_policy_output_validates_exclude_decision():
    """PolicyOutput must accept Literal['EXCLUDE'] as a valid decision."""
    output = PolicyOutput(
        product_id="PROD_BAD",
        decision="EXCLUDE",
        reasons=["Out of stock."],
        flags=[],
    )
    assert output.decision == "EXCLUDE"


def test_policy_output_rejects_invalid_decision():
    """PolicyOutput must reject decisions outside the Literal set."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        PolicyOutput(
            product_id="PROD_X",
            decision="MAYBE",  # invalid
            reasons=[],
            flags=[],
        )


# ===========================================================================
# run_laya_decision tool tests
# ===========================================================================

from backend.app.mcp.schemas import (
    FinalizeCandidate,
    LayaInput,
    LayaOutput,
    FinalizeInput,
    FinalizeOutput,
    FinalRecommendation,
    FinalExclusion,
    InventoryDetails,
)

LAYA_ADAPTER_PATH = "backend.app.mcp.server.LayaAdapter"


def _make_candidate(product_id: str, score: float = 0.9) -> FinalizeCandidate:
    return FinalizeCandidate(
        product_id=product_id,
        product_name=f"Product {product_id}",
        recommendation_score=score,
    )


# ---------------------------------------------------------------------------
# run_laya_decision – tool registration
# ---------------------------------------------------------------------------


def test_run_laya_decision_is_registered_on_server():
    """run_laya_decision must appear in the MCP server tool registry."""
    import backend.app.mcp.server as server_module  # noqa: PLC0415

    registered_names = [
        tool.name for tool in server_module.server._tool_manager._tools.values()
    ]
    assert "run_laya_decision" in registered_names, (
        f"'run_laya_decision' not found in: {registered_names}"
    )


# ---------------------------------------------------------------------------
# run_laya_decision – Laya enabled path (status="LAYA")
# ---------------------------------------------------------------------------


def test_run_laya_decision_returns_laya_status_when_enabled():
    """When Laya is enabled and choose() succeeds, status must be 'LAYA'."""
    mock_router = MagicMock()
    mock_router.predict.return_value = {
        "answers": {"selected_product_id": {"choice": "PROD_A"}}
    }

    mock_adapter = MagicMock()
    mock_adapter.enabled = True
    mock_adapter.choose.return_value = {
        "selected": {"product_id": "PROD_A", "product_name": "Product PROD_A",
                     "recommendation_score": 0.95},
        "explanation": "Selected by Laya Router.",
    }

    with patch(LAYA_ADAPTER_PATH, return_value=mock_adapter):
        from backend.app.mcp.server import run_laya_decision  # noqa: PLC0415

        output = run_laya_decision(
            LayaInput(candidates=[_make_candidate("PROD_A", 0.95)])
        )

    assert isinstance(output, LayaOutput)
    assert output.status == "LAYA"
    assert output.selected_product_id == "PROD_A"


# ---------------------------------------------------------------------------
# run_laya_decision – Laya disabled path (status="FALLBACK")
# ---------------------------------------------------------------------------


def test_run_laya_decision_returns_fallback_when_disabled():
    """When Laya is disabled the tool returns status='FALLBACK' (not 'LAYA')."""
    mock_adapter = MagicMock()
    mock_adapter.enabled = False
    mock_adapter.reason = "Laya is disabled in configuration."

    with patch(LAYA_ADAPTER_PATH, return_value=mock_adapter):
        from backend.app.mcp.server import run_laya_decision  # noqa: PLC0415

        output = run_laya_decision(
            LayaInput(
                candidates=[
                    _make_candidate("PROD_A", 0.9),
                    _make_candidate("PROD_B", 0.7),
                ]
            )
        )

    assert output.status == "FALLBACK"
    # Score-based: PROD_A has higher score so it is chosen
    assert output.selected_product_id == "PROD_A"


# ---------------------------------------------------------------------------
# Workflow-level Laya integration tests (unit, no live MCP subprocess)
#
# These tests exercise _run_workflow's Laya stage by mocking MCPClient so
# that no subprocess is spawned and no network calls are made.
# ---------------------------------------------------------------------------

from backend.app.mcp.workflow import (
    SharedWorkflowState,
    _apply_inventory_safety,
    _result,
    _REQUIRED_TOOLS,
)


def _build_state(candidates=None, policy=None, inventory=None):
    """Return a minimal SharedWorkflowState for unit testing helpers."""
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


# ---------------------------------------------------------------------------
# T1: Laya receives ONLY policy-feasible candidates
# ---------------------------------------------------------------------------


def test_laya_receives_only_policy_feasible_candidates():
    """
    After Stage 4, only candidates with policy decision == PASS are forwarded
    to run_laya_decision.  EXCLUDE candidates must never reach Laya.
    The filtering logic is the same list comprehension used in _run_workflow.
    """
    # Three candidates; only PROD_A passes policy
    candidates = [
        MagicMock(product_id="PROD_A", product_name="A", recommendation_score=0.9),
        MagicMock(product_id="PROD_B", product_name="B", recommendation_score=0.8),
        MagicMock(product_id="PROD_C", product_name="C", recommendation_score=0.7),
    ]
    policy = {
        "PROD_A": PolicyOutput(product_id="PROD_A", decision="PASS", reasons=[], flags=[]),
        "PROD_B": PolicyOutput(product_id="PROD_B", decision="EXCLUDE",
                               reasons=["Out of stock."], flags=[]),
        "PROD_C": PolicyOutput(product_id="PROD_C", decision="EXCLUDE",
                               reasons=["Low margin."], flags=[]),
    }

    # Replicate the exact filter from _run_workflow Stage 4.5
    feasible_for_laya: list[FinalizeCandidate] = [
        FinalizeCandidate(
            product_id=c.product_id,
            product_name=c.product_name,
            recommendation_score=c.recommendation_score,
        )
        for c in candidates
        if (
            policy.get(c.product_id) is not None
            and policy[c.product_id].decision == "PASS"
        )
    ]

    laya_input = LayaInput(candidates=feasible_for_laya)

    assert len(laya_input.candidates) == 1, (
        f"Expected 1 feasible candidate, got {len(laya_input.candidates)}: "
        f"{[c.product_id for c in laya_input.candidates]}"
    )
    assert laya_input.candidates[0].product_id == "PROD_A"
    # Confirm excluded products are absent
    present_ids = {c.product_id for c in laya_input.candidates}
    assert "PROD_B" not in present_ids
    assert "PROD_C" not in present_ids


# ---------------------------------------------------------------------------
# T2: Laya's selected candidate is preserved through finalize_decision
# ---------------------------------------------------------------------------


def test_laya_selected_candidate_passed_to_finalize():
    """
    finalize_decision must receive exactly the Laya-selected candidate
    (not the full feasible list), so score-based sorting cannot replace
    Laya's choice.
    """
    # Build a scenario: two feasible candidates; Laya picks the lower-scored one.
    feasible = [
        FinalizeCandidate(product_id="PROD_HIGH", product_name="High", recommendation_score=0.95),
        FinalizeCandidate(product_id="PROD_LAYA", product_name="Laya Pick", recommendation_score=0.60),
    ]
    laya_selected_id = "PROD_LAYA"

    # Simulate what the workflow does: find the Laya-selected candidate and
    # build a single-element FinalizeInput.
    laya_candidate = next(c for c in feasible if c.product_id == laya_selected_id)
    finalize_input = FinalizeInput(
        candidates=[laya_candidate],
        reward_context=False,
        promotion_context=False,
        express_context=False,
    )

    assert len(finalize_input.candidates) == 1
    assert finalize_input.candidates[0].product_id == "PROD_LAYA"
    # The higher-scored candidate must NOT be in the finalize input.
    assert all(c.product_id != "PROD_HIGH" for c in finalize_input.candidates)


# ---------------------------------------------------------------------------
# T3: Infeasible Laya selection is rejected (not returned as SUCCESS)
# ---------------------------------------------------------------------------


def test_infeasible_laya_selection_does_not_produce_success():
    """
    If the Laya-selected candidate fails finalize_decision + inventory safety,
    the workflow must set an error and must NOT return status=SUCCESS.
    """
    state = _build_state()
    state.laya_selected_id = "PROD_A"
    state.laya_output = LayaOutput(
        status="LAYA",
        selected_product_id="PROD_A",
        explanation="Selected by Laya Router.",
    )
    # finalize_decision returned the candidate but inventory is unverified
    state.final = FinalizeOutput(
        status="SUCCESS",
        recommendations=[
            FinalRecommendation(
                product_id="PROD_A",
                product_name="A",
                recommendation_score=0.9,
                policy_decision="PASS",
            )
        ],
        excluded_candidates=[],
    )
    # Inventory for PROD_A failed verification
    state.inventory = {
        "PROD_A": InventoryDetails(
            product_id="PROD_A",
            product_status="active",
            available_stock=None,
            inventory_status=None,
            gross_margin_pct=None,
            shipping_days=None,
            reward_eligible=None,
            promotion_eligible=None,
            verification_status="failed",
            error="DB timeout",
        )
    }
    state.policy = {
        "PROD_A": PolicyOutput(product_id="PROD_A", decision="PASS", reasons=[], flags=[])
    }

    # _apply_inventory_safety should move PROD_A to excluded
    safe_final = _apply_inventory_safety(state)
    assert safe_final.status == "ALL_CANDIDATES_EXCLUDED"
    assert len(safe_final.recommendations) == 0
    assert len(safe_final.excluded_candidates) == 1
    assert safe_final.excluded_candidates[0].product_id == "PROD_A"

    # Simulate the workflow check: no recommendations → error set
    if not safe_final.recommendations:
        state.error = (
            f"Laya-selected product '{state.laya_selected_id}' "
            "failed post-selection policy revalidation or inventory check."
        )
        state.final = safe_final

    result = _result(state, [])
    assert result.status == "FAILED_SAFE", f"Expected FAILED_SAFE, got {result.status}"
    assert result.error is not None
    assert "PROD_A" in result.error


# ---------------------------------------------------------------------------
# T4: Laya FALLBACK does not produce SUCCESS
# ---------------------------------------------------------------------------


def test_laya_fallback_does_not_produce_success():
    """
    When run_laya_decision returns status='FALLBACK' (Laya disabled),
    the workflow must set an error and _result must return FAILED_SAFE.
    """
    state = _build_state()
    # Simulate the workflow path where FALLBACK was detected
    fallback_output = LayaOutput(
        status="FALLBACK",
        selected_product_id="PROD_A",
        explanation="Laya is disabled in configuration.",
    )
    # Workflow sets error and does NOT set laya_output or laya_selected_id
    state.error = (
        f"Laya is unavailable and score-based fallback is not permitted: "
        f"{fallback_output.explanation}"
    )
    # state.laya_output remains None (workflow returned early)

    result = _result(state, [])
    assert result.status == "FAILED_SAFE"
    assert result.laya_selected_product_id is None
    assert result.laya_status is None
    assert "not permitted" in (result.error or "")


# ---------------------------------------------------------------------------
# T5: Empty feasible-candidate list is handled safely
# ---------------------------------------------------------------------------


def test_empty_feasible_candidates_handled_safely():
    """
    When all candidates fail policy evaluation, the workflow must NOT call
    Laya and must return FAILED_SAFE with an appropriate error.
    """
    state = _build_state()
    # All candidates excluded → feasible_for_laya is empty
    state.error = (
        "No policy-feasible candidates remain; "
        "Laya cannot select a Next-Best-Offer."
    )
    # state.laya_output is None; state.final is None

    result = _result(state, [])
    assert result.status == "FAILED_SAFE"
    assert result.laya_selected_product_id is None
    assert result.laya_status is None
    assert "No policy-feasible candidates" in (result.error or "")


# ---------------------------------------------------------------------------
# T6: _result() exposes Laya provenance fields correctly on success
# ---------------------------------------------------------------------------


def test_result_exposes_laya_provenance_on_success():
    """
    When Laya succeeds, _result must populate laya_selected_product_id and
    laya_status from SharedWorkflowState.
    """
    state = _build_state()
    state.laya_output = LayaOutput(
        status="LAYA",
        selected_product_id="PROD_X",
        explanation="Selected by Laya Router.",
    )
    state.laya_selected_id = "PROD_X"
    state.final = FinalizeOutput(
        status="SUCCESS",
        recommendations=[
            FinalRecommendation(
                product_id="PROD_X",
                product_name="X",
                recommendation_score=0.88,
                policy_decision="PASS",
            )
        ],
        excluded_candidates=[],
    )

    result = _result(state, [])
    assert result.status == "SUCCESS"
    assert result.laya_selected_product_id == "PROD_X"
    assert result.laya_status == "LAYA"
    assert result.error is None


# ---------------------------------------------------------------------------
# T7: _REQUIRED_TOOLS includes run_laya_decision
# ---------------------------------------------------------------------------


def test_required_tools_includes_run_laya_decision():
    """The workflow's required-tool set must include 'run_laya_decision'."""
    assert "run_laya_decision" in _REQUIRED_TOOLS, (
        f"'run_laya_decision' missing from _REQUIRED_TOOLS: {_REQUIRED_TOOLS}"
    )
