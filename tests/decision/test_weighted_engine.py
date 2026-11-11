"""Unit & integration tests for the lightweight deterministic weighted decision engine."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from backend.app.decision.laya_adapter import LayaAdapter
from backend.app.decision.objectives import DecisionWeights
from backend.app.decision.weighted_engine import WeightedDecisionEngine
from backend.app.recommendation.decision_module import DecisionModule
from backend.app.recommendation.recommendation_model import (
    ScoreExplanation,
    ScoredCandidate,
)


def _scored(
    product_id: str,
    score: float,
    category: str = "Electronics",
    subcategory: str = "Audio",
    brand: str = "BrandX",
) -> ScoredCandidate:
    return ScoredCandidate(
        product_id=product_id,
        product_name=f"Product {product_id}",
        category=category,
        subcategory=subcategory,
        brand=brand,
        unit_price=100.0,
        product_rating=4.5,
        product_popularity=0.8,
        product_status="active",
        score=score,
        explanation=ScoreExplanation(
            category_affinity_score=score,
            popularity_score=0.8,
            rating_score=0.9,
            interaction_bonus=0.1,
            composite_score=score,
            reason_codes=["ML propensity score"],
        ),
    )


def test_decision_weights_normalization_and_validation():
    weights = DecisionWeights(relevance=9.0, margin=5.0, diversity=3.0, friction=3.0)
    norm = weights.normalized()
    assert pytest.approx(sum(norm.values()), abs=1e-6) == 1.0
    assert norm == {
        "relevance": 0.45,
        "margin": 0.25,
        "diversity": 0.15,
        "friction": 0.15,
    }

    with pytest.raises(ValueError, match="negative"):
        DecisionWeights(relevance=-0.1, margin=0.5, diversity=0.3, friction=0.3).normalized()

    with pytest.raises(ValueError, match="strictly positive"):
        DecisionWeights(relevance=0.0, margin=0.0, diversity=0.0, friction=0.0).normalized()


def test_weighted_engine_ranks_multi_objective_tradeoffs():
    engine = WeightedDecisionEngine(
        enabled=True,
        weights=DecisionWeights(relevance=0.45, margin=0.25, diversity=0.15, friction=0.15),
    )
    candidates = [
        {
            "product_id": "PROD_LOW_MARGIN",
            "product_name": "Low Margin Popular",
            "recommendation_score": 0.90,
            "gross_margin_pct": 0.12,
            "subcategory": "Audio",
            "brand": "BrandA",
            "shipping_days": 8,
            "available_stock": 8,
            "reorder_point": 15,
            "inventory_status": "low_stock",
        },
        {
            "product_id": "PROD_BALANCED_HIGH",
            "product_name": "High Margin Fast Fulfilment",
            "recommendation_score": 0.85,
            "gross_margin_pct": 0.72,
            "subcategory": "Wearables",
            "brand": "BrandB",
            "shipping_days": 1,
            "available_stock": 60,
            "reorder_point": 10,
            "inventory_status": "available",
        },
        {
            "product_id": "PROD_COMMON_SUBCAT",
            "product_name": "Duplicate Subcategory",
            "recommendation_score": 0.80,
            "gross_margin_pct": 0.30,
            "subcategory": "Audio",
            "brand": "BrandA",
            "shipping_days": 3,
            "available_stock": 30,
            "reorder_point": 10,
            "inventory_status": "available",
        },
    ]

    result = engine.choose(candidates, express_context=True)

    assert result["selected_product_id"] == "PROD_BALANCED_HIGH"
    assert result["ranked_candidates"][0]["rank"] == 1
    assert set(result["objective_scores"]) == {
        "PROD_LOW_MARGIN",
        "PROD_BALANCED_HIGH",
        "PROD_COMMON_SUBCAT",
    }
    assert result["objective_scores"]["PROD_BALANCED_HIGH"]["operational_friction"] < (
        result["objective_scores"]["PROD_LOW_MARGIN"]["operational_friction"]
    )
    assert "weighted_score=" in result["explanation"]


def test_weighted_engine_handles_single_and_empty_candidates():
    engine = WeightedDecisionEngine(enabled=True)
    with pytest.raises(ValueError, match="at least one feasible candidate"):
        engine.choose([])

    single = engine.choose(
        [
            {
                "product_id": "PROD_ONLY",
                "product_name": "Only Option",
                "recommendation_score": 0.75,
                "gross_margin_pct": 0.35,
                "shipping_days": 2,
                "available_stock": 20,
                "inventory_status": "available",
            }
        ]
    )
    assert single["selected_product_id"] == "PROD_ONLY"
    assert single["ranked_candidates"][0]["rank"] == 1


def test_decision_module_excludes_infeasible_and_returns_empty_when_all_excluded():
    recommender = Mock()
    recommender.rank_candidates.return_value = [_scored("PROD_BAD_1", 0.95), _scored("PROD_BAD_2", 0.80)]
    module = DecisionModule(recommender=recommender, decision_engine=WeightedDecisionEngine(enabled=True))
    module._validate_customer_exists = Mock()
    module._load_operational_map = Mock(return_value={})

    with patch(
        "backend.app.recommendation.decision_module.evaluate_product",
        return_value={"product_id": "MOCK", "decision": "EXCLUDE", "reasons": ["Out of stock."], "flags": []},
    ):
        result = module.decide("CUST_0001", top_k=5)

    assert result["status"] == "ALL_CANDIDATES_EXCLUDED"
    assert result["feasible_count"] == 0
    assert result["excluded_count"] == 2
    assert result["recommendations"] == []
    assert result["decision_method"] == "NONE"


def test_decision_module_fallback_on_disabled_laya_or_invalid_choice():
    candidates = [_scored("PROD_1", 0.91), _scored("PROD_2", 0.75), _scored("PROD_EXCL", 0.99)]
    recommender = Mock()
    recommender.rank_candidates.return_value = candidates

    bad_laya = LayaAdapter(
        enabled=True,
        custom_selector=lambda _: {"product_id": "PROD_HALLUCINATED"},
    )
    module = DecisionModule(
        recommender=recommender,
        laya_adapter=bad_laya,
        decision_engine=WeightedDecisionEngine(enabled=True),
    )
    module._validate_customer_exists = Mock()
    module._load_operational_map = Mock(
        return_value={
            "PROD_1": {"gross_margin_pct": 0.4, "shipping_days": 2, "available_stock": 25, "inventory_status": "available"},
            "PROD_2": {"gross_margin_pct": 0.3, "shipping_days": 3, "available_stock": 25, "inventory_status": "available"},
        }
    )

    def _policy(product_id, **_):
        if product_id == "PROD_EXCL":
            return {"product_id": product_id, "decision": "EXCLUDE", "reasons": ["Out of stock."], "flags": []}
        return {"product_id": product_id, "decision": "PASS", "reasons": [], "flags": []}

    with patch("backend.app.recommendation.decision_module.evaluate_product", side_effect=_policy):
        result = module.decide("CUST_0001", top_k=2)

    assert result["status"] == "SUCCESS"
    assert result["fallback_used"] is True
    assert result["decision_method"] == "WEIGHTED_DECISION_FALLBACK"
    assert "PROD_HALLUCINATED" in (result["fallback_reason"] or "")
    assert [r["product_id"] for r in result["recommendations"]] == ["PROD_1", "PROD_2"]
    assert "PROD_EXCL" not in [r["product_id"] for r in result["recommendations"]]


def test_decision_module_post_selection_revalidation_rejects_and_falls_back():
    candidates = [_scored("PROD_A", 0.90), _scored("PROD_B", 0.80)]
    recommender = Mock()
    recommender.rank_candidates.return_value = candidates

    laya_pick = LayaAdapter(enabled=True, custom_selector=lambda _: {"product_id": "PROD_A"})
    module = DecisionModule(
        recommender=recommender,
        laya_adapter=laya_pick,
        decision_engine=WeightedDecisionEngine(enabled=True),
    )
    module._validate_customer_exists = Mock()
    module._load_operational_map = Mock(
        return_value={
            "PROD_A": {"gross_margin_pct": 0.6, "shipping_days": 1, "available_stock": 40, "inventory_status": "available"},
            "PROD_B": {"gross_margin_pct": 0.3, "shipping_days": 2, "available_stock": 40, "inventory_status": "available"},
        }
    )

    calls = {"PROD_A": 0}

    def _dynamic_policy(product_id, **_):
        if product_id == "PROD_A":
            calls["PROD_A"] += 1
            if calls["PROD_A"] == 1:
                return {"product_id": product_id, "decision": "PASS", "reasons": [], "flags": []}
            return {"product_id": product_id, "decision": "EXCLUDE", "reasons": ["Inventory depleted"], "flags": []}
        return {"product_id": product_id, "decision": "PASS", "reasons": [], "flags": []}

    with patch("backend.app.recommendation.decision_module.evaluate_product", side_effect=_dynamic_policy):
        result = module.decide("CUST_0001", top_k=2)

    assert result["status"] == "SUCCESS"
    assert result["fallback_used"] is True
    assert result["decision_method"] == "WEIGHTED_DECISION_FALLBACK"
    assert result["selected_product"]["product_id"] == "PROD_B"
    assert [r["product_id"] for r in result["recommendations"]] == ["PROD_B"]
