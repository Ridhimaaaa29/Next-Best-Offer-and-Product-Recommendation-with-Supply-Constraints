"""
Centralized Application Configuration
Project: Next-Best-Offer and Product Recommendation with Supply Constraints

Single source of truth for all environment variables and application settings.
Eliminates the duplicate load_dotenv() / os.getenv() pattern across pipeline modules.

SECURITY: Credentials are never logged or exposed in API responses.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


# Project root is two levels above this file:
# backend/app/config.py → backend/app/ → backend/ → project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables / .env file.
    All fields with secrets are excluded from repr and logging.
    """

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ----------------------------------------------------------------
    # Database
    # ----------------------------------------------------------------
    database_url: str

    # ----------------------------------------------------------------
    # ML Model
    # ----------------------------------------------------------------
    model_artifact_path: Path = PROJECT_ROOT / "models" / "nbo_propensity_best_model.joblib"
    use_ml_scoring: bool = True

    # ----------------------------------------------------------------
    # API
    # ----------------------------------------------------------------
    app_title: str = "Next-Best-Offer Recommendation API"
    app_version: str = "1.0.0"
    app_description: str = (
        "Supply-constrained Next-Best-Offer recommendation engine. "
        "Combines ML propensity scoring with deterministic policy constraints."
    )
    api_prefix: str = "/api/v1"
    debug: bool = False

    # ----------------------------------------------------------------
    # Logging
    # ----------------------------------------------------------------
    log_level: str = "INFO"

    # Optional Groq assistant configuration
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-120b"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    # ----------------------------------------------------------------
    # Laya Decision Layer
    # ----------------------------------------------------------------
    laya_enabled: bool = True
    laya_cache_dir: Path | None = PROJECT_ROOT / ".laya-cache"

    def __repr__(self) -> str:
        """Safe repr — never exposes DATABASE_URL or secrets."""
        return (
            f"Settings(app_version={self.app_version!r}, "
            f"api_prefix={self.api_prefix!r}, "
            f"use_ml_scoring={self.use_ml_scoring}, "
            f"model_artifact_path={self.model_artifact_path}, "
            f"log_level={self.log_level!r}, "
            f"database_url=<redacted>)"
        )


# Singleton instance — import this everywhere instead of os.getenv()
settings = Settings()
