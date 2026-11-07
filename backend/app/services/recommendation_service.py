"""
Recommendation Service Orchestrator.
Wraps candidate generation and scoring logic.
"""

from typing import List, Dict, Any, Optional
from backend.app.recommendation.recommendation_model import RecommendationModel, ScoredCandidate
from backend.app.recommendation.candidate_generator import generate_candidates


class RecommendationService:
    def __init__(self, recommender: Optional[RecommendationModel] = None):
        self.recommender = recommender or RecommendationModel()

    def get_ranked_candidates(self, customer_id: str, limit: int = 20) -> List[ScoredCandidate]:
        candidates = generate_candidates(customer_id=customer_id, limit=limit)
        return self.recommender.rank_candidates(customer_id=customer_id, candidates=candidates)
