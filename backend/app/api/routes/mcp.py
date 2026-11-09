"""
MCP Sequential Workflow Router.
Project: Next-Best-Offer and Product Recommendation with Supply Constraints
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Response, status

from backend.app.api.schemas.common import ErrorResponse
from backend.app.api.schemas.mcp import MCPWorkflowRequest
from backend.app.mcp.workflow import MCPWorkflowResult, _run_workflow

logger = logging.getLogger("nbo.api.mcp")
router = APIRouter(tags=["MCP Workflow"])


def _sanitize_error_message(error: str | None) -> str | None:
    """Sanitize error messages to ensure no credentials, connection strings, or stack traces leak."""
    if not error:
        return None
    sensitive_markers = [
        "password",
        "secret",
        "bearer",
        "api_key",
        "postgresql://",
        "postgres://",
        "Traceback (most recent call last)",
    ]
    error_lower = error.lower()
    for marker in sensitive_markers:
        if marker in error_lower:
            return "An internal error occurred during workflow execution."
    return error


@router.post(
    "/mcp/workflow",
    response_model=MCPWorkflowResult,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"model": MCPWorkflowResult, "description": "Workflow completed successfully"},
        404: {"model": MCPWorkflowResult, "description": "Customer not found"},
        422: {"description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        502: {"model": MCPWorkflowResult, "description": "Laya decision layer failed or invalid selection, or upstream MCP tool failure"},
        503: {"model": MCPWorkflowResult, "description": "Laya decision layer unavailable or disabled"},
    },
    summary="Execute Sequential Multi-Agent MCP Recommendation Workflow",
    description=(
        "Executes the full deterministic multi-agent workflow communicating via MCP tools: "
        "Customer Agent -> Recommendation Agent -> Inventory Agent -> Policy Agent -> "
        "Mandatory Laya Decision -> Final Policy Revalidation & Inventory Safety."
    ),
)
async def execute_mcp_workflow(
    request: MCPWorkflowRequest,
    response: Response,
) -> MCPWorkflowResult:
    logger.info(
        "Received MCP workflow execution request",
        extra={
            "customer_id": request.customer_id,
            "top_k": request.top_k,
            "reward_context": request.reward_context,
            "promotion_context": request.promotion_context,
            "express_context": request.express_context,
        },
    )

    try:
        result = await _run_workflow(
            customer_id=request.customer_id,
            top_k=request.top_k,
            reward_context=request.reward_context,
            promotion_context=request.promotion_context,
            express_context=request.express_context,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected error executing MCP workflow")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during MCP workflow execution.",
        ) from exc

    # Sanitize top-level error string to prevent sensitive information leakage
    if result.error:
        result.error = _sanitize_error_message(result.error)

    # Sanitize individual agent error messages if present
    for agent_exec in result.agents:
        if agent_exec.error:
            agent_exec.error = _sanitize_error_message(agent_exec.error)

    # Map failures to appropriate HTTP status codes while preserving full structured audit contract
    if result.status == "FAILED_SAFE":
        laya_agent = next((a for a in result.agents if a.agent == "Laya Agent"), None)
        decision_agent = next((a for a in result.agents if a.agent == "Decision Agent"), None)
        customer_agent = next((a for a in result.agents if a.agent == "Customer Agent"), None)

        err_lower = (result.error or "").lower()

        if customer_agent and customer_agent.status == "failed_safe" and "not found" in err_lower:
            response.status_code = status.HTTP_404_NOT_FOUND
        elif laya_agent and laya_agent.status == "failed_laya_unavailable":
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif (
            (laya_agent and laya_agent.status in ("failed_invalid_selection", "failed_safe"))
            or (decision_agent and decision_agent.status in ("laya_selection_infeasible", "failed_safe"))
            or "laya" in err_lower
        ):
            response.status_code = status.HTTP_502_BAD_GATEWAY
        else:
            response.status_code = status.HTTP_502_BAD_GATEWAY

    return result
