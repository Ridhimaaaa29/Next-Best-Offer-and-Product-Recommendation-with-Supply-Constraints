"""
MCP Sequential Workflow Router.
Project: Next-Best-Offer and Product Recommendation with Supply Constraints
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.app.api.schemas.common import ErrorResponse
from backend.app.api.schemas.mcp import MCPWorkflowRequest
from backend.app.db.session import get_db
from backend.app.mcp.workflow import MCPWorkflowResult, _run_workflow
from backend.app.services.audit_service import AuditService

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
        502: {"model": MCPWorkflowResult, "description": "Upstream MCP tool failure"},
        503: {"model": ErrorResponse, "description": "Decision audit persistence failed"},
    },
    summary="Execute Sequential Multi-Agent MCP Recommendation Workflow",
    description=(
        "Executes the 6-stage multi-agent workflow via in-process MCP tools: "
        "Customer Agent -> Recommendation Agent -> Inventory Agent -> Policy Agent -> "
        "Decision Agent (Laya Model with Weighted Fallback) -> Final Decision Agent "
        "(Revalidation & Safety) with persisted PostgreSQL audit."
    ),
)
async def execute_mcp_workflow(
    request: MCPWorkflowRequest,
    response: Response,
    db: Session = Depends(get_db),
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

    is_customer_not_found = False
    if result.status == "FAILED_SAFE":
        customer_agent = next((a for a in result.agents if a.agent == "Customer Agent"), None)
        err_lower = (result.error or "").lower()
        if customer_agent and customer_agent.status == "failed_safe" and "not found" in err_lower:
            is_customer_not_found = True
            response.status_code = status.HTTP_404_NOT_FOUND
        else:
            response.status_code = status.HTTP_502_BAD_GATEWAY

    if not is_customer_not_found:
        rec_agent = next((a for a in result.agents if a.agent == "Recommendation Agent"), None)
        all_candidates = (
            (rec_agent.output or {}).get("candidates", [])
            if rec_agent and isinstance(rec_agent.output, dict)
            else []
        )
        audit_payload = {
            "customer_id": result.customer_id,
            "status": result.status,
            "all_evaluated_candidates": all_candidates,
            "recommendations": [item.model_dump() for item in result.recommendations],
            "excluded_candidates": [item.model_dump() for item in result.excluded_candidates],
            "selected_product_id": result.selected_product_id,
            "decision_method": result.decision_method or "NONE",
            "decision_weights": result.decision_weights,
            "objective_scores": result.objective_scores,
            "final_validation": result.final_validation,
            "decision_explanation": result.decision_explanation,
            "fallback_used": result.fallback_used,
            "fallback_reason": result.fallback_reason or result.error,
        }
        try:
            result.decision_id = AuditService(db).log_decision_audit(audit_payload)
        except Exception as audit_err:
            logger.exception("Failed to persist MCP workflow audit record")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"MCP workflow completed but decision audit persistence failed: {audit_err}",
            ) from audit_err

    return result
