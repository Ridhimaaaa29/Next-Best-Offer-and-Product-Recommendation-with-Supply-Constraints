"""Mandatory Laya decision adapter with lazy model loading and deterministic safety.

Laya operates strictly downstream of the deterministic policy engine:
No candidate reaches this adapter until the authoritative policy engine has marked it feasible.
Model checkpoints are loaded lazily on demand to optimize memory and startup time.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Any, Optional
from backend.app.config import settings


class LayaAdapter:
    """Documented Laya Router decision adapter with lazy model loading."""

    _cached_router: Any = None

    def __init__(
        self,
        enabled: Optional[bool] = None,
        router: Any = None,
        cache_dir: Optional[str | Path] = None,
    ) -> None:
        # Precedence for enabled: constructor > environment variable > centralized settings
        if enabled is not None:
            self._enabled = enabled
        else:
            env_val = os.getenv("LAYA_ENABLED")
            if env_val is not None:
                self._enabled = env_val.strip().lower() in ("true", "1", "yes")
            else:
                self._enabled = getattr(settings, "laya_enabled", True)

        # Precedence for cache_dir: constructor > environment variable > centralized settings
        if cache_dir is not None:
            self._cache_dir = Path(cache_dir)
        elif os.getenv("LAYA_CACHE_DIR"):
            self._cache_dir = Path(os.environ["LAYA_CACHE_DIR"])
        else:
            default_setting = getattr(settings, "laya_cache_dir", None)
            self._cache_dir = Path(default_setting) if default_setting else None

        self._custom_router = router
        self.reason: Optional[str] = None if self._enabled else "Laya is disabled in configuration."

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def is_installed(self) -> bool:
        """Lightweight check whether the laya package is installed in Python."""
        try:
            return importlib.util.find_spec("laya") is not None
        except Exception:
            return False

    @property
    def is_loaded(self) -> bool:
        """Check whether the Laya model runtime has actually been initialized into memory."""
        return self._custom_router is not None or LayaAdapter._cached_router is not None

    @property
    def available(self) -> bool:
        """
        Lightweight availability check:
        True if Laya is configured/enabled and either already loaded or installed and ready to be loaded.
        Does NOT trigger model initialization or checkpoint downloads.
        """
        if not self._enabled:
            return False
        return self.is_loaded or self.is_installed

    def status_info(self) -> dict[str, Any]:
        """Return a lightweight status summary without loading models."""
        return {
            "configured": self._enabled,
            "enabled": self._enabled,
            "installed": self.is_installed,
            "loaded": self.is_loaded,
            "available": self.available,
            "cache_dir": str(self._cache_dir) if self._cache_dir else None,
            "reason": self.reason if not self.available else None,
        }

    def _get_router(self) -> Any:
        """Lazily load and cache the Laya Router."""
        if not self._enabled:
            raise RuntimeError(self.reason or "Laya is disabled in configuration.")

        if self._custom_router is not None:
            return self._custom_router

        if LayaAdapter._cached_router is not None:
            return LayaAdapter._cached_router

        if self._cache_dir:
            os.environ.setdefault("HF_HOME", str(self._cache_dir))
            os.environ.setdefault("TRANSFORMERS_CACHE", str(self._cache_dir))
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

        try:
            from laya import Router

            LayaAdapter._cached_router = Router()
            return LayaAdapter._cached_router
        except ImportError as error:
            self._enabled = False
            self.reason = f"Laya package is not installed: {error}"
            raise RuntimeError(self.reason) from error
        except Exception as error:
            self._enabled = False
            self.reason = f"Laya initialization failed: {type(error).__name__}: {error}"
            raise RuntimeError(self.reason) from error

    def choose(self, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Invoke Laya Router on already policy-feasible candidates.

        Raises:
            ValueError: If candidates list is empty or response is malformed.
            RuntimeError: If Laya is disabled, unavailable, or selects an unrecognized option.
        """
        if not candidates:
            raise ValueError("Laya requires at least one feasible candidate.")

        router = self._get_router()
        if router is None:
            raise RuntimeError(self.reason or "Laya router is unavailable.")

        options = [str(candidate["product_id"]) for candidate in candidates if "product_id" in candidate]
        if not options:
            raise ValueError("No valid product_ids found in candidates.")

        prompt = (
            "Choose the best next-best-offer from the feasible product IDs. "
            f"Customer options: {', '.join(options)}."
        )
        questions = {
            "selected_product_id": {
                "type": "choice",
                "instructions": "Which feasible product is the best next-best-offer?",
                "criteria": {product_id: product_id for product_id in options},
            }
        }

        try:
            result = router.predict(prompt, questions)
        except Exception as error:
            raise RuntimeError(f"Laya inference failed: {type(error).__name__}: {error}") from error

        # Validate response structure for malformed outputs
        if not isinstance(result, dict):
            raise ValueError(f"Laya returned malformed result: expected dict, got {type(result).__name__}")

        answers = result.get("answers")
        if not isinstance(answers, dict):
            raise ValueError("Laya returned malformed result: 'answers' field is missing or not a dict.")

        answer = answers.get("selected_product_id")
        selected = None
        if isinstance(answer, dict):
            selected = answer.get("choice")
        elif isinstance(answer, str):
            selected = answer

        if not selected or not isinstance(selected, str):
            raise ValueError(f"Laya returned malformed or empty candidate choice: {answer}")

        selected_candidate = next((item for item in candidates if str(item.get("product_id")) == str(selected)), None)
        if selected_candidate is None:
            raise RuntimeError(f"Laya returned candidate '{selected}' not present in feasible options: {options}")

        return {
            "selected": selected_candidate,
            "explanation": "Selected by Laya Router from the policy-feasible candidate set.",
            "raw_result": result,
        }
