"""Sequential deterministic agents that communicate only through MCP tools.

Six-Stage Architecture:
  Stage 1 – Customer Agent       : get_customer_context
  Stage 2 – Recommendation Agent : generate_recommendations
  Stage 3 – Inventory Agent      : get_inventory_details (per candidate)
  Stage 4 – Policy Agent         : evaluate_policy (per candidate)
  Stage 5 – Decision Agent       : run_decision_engine (policy-feasible candidates only)
  Stage 6 – Final Decision Agent : finalize_decision + authoritative inventory safety

If the lightweight weighted decision engine is disabled, fails, or proposes a
product outside the original feasible candidate pool, the workflow falls back
explicitly to the deterministic baseline ranker (and records fallback status and
reason) while still enforcing Stage 6 policy and inventory revalidation.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from pydantic import BaseModel

from backend.app.decision.baseline_ranker import rank_feasible_candidates
from backend.app.decision.weighted_engine import WeightedDecisionEngine
from backend.app.mcp.client import MCPClient, MCPToolError, MCPToolTrace
from backend.app.mcp.schemas import (
    CustomerContext,
    CustomerInput,
    DecisionCandidateInput,
    DecisionEngineInput,
    DecisionEngineOutput,
    FinalExclusion,
    FinalizeCandidate,
    FinalizeInput,
    FinalizeOutput,
    FinalRecommendation,
    InventoryDetails,
    InventoryInput,
    PolicyInput,
    PolicyOutput,
    RecommendationInput,
    RecommendationOutput,
)
from backend.app.recommendation.policy_engine import FRESH_DATA_STATUSES


logger = logging.getLogger("nbo.mcp.workflow")

# All six core tools must be present before the workflow starts.
_REQUIRED_TOOLS: frozenset[str] = frozenset(
    {
        "get_customer_context",
        "generate_recommendations",
        "get_inventory_details",
        "evaluate_policy",
        "run_laya_decision",
        "finalize_decision",
    }
)


class AgentExecution(BaseModel):
    agent: str
    responsibility: str
    status: str
    duration_ms: float
    output: dict[str, Any] | None = None
    error: str | None = None


class MCPWorkflowResult(BaseModel):
    status: str
    customer_id: str
    agents: list[AgentExecution]
    tool_calls: list[MCPToolTrace]
    recommendations: list[FinalRecommendation]
    excluded_candidates: list[FinalExclusion]
    decision_id: str | None = None
    selected_product_id: str | None = None
    laya_selected_product_id: str | None = None
    laya_status: str | None = None
    decision_method: str | None = None
    decision_engine_status: str | None = None
    decision_weights: dict[str, float] | None = None
    objective_scores: dict[str, dict[str, Any]] = {}
    final_ranking: list[dict[str, Any]] = []
    final_validation: dict[str, Any] | None = None
    decision_explanation: str | None = None
    fallback_used: bool = False
    fallback_reason: str | None = None
    error: str | None = None


class SharedWorkflowState:
    def __init__(
        self,
        customer_id: str,
        top_k: int,
        reward_context: bool,
        promotion_context: bool,
        express_context: bool,
    ) -> None:
        self.customer_id = customer_id
        self.top_k = top_k
        self.reward_context = reward_context
        self.promotion_context = promotion_context
        self.express_context = express_context
        self.customer_context: CustomerContext | None = None
        self.recommendations: RecommendationOutput | None = None
        self.inventory: dict[str, InventoryDetails] = {}
        self.policy: dict[str, PolicyOutput] = {}
        self.decision_output: DecisionEngineOutput | None = None
        self.selected_product_id: str | None = None
        self.laya_selected_product_id: str | None = None
        self.laya_status: str | None = None
        self.decision_method: str = "NONE"
        self.decision_engine_status: str | None = None
        self.decision_weights: dict[str, float] | None = None
        self.objective_scores: dict[str, dict[str, Any]] = {}
        self.final_ranking: list[dict[str, Any]] = []
        self.final_validation: dict[str, Any] | None = None
        self.decision_explanation: str | None = None
        self.fallback_used: bool = False
        self.fallback_reason: str | None = None
        self.final: FinalizeOutput | None = None
        self.agents: list[AgentExecution] = []
        self.error: str | None = None


def _record_agent(
    state: SharedWorkflowState,
    agent: str,
    responsibility: str,
    started: float,
    status: str,
    output: BaseModel | dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    if isinstance(output, BaseModel):
        output_data = output.model_dump(mode="json")
    else:
        output_data = output
    state.agents.append(
        AgentExecution(
            agent=agent,
            responsibility=responsibility,
            status=status,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            output=output_data,
            error=error,
        )
    )


def _policy_excluded_candidates(state: SharedWorkflowState) -> list[FinalExclusion]:
    if state.recommendations is None:
        return []
    exclusions: list[FinalExclusion] = []
    for candidate in state.recommendations.candidates:
        policy = state.policy.get(candidate.product_id)
        if policy is not None and policy.decision != "PASS":
            exclusions.append(
                FinalExclusion(
                    product_id=candidate.product_id,
                    product_name=candidate.product_name,
                    recommendation_score=candidate.recommendation_score,
                    policy_decision="EXCLUDE",
                    policy_reasons=policy.reasons,
                )
            )
    return exclusions


async def _run_workflow(
    customer_id: str,
    top_k: int,
    reward_context: bool,
    promotion_context: bool,
    express_context: bool,
) -> MCPWorkflowResult:
    state = SharedWorkflowState(
        customer_id,
        top_k,
        reward_context,
        promotion_context,
        express_context,
    )
    try:
        async with MCPClient() as client:
            if not _REQUIRED_TOOLS.issubset(client.server_tools):
                missing = _REQUIRED_TOOLS - set(client.server_tools)
                raise MCPToolError(
                    f"MCP server did not expose the required tools. Missing: {sorted(missing)}"
                )

            # ------------------------------------------------------------------
            # Stage 1 – Customer Agent
            # ------------------------------------------------------------------
            started = time.perf_counter()
            try:
                state.customer_context = await client.call_tool(
                    "get_customer_context",
                    CustomerInput(customer_id=customer_id),
                    CustomerContext,
                )
                _record_agent(
                    state,
                    "Customer Agent",
                    "Retrieve customer profile and interaction history.",
                    started,
                    "completed",
                    state.customer_context,
                )
            except MCPToolError as error:
                state.error = str(error)
                _record_agent(
                    state,
                    "Customer Agent",
                    "Retrieve customer profile and interaction history.",
                    started,
                    "failed_safe",
                    error=state.error,
                )
                return _result(state, client.traces)

            # ------------------------------------------------------------------
            # Stage 2 – Recommendation Agent
            # ------------------------------------------------------------------
            started = time.perf_counter()
            try:
                state.recommendations = await client.call_tool(
                    "generate_recommendations",
                    RecommendationInput(customer_id=customer_id, limit=max(top_k, 20)),
                    RecommendationOutput,
                )
                _record_agent(
                    state,
                    "Recommendation Agent",
                    "Generate and score candidates using the Gradient Boosting pipeline.",
                    started,
                    "completed",
                    state.recommendations,
                )
            except MCPToolError as error:
                state.error = str(error)
                _record_agent(
                    state,
                    "Recommendation Agent",
                    "Generate and score candidates using the Gradient Boosting pipeline.",
                    started,
                    "failed_safe",
                    error=state.error,
                )
                return _result(state, client.traces)

            # ------------------------------------------------------------------
            # Stage 3 – Inventory Agent
            # ------------------------------------------------------------------
            started = time.perf_counter()
            inventory_errors = 0
            for candidate in state.recommendations.candidates:
                try:
                    state.inventory[candidate.product_id] = await client.call_tool(
                        "get_inventory_details",
                        InventoryInput(product_id=candidate.product_id),
                        InventoryDetails,
                    )
                except MCPToolError as error:
                    inventory_errors += 1
                    state.inventory[candidate.product_id] = InventoryDetails(
                        product_id=candidate.product_id,
                        product_status="unknown",
                        available_stock=None,
                        inventory_status=None,
                        gross_margin_pct=None,
                        shipping_days=None,
                        reward_eligible=None,
                        promotion_eligible=None,
                        reorder_point=None,
                        max_discount_pct=None,
                        data_freshness_status=None,
                        verification_status="failed",
                        error=str(error),
                    )
            _record_agent(
                state,
                "Inventory Agent",
                "Verify operational stock, margin, fulfilment, freshness, and eligibility data.",
                started,
                "completed" if inventory_errors == 0 else "completed_with_errors",
                {
                    "verified": sum(
                        item.verification_status == "verified"
                        for item in state.inventory.values()
                    ),
                    "failed": inventory_errors,
                    "products": [i.model_dump(mode="json") for i in state.inventory.values()],
                },
            )

            # ------------------------------------------------------------------
            # Stage 4 – Policy Agent
            # ------------------------------------------------------------------
            started = time.perf_counter()
            policy_errors = 0
            for candidate in state.recommendations.candidates:
                try:
                    state.policy[candidate.product_id] = await client.call_tool(
                        "evaluate_policy",
                        PolicyInput(
                            product_id=candidate.product_id,
                            reward_context=reward_context,
                            promotion_context=promotion_context,
                            express_context=express_context,
                        ),
                        PolicyOutput,
                    )
                except MCPToolError as error:
                    policy_errors += 1
                    state.policy[candidate.product_id] = PolicyOutput(
                        product_id=candidate.product_id,
                        decision="EXCLUDE",
                        reasons=[f"Policy verification failed: {error}"],
                        flags=[],
                    )
            _record_agent(
                state,
                "Policy Agent",
                "Apply the authoritative deterministic supply and eligibility policy.",
                started,
                "completed" if policy_errors == 0 else "completed_with_errors",
                {
                    "pass": sum(
                        item.decision == "PASS" for item in state.policy.values()
                    ),
                    "excluded": sum(
                        item.decision == "EXCLUDE" for item in state.policy.values()
                    ),
                    "failed": policy_errors,
                    "results": [p.model_dump(mode="json") for p in state.policy.values()],
                },
            )

            # ------------------------------------------------------------------
            # Stage 5 – Decision Agent (Lightweight Weighted Decision Engine)
            # Receives ONLY candidates marked PASS by Policy Agent.
            # ------------------------------------------------------------------
            started = time.perf_counter()
            feasible_inputs: list[DecisionCandidateInput] = []
            for cand in state.recommendations.candidates:
                policy = state.policy.get(cand.product_id)
                if policy is not None and policy.decision == "PASS":
                    inv = state.inventory.get(cand.product_id)
                    feasible_inputs.append(
                        DecisionCandidateInput(
                            product_id=cand.product_id,
                            product_name=cand.product_name,
                            recommendation_score=cand.recommendation_score,
                            category=cand.category,
                            subcategory=cand.subcategory,
                            brand=cand.brand,
                            gross_margin_pct=inv.gross_margin_pct if inv else None,
                            available_stock=inv.available_stock if inv else None,
                            inventory_status=inv.inventory_status if inv else None,
                            shipping_days=inv.shipping_days if inv else None,
                            reorder_point=inv.reorder_point if inv else None,
                        )
                    )

            if not feasible_inputs:
                state.decision_engine_status = "SKIPPED_NO_FEASIBLE"
                state.decision_method = "NONE"
                state.final = FinalizeOutput(
                    status="ALL_CANDIDATES_EXCLUDED",
                    recommendations=[],
                    excluded_candidates=_policy_excluded_candidates(state),
                )
                _record_agent(
                    state,
                    "Decision Agent",
                    "Compare policy-feasible candidates using configured multi-objective weights.",
                    started,
                    "skipped_no_feasible",
                    error="No policy-feasible candidates remain.",
                )
                return _result(state, client.traces)

            feasible_ids = {item.product_id for item in feasible_inputs}
            finalize_candidates: list[FinalizeCandidate] = []

            try:
                decision_output = await client.call_tool(
                    "run_laya_decision",
                    DecisionEngineInput(
                        candidates=feasible_inputs,
                        express_context=express_context,
                    ),
                    DecisionEngineOutput,
                )
                state.decision_output = decision_output
                selected_id = decision_output.selected_product_id

                if selected_id not in feasible_ids:
                    raise MCPToolError(
                        f"Laya selected '{selected_id}' which is not in the policy-feasible candidate set."
                    )

                state.decision_weights = decision_output.weights or None
                state.objective_scores = decision_output.objective_scores
                state.decision_explanation = decision_output.explanation
                state.selected_product_id = selected_id

                if decision_output.status == "FALLBACK":
                    state.fallback_used = True
                    state.fallback_reason = (
                        decision_output.fallback_reason
                        or decision_output.explanation
                    )
                    state.laya_status = "FALLBACK"
                    state.laya_selected_product_id = None
                    state.decision_method = "WEIGHTED_DECISION_FALLBACK"
                    state.decision_engine_status = "FALLBACK"
                else:
                    state.laya_status = "SUCCESS"
                    state.laya_selected_product_id = selected_id
                    state.decision_method = "LAYA"
                    state.decision_engine_status = "LAYA_PRIMARY"

                for item in decision_output.ranked_candidates:
                    pid = str(item["product_id"])
                    if pid in feasible_ids:
                        finalize_candidates.append(
                            FinalizeCandidate(
                                product_id=pid,
                                product_name=str(item["product_name"]),
                                recommendation_score=float(item["recommendation_score"]),
                                objective_scores=item.get("objective_scores"),
                                weighted_score=item.get("weighted_score"),
                                rank=item.get("rank"),
                            )
                        )

                if not finalize_candidates:
                    chosen_in = next(i for i in feasible_inputs if i.product_id == selected_id)
                    finalize_candidates.append(
                        FinalizeCandidate(
                            product_id=chosen_in.product_id,
                            product_name=chosen_in.product_name,
                            recommendation_score=chosen_in.recommendation_score,
                        )
                    )

                _record_agent(
                    state,
                    "Decision Agent",
                    "Run Laya inference over capped policy-feasible candidates (with weighted fallback).",
                    started,
                    "completed" if not state.fallback_used else "completed_with_fallback",
                    decision_output,
                    error=state.fallback_reason,
                )

            except MCPToolError as error:
                state.fallback_used = True
                state.fallback_reason = str(error)
                state.laya_status = "FALLBACK"
                state.laya_selected_product_id = None
                raw_pool = [item.model_dump() for item in feasible_inputs]
                weighted_fb = WeightedDecisionEngine()
                if weighted_fb.enabled:
                    state.decision_method = "WEIGHTED_DECISION_FALLBACK"
                    state.decision_engine_status = "FALLBACK"
                    fb_res = weighted_fb.choose(raw_pool, express_context=express_context)
                    state.decision_weights = fb_res["weights"]
                    state.objective_scores = fb_res["objective_scores"]
                    fallback_ranked = fb_res["ranked_candidates"]
                else:
                    state.decision_method = "DETERMINISTIC_FALLBACK"
                    state.decision_engine_status = "FALLBACK"
                    fallback_ranked = rank_feasible_candidates(raw_pool, top_k=len(raw_pool))

                state.selected_product_id = str(fallback_ranked[0]["product_id"])
                state.decision_explanation = (
                    f"{state.decision_method} selected {state.selected_product_id} "
                    f"after Laya tool error: {state.fallback_reason}"
                )
                finalize_candidates = [
                    FinalizeCandidate(
                        product_id=str(item["product_id"]),
                        product_name=str(item["product_name"]),
                        recommendation_score=float(item["recommendation_score"]),
                        objective_scores=item.get("objective_scores"),
                        weighted_score=item.get("weighted_score"),
                        rank=item.get("rank", idx + 1),
                    )
                    for idx, item in enumerate(fallback_ranked)
                ]
                _record_agent(
                    state,
                    "Decision Agent",
                    "Run Laya inference over capped policy-feasible candidates (with weighted fallback).",
                    started,
                    "completed_with_fallback",
                    {
                        "status": "FALLBACK",
                        "selected_product_id": state.selected_product_id,
                        "fallback_reason": state.fallback_reason,
                    },
                    error=state.fallback_reason,
                )

            # ------------------------------------------------------------------
            # Stage 6 – Final Decision Agent
            # Revalidates ranked candidates against authoritative policy & inventory.
            # ------------------------------------------------------------------
            started = time.perf_counter()
            try:
                state.final = await client.call_tool(
                    "finalize_decision",
                    FinalizeInput(
                        candidates=finalize_candidates,
                        reward_context=reward_context,
                        promotion_context=promotion_context,
                        express_context=express_context,
                    ),
                    FinalizeOutput,
                )
                state.final = _apply_inventory_safety(state)
                # Ensure all policy-excluded items from Stage 4 are included in excluded_candidates
                already_excluded = {e.product_id for e in state.final.excluded_candidates}
                merged_exclusions = list(state.final.excluded_candidates)
                for exc in _policy_excluded_candidates(state):
                    if exc.product_id not in already_excluded:
                        merged_exclusions.append(exc)
                state.final = FinalizeOutput(
                    status=state.final.status,
                    recommendations=state.final.recommendations,
                    excluded_candidates=merged_exclusions,
                )

                if state.final.recommendations:
                    winner = state.final.recommendations[0]
                    if winner.product_id != state.selected_product_id:
                        state.fallback_used = True
                        state.fallback_reason = (
                            state.fallback_reason
                            or f"Top candidate '{state.selected_product_id}' failed post-selection revalidation; promoted '{winner.product_id}'."
                        )
                        state.selected_product_id = winner.product_id
                    state.final_validation = {
                        "decision": "PASS",
                        "selected_product_id": winner.product_id,
                        "verified_count": len(state.final.recommendations),
                    }
                    state.final_ranking = [
                        {
                            "rank": rec.rank if rec.rank is not None else idx + 1,
                            "product_id": rec.product_id,
                            "product_name": rec.product_name,
                            "weighted_score": rec.weighted_score,
                            "recommendation_score": rec.recommendation_score,
                            "objective_scores": rec.objective_scores or {},
                        }
                        for idx, rec in enumerate(state.final.recommendations)
                    ]
                    _record_agent(
                        state,
                        "Final Decision Agent",
                        "Revalidate selected candidates against policy and verified inventory.",
                        started,
                        "completed",
                        state.final,
                    )
                else:
                    state.selected_product_id = None
                    state.final_validation = {
                        "decision": "EXCLUDE",
                        "selected_product_id": None,
                        "verified_count": 0,
                    }
                    _record_agent(
                        state,
                        "Final Decision Agent",
                        "Revalidate selected candidates against policy and verified inventory.",
                        started,
                        "completed_none_feasible",
                        state.final,
                        error="No candidate passed final policy revalidation and inventory safety checks.",
                    )
            except MCPToolError as error:
                state.error = str(error)
                _record_agent(
                    state,
                    "Final Decision Agent",
                    "Revalidate selected candidates against policy and verified inventory.",
                    started,
                    "failed_safe",
                    error=state.error,
                )
            return _result(state, client.traces)

    except Exception as error:
        logger.exception("MCP workflow failed before completion")
        state.error = str(error)
        return _result(state, [])


def _apply_inventory_safety(state: SharedWorkflowState) -> FinalizeOutput:
    """Prevent failed, unknown, zero-stock, or stale inventory checks from becoming actionable."""
    if state.final is None:
        return FinalizeOutput(
            status="ALL_CANDIDATES_EXCLUDED", recommendations=[], excluded_candidates=[]
        )
    safe_recommendations: list[FinalRecommendation] = []
    additional_exclusions: list[FinalExclusion] = []
    for recommendation in state.final.recommendations:
        inventory = state.inventory.get(recommendation.product_id)
        policy = state.policy.get(recommendation.product_id)
        freshness_ok = (
            inventory is not None
            and inventory.data_freshness_status is not None
            and str(inventory.data_freshness_status).strip().lower() in FRESH_DATA_STATUSES
        )
        if (
            inventory is not None
            and inventory.verification_status == "verified"
            and inventory.available_stock is not None
            and inventory.available_stock > 0
            and str(inventory.inventory_status or "").strip().lower() != "unknown"
            and freshness_ok
            and policy is not None
            and policy.decision == "PASS"
        ):
            safe_recommendations.append(recommendation)
        else:
            if policy is None or policy.decision != "PASS":
                reason = (
                    policy.reasons
                    if policy and policy.reasons
                    else ["Policy was not verified as PASS."]
                )
            elif inventory is not None and not freshness_ok:
                reason = [
                    f"Operational inventory data is stale or unverified ({inventory.data_freshness_status})."
                ]
            else:
                reason = [
                    inventory.error
                    if inventory and inventory.error
                    else "Inventory was not verified as available."
                ]
            additional_exclusions.append(
                FinalExclusion(
                    product_id=recommendation.product_id,
                    product_name=recommendation.product_name,
                    recommendation_score=recommendation.recommendation_score,
                    policy_decision="EXCLUDE",
                    policy_reasons=reason,
                )
            )
    safe_recommendations = safe_recommendations[: state.top_k]
    exclusions = list(state.final.excluded_candidates)
    exclusions.extend(additional_exclusions)
    return FinalizeOutput(
        status="SUCCESS" if safe_recommendations else "ALL_CANDIDATES_EXCLUDED",
        recommendations=safe_recommendations,
        excluded_candidates=exclusions,
    )


def _result(
    state: SharedWorkflowState, traces: list[MCPToolTrace]
) -> MCPWorkflowResult:
    final = state.final or FinalizeOutput(
        status="ALL_CANDIDATES_EXCLUDED",
        recommendations=[],
        excluded_candidates=[],
    )
    status = final.status if state.error is None else "FAILED_SAFE"
    return MCPWorkflowResult(
        status=status,
        customer_id=state.customer_id,
        agents=state.agents,
        tool_calls=traces,
        recommendations=final.recommendations,
        excluded_candidates=final.excluded_candidates,
        selected_product_id=state.selected_product_id,
        laya_selected_product_id=state.laya_selected_product_id,
        laya_status=state.laya_status,
        decision_method=state.decision_method,
        decision_engine_status=state.decision_engine_status,
        decision_weights=state.decision_weights,
        objective_scores=state.objective_scores,
        final_ranking=state.final_ranking,
        final_validation=state.final_validation,
        decision_explanation=state.decision_explanation,
        fallback_used=state.fallback_used,
        fallback_reason=state.fallback_reason,
        error=state.error,
    )


def run_mcp_workflow(
    customer_id: str,
    top_k: int = 5,
    reward_context: bool = False,
    promotion_context: bool = False,
    express_context: bool = False,
) -> MCPWorkflowResult:
    """Run the real local MCP client-server workflow."""
    return asyncio.run(
        _run_workflow(
            customer_id=customer_id,
            top_k=top_k,
            reward_context=reward_context,
            promotion_context=promotion_context,
            express_context=express_context,
        )
    )
