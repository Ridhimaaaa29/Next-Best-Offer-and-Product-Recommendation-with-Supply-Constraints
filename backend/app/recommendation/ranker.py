"""
Recommendation Ranker Module.
Exposes the recommendation model scoring and ranking interfaces.
"""

from backend.app.recommendation.recommendation_model import (
    RecommendationModel,
    ScoredCandidate,
    ScoreExplanation,
    score_customer_candidates,
)

__all__ = [
    "RecommendationModel",
    "ScoredCandidate",
    "ScoreExplanation",
    "score_customer_candidates",
]
