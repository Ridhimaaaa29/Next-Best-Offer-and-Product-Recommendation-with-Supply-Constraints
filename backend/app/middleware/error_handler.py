
"""
Centralized Error Handling Middleware and Exception Handlers.
"""

import time

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.logging_config import get_logger


logger = get_logger("app.middleware.error_handler")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        req_id = getattr(request.state, "request_id", None)

        logger.info(
            "HTTP request started",
            request_id=req_id,
            method=request.method,
            path=request.url.path,
            client=request.client.host if request.client else None,
        )

        try:
            response = await call_next(request)

            duration_ms = round(
                (time.perf_counter() - start_time) * 1000, 2
            )

            logger.info(
                "HTTP request completed",
                request_id=req_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )

            return response

        except Exception as exc:
            duration_ms = round(
                (time.perf_counter() - start_time) * 1000, 2
            )

            logger.error(
                "HTTP request failed with unhandled exception",
                request_id=req_id,
                method=request.method,
                path=request.url.path,
                error=str(exc),
                duration_ms=duration_ms,
            )

            raise


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    req_id = getattr(request.state, "request_id", None)

    logger.warning(
        "Request validation failed",
        request_id=req_id,
        path=request.url.path,
        errors=exc.errors(),
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "error": "Validation Error",
            "detail": exc.errors(),
        },
    )
