"""Lightweight deterministic weighted multi-objective decision engine.

Operates strictly downstream of the authoritative policy engine: only candidates
that already passed deterministic supply, margin, and context feasibility checks
reach this component. Zero heavyweight ML weights or external LLM calls are used.
"""

from __future__ import annotations

import os
from typing import Any, Callable, Optional

from backend.app.config import settings
from backend.app.decision.objectives import (
    DECISION_FORMULA,
    DecisionWeights,
    compute_diversity_scores,
    compute_operational_friction,
    normalize_margin,
    normalize_relevance,
)


class WeightedDecisionEngine:
    """Deterministic multi-objective weighted ranker for policy-feasible offers."""

    def __init__(
        self,
        enabled: Optional[bool] = None,
        weights: Optional[DecisionWeights] = None,
        custom_selector: Optional[Callable[[list[dict[str, Any]]], dict[str, Any]]] = None,
    ) -> None:
        if enabled is not None:
            self._enabled = enabled
        else:
            env_val = os.getenv("DECISION_ENGINE_ENABLED")
            if env_val is not None:
                self._enabled = env_val.strip().lower() in ("true", "1", "yes")
            else:
                self._enabled = getattr(settings, "decision_engine_enabled", True)

        self._weights = weights or DecisionWeights(
            relevance=getattr(settings, "decision_weight_relevance", 0.45),
            margin=getattr(settings, "decision_weight_margin", 0.25),
            diversity=getattr(settings, "decision_weight_diversity", 0.15),
            friction=getattr(settings, "decision_weight_friction", 0.15),
        )
        self._custom_selector = custom_selector
        self.reason: Optional[str] = (
            None if self._enabled else "Weighted decision engine is disabled in configuration."
        )

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def available(self) -> bool:
        return self._enabled

    def normalized_weights(self) -> dict[str, float]:
        return self._weights.normalized()

    def status_info(self) -> dict[str, Any]:
        """Return lightweight configuration and readiness status."""
        weights: dict[str, float] | None = None
        reason = self.reason
        available = self._enabled
        try:
            weights = self.normalized_weights()
        except ValueError as error:
            available = False
            reason = str(error)

        return {
            "configured": self._enabled,
            "enabled": self._enabled,
            "available": available,
            "engine": "lightweight_weighted_decision_engine",
            "formula": DECISION_FORMULA,
            "weights": weights,
            "reason": reason if not available else None,
        }

    def choose(
        self,
        candidates: list[dict[str, Any]],
        express_context: bool = False,
    ) -> dict[str, Any]:
        """
        Evaluate and rank policy-feasible candidates using normalised multi-objective weights.

        Raises:
            ValueError: If candidates is empty, weights are invalid, or custom selector output is malformed.
            RuntimeError: If engine is disabled or returns an unrecognised product ID.
        """
        if not self._enabled:
            raise RuntimeError(self.reason or "Weighted decision engine is disabled.")
        if not candidates:
            raise ValueError("Decision engine requires at least one feasible candidate.")

        options = [str(c["product_id"]) for c in candidates if c.get("product_id")]
        if len(options) != len(candidates):
            raise ValueError("All candidates must include a valid 'product_id'.")

        weights = self.normalized_weights()
        diversity_map = compute_diversity_scores(candidates)

        scored_entries: list[dict[str, Any]] = []
        objective_scores_map: dict[str, dict[str, Any]] = {}

        for candidate in candidates:
            pid = str(candidate["product_id"])
            relevance = normalize_relevance(candidate.get("recommendation_score"))
            margin = normalize_margin(candidate.get("gross_margin_pct"))
            diversity = diversity_map.get(pid, 1.0)
            friction, suitability = compute_operational_friction(
                candidate, express_context=express_context
            )

            weighted_score = round(
                weights["relevance"] * relevance
                + weights["margin"] * margin
                + weights["diversity"] * diversity
                - weights["friction"] * friction,
                4,
            )

            objectives = {
                "recommendation_relevance": relevance,
                "margin_contribution": margin,
                "product_diversity": diversity,
                "operational_suitability": suitability,
                "operational_friction": friction,
                "weighted_score": weighted_score,
            }
            objective_scores_map[pid] = objectives

            enriched = {
                **candidate,
                "objective_scores": objectives,
                "weighted_score": weighted_score,
            }
            scored_entries.append(enriched)

        scored_entries.sort(
            key=lambda item: (
                -item["weighted_score"],
                -float(item.get("recommendation_score") or 0.0),
                str(item["product_id"]),
            )
        )
        for rank_idx, entry in enumerate(scored_entries, start=1):
            entry["rank"] = rank_idx
            objective_scores_map[str(entry["product_id"])]["rank"] = rank_idx

        if self._custom_selector is not None:
            raw_selected = self._custom_selector(scored_entries)
            if not isinstance(raw_selected, dict) or not raw_selected.get("product_id"):
                raise ValueError(
                    f"Decision selector returned malformed output: {raw_selected!r}"
                )
            selected_id = str(raw_selected["product_id"])
            selected_candidate = next(
                (item for item in scored_entries if str(item["product_id"]) == selected_id),
                None,
            )
            if selected_candidate is None:
                raise RuntimeError(
                    f"Decision engine selected '{selected_id}' which is not present in feasible options: {options}"
                )
        else:
            selected_candidate = scored_entries[0]
            selected_id = str(selected_candidate["product_id"])

        win_obj = selected_candidate["objective_scores"]
        explanation = (
            f"Selected {selected_id} by deterministic weighted decision engine "
            f"(weighted_score={win_obj['weighted_score']:.4f}; "
            f"relevance={win_obj['recommendation_relevance']:.2f}×{weights['relevance']:.2f}, "
            f"margin={win_obj['margin_contribution']:.2f}×{weights['margin']:.2f}, "
            f"diversity={win_obj['product_diversity']:.2f}×{weights['diversity']:.2f}, "
            f"friction=-{win_obj['operational_friction']:.2f}×{weights['friction']:.2f})."
        )

        return {
            "selected_product_id": selected_id,
            "selected": selected_candidate,
            "ranked_candidates": scored_entries,
            "objective_scores": objective_scores_map,
            "weights": weights,
            "formula": DECISION_FORMULA,
            "explanation": explanation,
        }
