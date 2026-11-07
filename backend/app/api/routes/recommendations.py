"""
Recommendation Router
Project: Next-Best-Offer and Product Recommendation with Supply Constraints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.api.schemas.recommendation import (
    RecommendationRequest,
    RecommendationResponse,
)
from backend.app.api.schemas.common import ErrorResponse
from backend.app.recommendation.decision_module import DecisionModule
from backend.app.db.session import get_db
from backend.app.logging_config import get_logger
from backend.app.services.audit_service import AuditService

logger = get_logger("api.recommend")
router = APIRouter(tags=["Recommendations"])

@router.post(
    "/recommend",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "Customer not found"},
        422: {"description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Generate Next-Best-Offer Recommendations",
    description=(
        "Executes the full supply-constrained recommendation pipeline: "
        "Customer Context -> Candidate Generation -> ML/Heuristic Scoring -> "
        "Policy Hard Constraints -> Feasibility Pruning -> Top-K Structured Output."
    ),
)
def generate_recommendations(
    req: RecommendationRequest,
    db: Session = Depends(get_db),
) -> RecommendationResponse:
    logger.info(
        "Received recommendation request",
        customer_id=req.customer_id,
        top_k=req.top_k,
        reward_context=req.reward_context,
        promotion_context=req.promotion_context,
        express_context=req.express_context,
    )

    try:
        decision_module = DecisionModule(session=db)
        raw_result = decision_module.decide(
            customer_id=req.customer_id,
            top_k=req.top_k,
            reward_context=req.reward_context,
            promotion_context=req.promotion_context,
            express_context=req.express_context,
        )
    except ValueError as ve:
        logger.warning("Customer context validation error", customer_id=req.customer_id, error=str(ve))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(ve),
        )
    except Exception as e:
        logger.error("Unhandled error during recommendation generation", customer_id=req.customer_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Recommendation pipeline failed: {str(e)}",
        )

    # Format result to match RecommendationResponse
    audit_id = AuditService(db).log_decision_audit(raw_result)
    excluded = raw_result.get("excluded_candidates") if req.include_excluded else None

    # Map candidate dicts to score breakdown schema
    formatted_recs = []
    for rec in raw_result.get("recommendations", []):
        formatted_recs.append(
            {
                "product_id": rec["product_id"],
                "product_name": rec["product_name"],
                "category": rec["category"],
                "subcategory": rec["subcategory"],
                "brand": rec["brand"],
                "unit_price": rec["unit_price"],
                "product_rating": rec["product_rating"],
                "product_popularity": rec["product_popularity"],
                "product_status": rec["product_status"],
                "recommendation_score": rec["recommendation_score"],
                "policy_decision": rec["policy_decision"],
                "policy_reasons": rec.get("policy_reasons", []),
                "score_breakdown": rec.get("score_explanation") or rec.get("explanation"),
            }
        )

    return RecommendationResponse(
        status=raw_result["status"],
        customer_id=raw_result["customer_id"],
        candidate_count=raw_result["candidate_count"],
        feasible_count=raw_result["feasible_count"],
        excluded_count=raw_result["excluded_count"],
        recommendations=formatted_recs,
        excluded_candidates=excluded,
    )
