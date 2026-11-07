"""Optional Laya decision adapter with deterministic fallback.

Laya is intentionally optional because its checkpoint-backed runtime is not
part of the base application install. No candidate reaches this adapter until
the authoritative policy engine has marked it feasible.
"""

import os
from typing import Any


class LayaAdapter:
    """Use documented Laya Router only when explicitly enabled and installed."""

    def __init__(self) -> None:
        self.enabled = False
        self.reason = "Laya is not installed or not explicitly enabled."
        self._router: Any = None
        if os.getenv("LAYA_ENABLED", "false").lower() != "true":
            return
        cache_dir = os.getenv("LAYA_CACHE_DIR")
        if cache_dir:
            os.environ.setdefault("HF_HOME", cache_dir)
            os.environ.setdefault("TRANSFORMERS_CACHE", cache_dir)
        try:
            from laya import Router

            self._router = Router()
            self.enabled = True
            self.reason = None
        except Exception as error:
            self.reason = f"Laya initialization failed: {type(error).__name__}"

    def choose(self, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        if not candidates:
            raise ValueError("Laya requires at least one feasible candidate.")
        if not self.enabled or self._router is None:
            raise RuntimeError(self.reason or "Laya is unavailable.")
        options = [candidate["product_id"] for candidate in candidates]
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
        result = self._router.predict(prompt, questions)
        selected = None
        if isinstance(result, dict):
            answer = result.get("answers", {}).get("selected_product_id", {})
            selected = answer.get("choice") if isinstance(answer, dict) else answer
        selected_candidate = next((item for item in candidates if item["product_id"] == selected), None)
        if selected_candidate is None:
            raise RuntimeError("Laya returned an unrecognized candidate.")
        return {
            "selected": selected_candidate,
            "explanation": "Selected by Laya Router from the policy-feasible candidate set.",
        }
