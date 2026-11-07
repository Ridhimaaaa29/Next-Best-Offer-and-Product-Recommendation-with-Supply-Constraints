"""
Health Router
Project: Next-Best-Offer and Product Recommendation with Supply Constraints
"""

from fastapi import APIRouter, status
from sqlalchemy import text

from backend.app.config import settings
from backend.app.db.session import engine
from backend.app.schemas.recommendation import HealthResponse
from backend.app.logging_config import get_logger

logger = get_logger("api.health")
router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Service Health Check",
    description="Check database connectivity and ML model availability status.",
)
def get_health() -> HealthResponse:
    # Check DB connectivity
    db_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            db_ok = True
    except Exception as e:
        logger.error("Health check database probe failed", error=str(e))
        db_ok = False

    # Check ML model availability
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

    service_status = "healthy" if db_ok else "degraded"

    return HealthResponse(
        status=service_status,
        app_version=settings.app_version,
        database_connected=db_ok,
        ml_model_loaded=ml_loaded,
        ml_model_name=ml_name,
    )
