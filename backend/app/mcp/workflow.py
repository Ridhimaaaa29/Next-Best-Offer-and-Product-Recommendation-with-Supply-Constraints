"""Sequential deterministic agents that communicate only through MCP tools.

Architecture (mandatory):
  Stage 1 – Customer Agent      : get_customer_context
  Stage 2 – Recommendation Agent: generate_recommendations
  Stage 3 – Inventory Agent     : get_inventory_details (per candidate)
  Stage 4 – Policy Agent        : evaluate_policy (per candidate)
  Stage 4.5 – Laya Agent        : run_laya_decision (feasible candidates only)
  Stage 5 – Decision Agent      : finalize_decision (Laya-selected candidate only)

Laya execution is mandatory.  The workflow NEVER returns SUCCESS via a
score-based sort.  If Laya is unavailable (FALLBACK status), fails, or
returns a product not in the feasible set the workflow returns FAILED_SAFE.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from pydantic import BaseModel

from backend.app.mcp.client import MCPClient, MCPToolError, MCPToolTrace
from backend.app.mcp.schemas import (
    CustomerContext,
    CustomerInput,
    FinalExclusion,
    FinalizeCandidate,
    FinalizeInput,
    FinalizeOutput,
    FinalRecommendation,
    InventoryDetails,
    InventoryInput,
    LayaInput,
    LayaOutput,
    PolicyInput,
    PolicyOutput,
    RecommendationInput,
    RecommendationOutput,
)


logger = logging.getLogger("nbo.mcp.workflow")

# All six tools must be present before the workflow starts.
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
    # Laya provenance fields – None when Laya stage was not reached.
    laya_selected_product_id: str | None = None
    laya_status: str | None = None
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
        # Laya outputs – set during Stage 4.5
        self.laya_output: LayaOutput | None = None
        self.laya_selected_id: str | None = None
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
                    "Generate and score candidates using the existing recommendation pipeline.",
                    started,
                    "completed",
                    state.recommendations,
                )
            except MCPToolError as error:
                state.error = str(error)
                _record_agent(
                    state,
                    "Recommendation Agent",
                    "Generate and score candidates using the existing recommendation pipeline.",
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
                        verification_status="failed",
                        error=str(error),
                    )
            _record_agent(
                state,
                "Inventory Agent",
                "Verify operational stock, margin, fulfilment, and eligibility data.",
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
            # Stage 4.5 – Laya Agent
            # Laya receives ONLY the candidates that passed policy evaluation.
            # A FALLBACK response (Laya disabled) is treated as a hard failure;
            # the workflow must NOT succeed via score-based sorting.
            # ------------------------------------------------------------------
            started = time.perf_counter()
            feasible_for_laya: list[FinalizeCandidate] = [
                FinalizeCandidate(
                    product_id=c.product_id,
                    product_name=c.product_name,
                    recommendation_score=c.recommendation_score,
                )
                for c in state.recommendations.candidates
                if (
                    state.policy.get(c.product_id) is not None
                    and state.policy[c.product_id].decision == "PASS"
                )
            ]

            if not feasible_for_laya:
                state.error = (
                    "No policy-feasible candidates remain; "
                    "Laya cannot select a Next-Best-Offer."
                )
                _record_agent(
                    state,
                    "Laya Agent",
                    "Select the Next-Best-Offer from policy-feasible candidates.",
                    started,
                    "skipped_no_feasible",
                    error=state.error,
                )
                return _result(state, client.traces)

            try:
                laya_output = await client.call_tool(
                    "run_laya_decision",
                    LayaInput(candidates=feasible_for_laya),
                    LayaOutput,
                )

                if laya_output.status == "FALLBACK":
                    # Laya is disabled or unavailable – score-based fallback is
                    # explicitly forbidden; surface this as a workflow failure.
                    state.error = (
                        f"Laya is unavailable and score-based fallback is not "
                        f"permitted: {laya_output.explanation}"
                    )
                    _record_agent(
                        state,
                        "Laya Agent",
                        "Select the Next-Best-Offer from policy-feasible candidates.",
                        started,
                        "failed_laya_unavailable",
                        laya_output,
                        state.error,
                    )
                    return _result(state, client.traces)

                # Validate that the selected product is in the feasible set.
                selected_id = laya_output.selected_product_id
                if not any(c.product_id == selected_id for c in feasible_for_laya):
                    state.error = (
                        f"Laya selected '{selected_id}' which is not in the "
                        "policy-feasible candidate set."
                    )
                    _record_agent(
                        state,
                        "Laya Agent",
                        "Select the Next-Best-Offer from policy-feasible candidates.",
                        started,
                        "failed_invalid_selection",
                        laya_output,
                        state.error,
                    )
                    return _result(state, client.traces)

                state.laya_output = laya_output
                state.laya_selected_id = selected_id
                _record_agent(
                    state,
                    "Laya Agent",
                    "Select the Next-Best-Offer from policy-feasible candidates.",
                    started,
                    "completed",
                    laya_output,
                )

            except MCPToolError as error:
                state.error = str(error)
                _record_agent(
                    state,
                    "Laya Agent",
                    "Select the Next-Best-Offer from policy-feasible candidates.",
                    started,
                    "failed_safe",
                    error=state.error,
                )
                return _result(state, client.traces)

            # ------------------------------------------------------------------
            # Stage 5 – Decision Agent
            # Pass ONLY the Laya-selected candidate to finalize_decision so that
            # the internal score-sort cannot displace Laya's choice.
            # finalize_decision will revalidate the candidate against the policy
            # engine for a final authoritative check.
            # ------------------------------------------------------------------
            started = time.perf_counter()
            laya_selected_candidate = next(
                c for c in feasible_for_laya
                if c.product_id == state.laya_selected_id
            )
            try:
                state.final = await client.call_tool(
                    "finalize_decision",
                    FinalizeInput(
                        candidates=[laya_selected_candidate],
                        reward_context=reward_context,
                        promotion_context=promotion_context,
                        express_context=express_context,
                    ),
                    FinalizeOutput,
                )
                state.final = _apply_inventory_safety(state)

                # If the Laya-selected candidate failed revalidation or the
                # inventory check, the workflow cannot claim SUCCESS.
                if not state.final.recommendations:
                    state.error = (
                        f"Laya-selected product '{state.laya_selected_id}' "
                        "failed post-selection policy revalidation or inventory check."
                    )
                    _record_agent(
                        state,
                        "Decision Agent",
                        "Revalidate Laya-selected candidate against policy and inventory.",
                        started,
                        "laya_selection_infeasible",
                        state.final,
                        state.error,
                    )
                else:
                    _record_agent(
                        state,
                        "Decision Agent",
                        "Revalidate Laya-selected candidate against policy and inventory.",
                        started,
                        "completed",
                        state.final,
                    )
            except MCPToolError as error:
                state.error = str(error)
                _record_agent(
                    state,
                    "Decision Agent",
                    "Revalidate Laya-selected candidate against policy and inventory.",
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
    """Prevent failed or unknown inventory checks from becoming feasible."""
    if state.final is None:
        return FinalizeOutput(
            status="ALL_CANDIDATES_EXCLUDED", recommendations=[], excluded_candidates=[]
        )
    safe_recommendations: list[FinalRecommendation] = []
    additional_exclusions: list[FinalExclusion] = []
    for recommendation in state.final.recommendations:
        inventory = state.inventory.get(recommendation.product_id)
        policy = state.policy.get(recommendation.product_id)
        if (
            inventory is not None
            and inventory.verification_status == "verified"
            and inventory.available_stock is not None
            and inventory.available_stock > 0
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
        laya_selected_product_id=state.laya_selected_id,
        laya_status=(
            state.laya_output.status if state.laya_output is not None else None
        ),
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
