from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.recommendations import router as recommendations_router
from backend.app.api.routes.products import router as products_router
from backend.app.api.routes.evaluation import router as evaluation_router
from backend.app.api.routes.decisions import router as decisions_router

__all__ = [
    "health_router",
    "recommendations_router",
    "products_router",
    "evaluation_router",
    "decisions_router",
]
