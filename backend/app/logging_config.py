"""
Structured Application Logging
Project: Next-Best-Offer and Product Recommendation with Supply Constraints

Configures structured logging with key-value kwargs support.
Call configure_logging() once at application startup.

SECURITY: This module must never log DATABASE_URL, API keys, or Milvus tokens.
"""

import logging
import sys
from typing import Any, Optional


class _SafeFormatter(logging.Formatter):
    """
    Log formatter that produces compact, structured log lines.
    Format: [LEVEL] logger_name | message | key=value ...
    """

    def format(self, record: logging.LogRecord) -> str:
        base = f"[{record.levelname}] {record.name} | {record.getMessage()}"
        extras = {
            k: v
            for k, v in record.__dict__.items()
            if k not in logging.LogRecord.__dict__
            and k not in {
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "message", "pathname", "process", "processName",
                "relativeCreated", "stack_info", "thread", "threadName",
                "exc_info", "exc_text", "taskName",
            }
        }
        if extras:
            kv = " | ".join(f"{k}={v}" for k, v in extras.items())
            base = f"{base} | {kv}"
        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)
        return base


class StructuredLoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that automatically maps arbitrary keyword arguments into
    extra fields for structured logging.
    """

    def process(self, msg: Any, kwargs: Any) -> tuple[Any, Any]:
        # Extract kwargs that are not standard logging kwargs
        std_kwargs = {"exc_info", "stack_info", "stacklevel", "extra"}
        extra = kwargs.get("extra", {}) or {}
        custom_kwargs = {}
        for k in list(kwargs.keys()):
            if k not in std_kwargs:
                custom_kwargs[k] = kwargs.pop(k)

        extra.update(self.extra or {})
        extra.update(custom_kwargs)
        kwargs["extra"] = extra
        return msg, kwargs


def configure_logging(level: str = "INFO") -> None:
    """
    Configure root logger with structured formatting.
    Should be called once at application startup.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(numeric_level)
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)
    handler.setFormatter(_SafeFormatter())
    root.addHandler(handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("psycopg").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> StructuredLoggerAdapter:
    """
    Get a structured logger that supports arbitrary keyword arguments.
    Example: logger.info("Order processed", order_id="123", amount=45.5)
    """
    logger = logging.getLogger(name)
    return StructuredLoggerAdapter(logger, {})
