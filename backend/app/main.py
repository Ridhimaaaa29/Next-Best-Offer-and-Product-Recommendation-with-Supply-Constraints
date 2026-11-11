"""
FastAPI Main Application Entry Point
Project: Next-Best-Offer and Product Recommendation with Supply Constraints
"""

import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from backend.app.config import settings
from backend.app.decision.laya_adapter import LayaAdapter
from backend.app.observability.logging import configure_logging, get_logger
from backend.app.middleware.request_id import RequestIdMiddleware
from backend.app.middleware.error_handler import LoggingMiddleware, validation_exception_handler
from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.recommendations import router as recommendations_router
from backend.app.api.routes.products import router as products_router
from backend.app.api.routes.evaluation import router as evaluation_router
from backend.app.api.routes.decisions import router as decisions_router
from backend.app.api.routes.customers import router as customers_router
from backend.app.api.routes.catalogue import router as catalogue_router
from backend.app.api.routes.assistant import router as assistant_router
from backend.app.api.routes.audit import router as audit_router
from backend.app.api.routes.mcp import router as mcp_router

# Initialize structured logging
configure_logging(level=settings.log_level)
logger = get_logger("app.main")
logger.info(f"FastAPI starting with python_executable={sys.executable}")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    env_preload = os.getenv("LAYA_PRELOAD_ON_STARTUP")
    preload_enabled = (
        env_preload.strip().lower() in ("true", "1", "yes")
        if env_preload is not None
        else bool(getattr(settings, "laya_preload_on_startup", False))
    )
    if preload_enabled:
        adapter = LayaAdapter()
        if adapter.enabled:
            logger.info(
                "Preloading Laya decision model on startup",
                app_env=adapter.status_info().get("app_env"),
                model=adapter.status_info().get("model"),
                cache_dir=adapter.status_info().get("cache_dir"),
            )
            warmup_result = adapter.warmup()
            logger.info("Laya startup warmup completed", **warmup_result)
    yield


app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description=settings.app_description,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Register Middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(RequestIdMiddleware)

# Register Centralized Exception Handler
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Include API v1 Routes
app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(recommendations_router, prefix=settings.api_prefix)
app.include_router(products_router, prefix=settings.api_prefix)
app.include_router(evaluation_router, prefix=settings.api_prefix)
app.include_router(decisions_router, prefix=settings.api_prefix)
app.include_router(customers_router, prefix=settings.api_prefix)
app.include_router(catalogue_router, prefix=settings.api_prefix)
app.include_router(assistant_router, prefix=settings.api_prefix)
app.include_router(audit_router, prefix=settings.api_prefix)
app.include_router(mcp_router, prefix=settings.api_prefix)

# Also expose /health at root for container orchestration
app.include_router(health_router)
app.include_router(mcp_router)
app.include_router(assistant_router)
