"""Sequential deterministic agents that communicate only through MCP tools."""

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


logger = logging.getLogger("nbo.mcp.workflow")


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
            if not {
                "get_customer_context",
                "generate_recommendations",
                "get_inventory_details",
                "evaluate_policy",
                "finalize_decision",
            }.issubset(client.server_tools):
                raise MCPToolError("MCP server did not expose the required five tools.")

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
                    "verified": sum(item.verification_status == "verified" for item in state.inventory.values()),
                    "failed": inventory_errors,
                    "products": list(state.inventory.values()),
                },
            )

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
                    "pass": sum(item.decision == "PASS" for item in state.policy.values()),
                    "excluded": sum(item.decision == "EXCLUDE" for item in state.policy.values()),
                    "failed": policy_errors,
                    "results": list(state.policy.values()),
                },
            )

            started = time.perf_counter()
            try:
                state.final = await client.call_tool(
                    "finalize_decision",
                    FinalizeInput(
                        candidates=[
                            {
                                "product_id": candidate.product_id,
                                "product_name": candidate.product_name,
                                "recommendation_score": candidate.recommendation_score,
                            }
                            for candidate in state.recommendations.candidates
                        ],
                        reward_context=reward_context,
                        promotion_context=promotion_context,
                        express_context=express_context,
                    ),
                    FinalizeOutput,
                )
                state.final = _apply_inventory_safety(state)
                _record_agent(
                    state,
                    "Decision Agent",
                    "Revalidate every candidate and return only feasible recommendations.",
                    started,
                    "completed",
                    state.final,
                )
            except MCPToolError as error:
                state.error = str(error)
                _record_agent(
                    state,
                    "Decision Agent",
                    "Revalidate every candidate and return only feasible recommendations.",
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
        return FinalizeOutput(status="ALL_CANDIDATES_EXCLUDED", recommendations=[], excluded_candidates=[])
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


def _result(state: SharedWorkflowState, traces: list[MCPToolTrace]) -> MCPWorkflowResult:
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
