"""
LEGACY COMPATIBILITY SHIM
This module re-exports schemas from their new canonical location at:
  backend.app.api.schemas.recommendation

Existing imports to backend.app.schemas.recommendation continue to work unchanged.
"""

from backend.app.api.schemas.recommendation import (
    ScoreExplanationSchema,
    RecommendedProductSchema,
    ExcludedCandidateSchema,
    RecommendationRequest,
    RecommendationResponse,
)
from backend.app.api.schemas.common import (
    ErrorResponse,
    HealthResponse,
)

__all__ = [
    "ScoreExplanationSchema",
    "RecommendedProductSchema",
    "ExcludedCandidateSchema",
    "RecommendationRequest",
    "RecommendationResponse",
    "ErrorResponse",
    "HealthResponse",
]
