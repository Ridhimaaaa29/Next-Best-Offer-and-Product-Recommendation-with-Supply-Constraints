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


@router.post(
    "/recommendations/similar-products",
    status_code=status.HTTP_200_OK,
    summary="Generate Semantic Vector Similar Product Recommendations",
)
def get_similar_products_endpoint(
    payload: dict,
    db: Session = Depends(get_db),
) -> dict:
    """
    Computes pairwise vector embeddings and cosine similarity to discover semantically related products.
    """
    product_id = payload.get("product_id")
    top_n = int(payload.get("top_n", 5))
    if not product_id:
        raise HTTPException(status_code=400, detail="Missing product_id in request payload.")

    import pandas as pd
    from pathlib import Path
    from backend.app.recommendation.content_based import get_content_recommender
    from backend.app.db.models import Product

    # Query products from DB or fallback to synthetic CSV
    products = db.query(Product).all()
    if products:
        p_data = [
            {
                "product_id": p.product_id,
                "product_name": p.product_name,
                "category": p.category,
                "subcategory": p.subcategory,
                "brand": p.brand,
                "unit_price": p.unit_price,
                "product_rating": p.product_rating,
                "product_popularity": p.product_popularity,
            }
            for p in products
        ]
        df = pd.DataFrame(p_data)
    else:
        csv_path = Path("data/synthetic/products.csv")
        df = pd.read_csv(csv_path) if csv_path.exists() else pd.DataFrame()

    recommender = get_content_recommender(df)
    similar_items = recommender.get_similar_products_detailed(product_id, top_n=top_n)

    return {
        "status": "SUCCESS",
        "product_id": product_id,
        "vector_model": "TF-IDF + Cosine Similarity Vector Space",
        "total_embeddings_indexed": len(df),
        "similar_products": similar_items,
    }
