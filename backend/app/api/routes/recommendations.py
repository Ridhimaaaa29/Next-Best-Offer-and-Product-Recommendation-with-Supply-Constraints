"""
Recommendation Router
Project: Next-Best-Offer and Product Recommendation with Supply Constraints
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
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
        503: {"model": ErrorResponse, "description": "Audit persistence failed or database unavailable"},
    },
    summary="Generate Next-Best-Offer Recommendations",
    description=(
        "Executes the full supply-constrained recommendation pipeline: "
        "Customer Context -> Candidate Generation -> ML/Heuristic Scoring -> "
        "Policy Hard Constraints -> Capped Laya Decision Inference -> "
        "Authoritative Policy Revalidation (with Weighted Fallback) -> Persisted Audit."
    ),
)
def generate_recommendations(
    req: RecommendationRequest,
    response: Response,
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
            use_laya=True,
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

    try:
        audit_id = AuditService(db).log_decision_audit(raw_result)
    except Exception as audit_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Recommendation generated but audit persistence failed: {audit_err}",
        ) from audit_err

    excluded = raw_result.get("excluded_candidates") if req.include_excluded else None

    # Map candidate dicts to response schema
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
                "objective_scores": rec.get("objective_scores"),
                "weighted_score": rec.get("weighted_score"),
                "rank": rec.get("rank"),
            }
        )

    return RecommendationResponse(
        status=raw_result["status"],
        customer_id=raw_result["customer_id"],
        decision_id=audit_id,
        candidate_count=raw_result["candidate_count"],
        feasible_count=raw_result["feasible_count"],
        excluded_count=raw_result["excluded_count"],
        decision_method=raw_result.get("decision_method", "LAYA"),
        laya_status=raw_result.get("laya_status"),
        decision_engine_status=raw_result.get("decision_engine_status"),
        decision_weights=raw_result.get("decision_weights"),
        objective_scores=raw_result.get("objective_scores", {}),
        final_ranking=raw_result.get("final_ranking", []),
        final_validation=raw_result.get("final_validation"),
        decision_explanation=raw_result.get("decision_explanation"),
        fallback_used=bool(raw_result.get("fallback_used", False)),
        fallback_reason=raw_result.get("fallback_reason"),
        recommendations=formatted_recs,
        excluded_candidates=excluded,
    )
