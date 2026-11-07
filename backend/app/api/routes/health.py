"""
Health Check Router
Project: Next-Best-Offer and Product Recommendation with Supply Constraints
"""

from fastapi import APIRouter, status

from backend.app.config import settings
from backend.app.api.schemas.common import HealthResponse
from backend.app.db.session import check_database_connection
from backend.app.logging_config import get_logger

logger = get_logger("api.health")
router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Service Health Check",
    description="Returns service availability, Neon database connectivity, and ML model status.",
)
def get_health() -> HealthResponse:
    # 1. Neon DB connectivity
    db_connected = check_database_connection()

    # 2. Check ML model artifact
    ml_loaded = False
    ml_name = None
    if settings.model_artifact_path.exists():
        ml_loaded = True
        try:
            import joblib
            artifact = joblib.load(settings.model_artifact_path)
            ml_name = artifact.get("model_name", "ML Model")
        except Exception:
            ml_name = "Artifact file present (unparsed)"

    overall_status = "healthy" if db_connected else "degraded"
    logger.info("Health check performed", status=overall_status, db_connected=db_connected, ml_loaded=ml_loaded)

    return HealthResponse(
        status=overall_status,
        app_version=settings.app_version,
        database_connected=db_connected,
        ml_model_loaded=ml_loaded,
        ml_model_name=ml_name,
    )
