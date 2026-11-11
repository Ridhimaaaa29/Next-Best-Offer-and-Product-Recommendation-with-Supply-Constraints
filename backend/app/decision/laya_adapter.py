"""Lightweight-configured Laya decision adapter with lazy singleton reuse.

Executes strictly downstream of the deterministic policy engine over a capped
shortlist of policy-feasible candidates. Preserves real Laya (`convaiinnovations/laya`)
inference while minimizing RSS footprint via:
- Lazy initialization (`preload=False`, `vega=False`, zero torch/laya import at startup)
- Process-wide singleton reuse shared between REST and in-process MCP workflow
- CPU-only `max_loaded=1`, capped intra-op threads, disabled `torch.compile`/`vegaml`
- Optional post-load CPU `bfloat16` weight cast + `gc.collect()` to reclaim FP32 load overhead
- Configurable `max_candidates` cap so only top feasible candidates enter Laya prompts
"""

from __future__ import annotations

import gc
import importlib.util
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from pathlib import Path
from typing import Any, Callable, Optional

from backend.app.config import settings


def _has_local_laya_snapshot(cache_dir: Optional[Path]) -> bool:
    if cache_dir is None or not cache_dir.exists():
        return False
    return any(cache_dir.rglob("model.safetensors"))


class LayaAdapter:
    """Lazy, thread-safe singleton adapter for real Laya decision inference."""

    _router_lock = threading.Lock()
    _cached_router: Any = None
    _cached_router_key: tuple[Any, ...] | None = None

    def __init__(
        self,
        enabled: Optional[bool] = None,
        router: Any = None,
        cache_dir: Optional[str | Path] = None,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        cpu_bfloat16: Optional[bool] = None,
        max_candidates: Optional[int] = None,
        threads: Optional[int] = None,
        timeout_seconds: Optional[float] = None,
        custom_selector: Optional[Callable[[list[dict[str, Any]]], dict[str, Any]]] = None,
        app_env: Optional[str] = None,
    ) -> None:
        self._app_env = (
            (app_env or os.getenv("APP_ENV") or getattr(settings, "app_env", "local"))
            .strip()
            .lower()
        )
        if enabled is not None:
            self._enabled = bool(enabled)
            explicit_disabled_reason = "Laya is disabled in configuration."
        else:
            env_val = os.getenv("LAYA_ENABLED")
            if env_val is not None:
                self._enabled = env_val.strip().lower() in ("true", "1", "yes")
                explicit_disabled_reason = (
                    "Laya inference is disabled (LAYA_ENABLED=false; "
                    f"APP_ENV={self._app_env}) — using WeightedDecisionEngine fallback."
                )
            elif self._app_env in ("production", "prod", "render"):
                self._enabled = False
                explicit_disabled_reason = (
                    "Laya inference is unavailable in production deployment "
                    f"(APP_ENV={self._app_env}) due to the 512 MB memory limitation; "
                    "using WeightedDecisionEngine fallback."
                )
            else:
                self._enabled = bool(getattr(settings, "laya_enabled", True))
                explicit_disabled_reason = "Laya is disabled in configuration."

        if cache_dir is not None:
            self._cache_dir = Path(cache_dir)
        elif os.getenv("LAYA_CACHE_DIR"):
            self._cache_dir = Path(os.environ["LAYA_CACHE_DIR"])
        else:
            default_setting = getattr(settings, "laya_cache_dir", None)
            self._cache_dir = Path(default_setting) if default_setting else None

        self._model_name = (
            model_name
            or os.getenv("LAYA_MODEL")
            or getattr(settings, "laya_model", "english")
        )
        self._device = (
            device
            or os.getenv("LAYA_DEVICE")
            or getattr(settings, "laya_device", "cpu")
        )
        if cpu_bfloat16 is not None:
            self._cpu_bfloat16 = bool(cpu_bfloat16)
        else:
            env_bf16 = os.getenv("LAYA_CPU_BFLOAT16")
            if env_bf16 is not None:
                self._cpu_bfloat16 = env_bf16.strip().lower() in ("true", "1", "yes")
            else:
                self._cpu_bfloat16 = bool(getattr(settings, "laya_cpu_bfloat16", False))

        self._max_candidates = max(
            1,
            int(
                max_candidates
                if max_candidates is not None
                else os.getenv("LAYA_MAX_CANDIDATES")
                or getattr(settings, "laya_max_candidates", 5)
            ),
        )
        raw_threads = (
            threads
            if threads is not None
            else os.getenv("LAYA_THREADS")
            if os.getenv("LAYA_THREADS") is not None
            else getattr(settings, "laya_threads", 0)
        )
        self._threads = max(0, int(raw_threads))
        self._timeout_seconds = float(
            timeout_seconds
            if timeout_seconds is not None
            else os.getenv("LAYA_TIMEOUT_SECONDS")
            or getattr(settings, "laya_timeout_seconds", 45.0)
        )
        self._custom_router = router
        self._custom_selector = custom_selector
        env_preload = os.getenv("LAYA_PRELOAD_ON_STARTUP")
        if env_preload is not None:
            self._preload_on_startup = env_preload.strip().lower() in ("true", "1", "yes")
        else:
            self._preload_on_startup = bool(getattr(settings, "laya_preload_on_startup", False))
        self.reason: Optional[str] = None if self._enabled else explicit_disabled_reason

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def max_candidates(self) -> int:
        return self._max_candidates

    @property
    def is_installed(self) -> bool:
        """Check whether the `laya` package is importable without loading weights."""
        try:
            return importlib.util.find_spec("laya") is not None
        except Exception:
            return False

    @property
    def is_loaded(self) -> bool:
        """Return True only when a Laya router/model instance is already resident in memory."""
        return (
            self._custom_router is not None
            or self._custom_selector is not None
            or LayaAdapter._cached_router is not None
        )

    @property
    def available(self) -> bool:
        """Lightweight readiness check without triggering model weights load."""
        if not self._enabled:
            return False
        return self.is_loaded or self.is_installed

    def status_info(self) -> dict[str, Any]:
        """Return lightweight configuration and readiness telemetry without loading weights."""
        avail = self.available
        return {
            "app_env": self._app_env,
            "engine": "laya",
            "decision_provider": "laya" if avail else "lightweight_weighted_decision_engine",
            "configured": self._enabled,
            "enabled": self._enabled,
            "installed": self.is_installed,
            "loaded": self.is_loaded,
            "available": avail,
            "laya_available": avail,
            "model": self._model_name,
            "device": self._device,
            "cpu_bfloat16": self._cpu_bfloat16,
            "max_candidates": self._max_candidates,
            "threads": self._threads,
            "vega_disabled": True,
            "preload": self._preload_on_startup or self.is_loaded,
            "cache_dir": str(self._cache_dir) if self._cache_dir else None,
            "offline_cache_ready": _has_local_laya_snapshot(self._cache_dir),
            "fallback_engine": "lightweight_weighted_decision_engine",
            "reason": self.reason if not avail else None,
        }

    def warmup(self) -> dict[str, Any]:
        """Eagerly load the shared Laya singleton once (used on AWS startup warmup)."""
        if not self._enabled:
            return {
                "warmed": False,
                "loaded": False,
                "reason": self.reason or "Laya disabled",
                "elapsed_seconds": 0.0,
            }
        started = time.perf_counter()
        try:
            self._get_router()
            elapsed = round(time.perf_counter() - started, 3)
            return {
                "warmed": True,
                "loaded": self.is_loaded,
                "model": self._model_name,
                "cache_dir": str(self._cache_dir) if self._cache_dir else None,
                "offline_cache_ready": _has_local_laya_snapshot(self._cache_dir),
                "elapsed_seconds": elapsed,
            }
        except Exception as error:
            elapsed = round(time.perf_counter() - started, 3)
            return {
                "warmed": False,
                "loaded": self.is_loaded,
                "reason": str(error),
                "elapsed_seconds": elapsed,
            }

    def _config_key(self) -> tuple[Any, ...]:
        return (
            self._model_name,
            self._device,
            self._cpu_bfloat16,
            str(self._cache_dir) if self._cache_dir else None,
        )

    def _get_router(self) -> Any:
        """Lazily build and cache a single shared Laya Router across the process."""
        if not self._enabled:
            raise RuntimeError(self.reason or "Laya is disabled in configuration.")

        if self._custom_router is not None:
            return self._custom_router

        cfg_key = self._config_key()
        with LayaAdapter._router_lock:
            if (
                LayaAdapter._cached_router is not None
                and LayaAdapter._cached_router_key == cfg_key
            ):
                return LayaAdapter._cached_router

            if self._cache_dir is not None:
                os.environ["HF_HOME"] = str(self._cache_dir)
                os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
                if _has_local_laya_snapshot(self._cache_dir):
                    os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ.setdefault("USE_TF", "0")

            try:
                import torch
                import laya

                if self._device == "cpu" and self._threads > 0:
                    try:
                        torch.set_num_threads(self._threads)
                    except Exception:
                        pass

                router = laya.Router(
                    default=self._model_name,
                    device=self._device,
                    max_loaded=1,
                    preload=False,
                    vega=False,
                    agent_kwargs={"compile": False, "fast": False},
                )
                # Eagerly materialize only the requested default checkpoint inside the lock
                # so post-load memory cleanup / optional bfloat16 cast happens once cleanly.
                agent = router.load(router.default)
                if (
                    self._cpu_bfloat16
                    and self._device == "cpu"
                    and hasattr(agent, "model")
                    and agent.model is not None
                ):
                    try:
                        agent.model.to(dtype=torch.bfloat16)
                    except Exception:
                        # Keep float32 silently if host/model rejects bfloat16 conversion
                        pass
                gc.collect()
                LayaAdapter._cached_router = router
                LayaAdapter._cached_router_key = cfg_key
                return router
            except ImportError as error:
                self._enabled = False
                self.reason = f"Laya package is not installed: {error}"
                raise RuntimeError(self.reason) from error
            except Exception as error:
                self.reason = f"Laya initialization failed: {type(error).__name__}: {error}"
                raise RuntimeError(self.reason) from error

    @classmethod
    def reset_shared_instance(cls) -> None:
        """Release cached router reference (primarily for controlled tests)."""
        with cls._router_lock:
            cls._cached_router = None
            cls._cached_router_key = None
        gc.collect()

    def _build_prompt_and_questions(
        self,
        shortlist: list[dict[str, Any]],
        express_context: bool = False,
    ) -> tuple[str, dict[str, Any]]:
        lines = [
            "Select the single best Next-Best-Offer SKU from these policy-feasible products.",
            f"Express shipping preference: {'yes' if express_context else 'no'}.",
            "Feasible candidates:",
        ]
        criteria: dict[str, str] = {}
        for idx, item in enumerate(shortlist, 1):
            pid = str(item["product_id"])
            name = str(item.get("product_name") or pid)[:48]
            cat = str(item.get("subcategory") or item.get("category") or "general")[:24]
            score = float(item.get("recommendation_score") or 0.0)
            margin = item.get("gross_margin_pct")
            ship = item.get("shipping_days")
            margin_str = f"{float(margin) * 100:.0f}%" if margin is not None else "n/a"
            ship_str = f"{int(ship)}d" if ship is not None else "n/a"
            lines.append(
                f"{idx}. {pid} ({name}, {cat}, propensity={score:.2f}, margin={margin_str}, ship={ship_str})"
            )
            criteria[pid] = f"{pid}: {name} (score={score:.2f}, margin={margin_str}, ship={ship_str})"

        prompt = " ".join(lines)
        questions = {
            "selected_product_id": {
                "type": "choice",
                "instructions": "Which policy-feasible product_id is the optimal Next-Best-Offer?",
                "criteria": criteria,
            }
        }
        return prompt, questions

    def choose(
        self,
        candidates: list[dict[str, Any]],
        express_context: bool = False,
    ) -> dict[str, Any]:
        """Invoke real Laya decision inference over a capped shortlist of feasible candidates."""
        if not self._enabled:
            raise RuntimeError(self.reason or "Laya is disabled in configuration.")
        if not candidates:
            raise ValueError("Laya requires at least one policy-feasible candidate.")

        shortlist = candidates[: self._max_candidates]
        options = [str(item["product_id"]) for item in shortlist if item.get("product_id")]
        if len(options) != len(shortlist):
            raise ValueError("All candidates passed to Laya must include 'product_id'.")

        if self._custom_selector is not None:
            raw_choice = self._custom_selector(shortlist)
            if not isinstance(raw_choice, dict) or not raw_choice.get("product_id"):
                raise ValueError(f"Laya selector returned malformed output: {raw_choice!r}")
            selected = str(raw_choice["product_id"])
            selected_candidate = next(
                (item for item in shortlist if str(item.get("product_id")) == selected),
                None,
            )
            if selected_candidate is None:
                raise RuntimeError(
                    f"Laya returned candidate '{selected}' not present in feasible options: {options}"
                )
            return {
                "selected": selected_candidate,
                "selected_product_id": selected,
                "explanation": "Selected by Laya from the capped policy-feasible candidate set.",
                "raw_result": raw_choice,
                "candidate_pool_size": len(shortlist),
                "confidence": None,
            }

        router = self._get_router()
        if router is None:
            raise RuntimeError(self.reason or "Laya router is unavailable.")

        prompt, questions = self._build_prompt_and_questions(
            shortlist, express_context=express_context
        )

        def _run_predict() -> Any:
            return router.predict(prompt, questions)

        try:
            if self._timeout_seconds > 0 and self._custom_router is None:
                pool = ThreadPoolExecutor(max_workers=1)
                fut = pool.submit(_run_predict)
                try:
                    result = fut.result(timeout=self._timeout_seconds)
                finally:
                    pool.shutdown(wait=False, cancel_futures=True)
            else:
                result = _run_predict()
        except FutureTimeoutError as error:
            raise RuntimeError(
                f"Laya inference timed out after {self._timeout_seconds:.1f}s."
            ) from error
        except Exception as error:
            raise RuntimeError(f"Laya inference failed: {type(error).__name__}: {error}") from error

        if not isinstance(result, dict):
            raise ValueError(
                f"Laya returned malformed result: expected dict, got {type(result).__name__}"
            )

        answers = result.get("answers")
        if not isinstance(answers, dict):
            raise ValueError("Laya returned malformed result: 'answers' field is missing or not a dict.")

        answer = answers.get("selected_product_id")
        selected: Optional[str] = None
        confidence: Optional[float] = None
        if isinstance(answer, dict):
            selected = answer.get("choice")
            raw_conf = answer.get("answer_confidence", answer.get("confidence"))
            if isinstance(raw_conf, (int, float)):
                confidence = round(float(raw_conf), 4)
        elif isinstance(answer, str):
            selected = answer

        if not selected or not isinstance(selected, str):
            raise ValueError(f"Laya returned malformed or empty candidate choice: {answer!r}")

        selected_candidate = next(
            (item for item in shortlist if str(item.get("product_id")) == str(selected)),
            None,
        )
        if selected_candidate is None:
            raise RuntimeError(
                f"Laya returned candidate '{selected}' not present in feasible options: {options}"
            )

        return {
            "selected": selected_candidate,
            "selected_product_id": str(selected),
            "explanation": (
                f"Selected {selected} via Laya ({self._model_name}) from "
                f"{len(shortlist)} policy-feasible shortlist candidates."
            ),
            "raw_result": result,
            "candidate_pool_size": len(shortlist),
            "confidence": confidence,
        }
