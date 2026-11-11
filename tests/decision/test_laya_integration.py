"""
Tests for lightweight Laya integration, candidate shortlist capping,
timeout/error fallback to WeightedDecisionEngine, policy revalidation, and API status.
"""

import os
import time
import unittest
from unittest.mock import MagicMock, Mock, patch

from backend.app.decision.laya_adapter import LayaAdapter
from backend.app.decision.weighted_engine import WeightedDecisionEngine
from backend.app.recommendation.decision_module import DecisionModule
from backend.app.recommendation.recommendation_model import (
    ScoreExplanation,
    ScoredCandidate,
)


def _make_candidate(
    product_id: str,
    score: float = 0.85,
    subcategory: str = "Audio",
    brand: str = "BrandX",
) -> ScoredCandidate:
    return ScoredCandidate(
        product_id=product_id,
        product_name=f"Product {product_id}",
        category="Electronics",
        subcategory=subcategory,
        brand=brand,
        unit_price=99.99,
        product_rating=4.5,
        product_popularity=0.8,
        product_status="active",
        score=score,
        explanation=ScoreExplanation(
            category_affinity_score=0.8,
            popularity_score=0.8,
            rating_score=0.9,
            interaction_bonus=0.1,
            composite_score=score,
            reason_codes=["High popularity"],
        ),
    )


class TestLayaIntegration(unittest.TestCase):
    def _setup_decision_module(self, candidates, laya_adapter, op_map=None):
        recommender = Mock()
        recommender.rank_candidates.return_value = candidates
        module = DecisionModule(
            recommender=recommender,
            laya_adapter=laya_adapter,
            decision_engine=WeightedDecisionEngine(enabled=True),
        )
        module._validate_customer_exists = Mock()
        module._load_operational_map = Mock(return_value=op_map or {})
        return module

    def test_01_laya_primary_selection_and_revalidation(self):
        candidates = [
            _make_candidate("PROD_A", 0.90, subcategory="Audio", brand="Brand1"),
            _make_candidate("PROD_B", 0.85, subcategory="Wearables", brand="Brand2"),
        ]
        mock_router = Mock()
        mock_router.predict.return_value = {
            "answers": {"selected_product_id": {"choice": "PROD_B", "answer_confidence": 0.92}}
        }
        adapter = LayaAdapter(enabled=True, router=mock_router)
        module = self._setup_decision_module(candidates, adapter)

        with patch(
            "backend.app.recommendation.decision_module.evaluate_product",
            return_value={"product_id": "MOCK", "decision": "PASS", "reasons": [], "flags": []},
        ) as mock_eval:
            result = module.decide("CUST_0001", top_k=2, use_laya=True)

        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["decision_method"], "LAYA")
        self.assertEqual(result["laya_status"], "SUCCESS")
        self.assertFalse(result["fallback_used"])
        self.assertEqual(result["laya_selected_product"]["product_id"], "PROD_B")
        self.assertEqual([r["product_id"] for r in result["recommendations"]], ["PROD_B", "PROD_A"])
        called_products = [call.kwargs.get("product_id") for call in mock_eval.call_args_list]
        self.assertIn("PROD_B", called_products)

    def test_02_infeasible_laya_selection_triggers_weighted_fallback(self):
        candidates = [
            _make_candidate("PROD_1", 0.90),
            _make_candidate("PROD_2", 0.85),
        ]
        mock_router = Mock()
        mock_router.predict.return_value = {"answers": {"selected_product_id": {"choice": "PROD_1"}}}
        adapter = LayaAdapter(enabled=True, router=mock_router)
        module = self._setup_decision_module(candidates, adapter)

        call_count = 0

        def dynamic_policy(product_id, **_):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return {"product_id": product_id, "decision": "PASS", "reasons": [], "flags": []}
            if product_id == "PROD_1":
                return {"product_id": product_id, "decision": "EXCLUDE", "reasons": ["Out of stock on revalidation"], "flags": []}
            return {"product_id": product_id, "decision": "PASS", "reasons": [], "flags": []}

        with patch(
            "backend.app.recommendation.decision_module.evaluate_product",
            side_effect=dynamic_policy,
        ):
            result = module.decide("CUST_0001", top_k=2)

        self.assertEqual(result["status"], "SUCCESS")
        self.assertTrue(result["fallback_used"])
        self.assertEqual(result["decision_method"], "WEIGHTED_DECISION_FALLBACK")
        self.assertEqual(result["selected_product"]["product_id"], "PROD_2")
        self.assertIn("revalidation", result["fallback_reason"].lower())

    def test_03_disabled_malformed_or_unrecognized_laya_falls_back(self):
        candidates = [_make_candidate("PROD_LOW", 0.60), _make_candidate("PROD_HIGH", 0.95)]

        # Disabled
        disabled_mod = self._setup_decision_module(candidates, LayaAdapter(enabled=False))
        with patch(
            "backend.app.recommendation.decision_module.evaluate_product",
            return_value={"product_id": "MOCK", "decision": "PASS", "reasons": [], "flags": []},
        ):
            res_dis = disabled_mod.decide("CUST_0001", top_k=2)
        self.assertTrue(res_dis["fallback_used"])
        self.assertEqual(res_dis["decision_method"], "WEIGHTED_DECISION_FALLBACK")
        self.assertIn("disabled", res_dis["fallback_reason"].lower())

        # Unrecognized product ID
        bad_router = Mock()
        bad_router.predict.return_value = {"answers": {"selected_product_id": {"choice": "PROD_HALLUCINATED"}}}
        bad_mod = self._setup_decision_module(candidates, LayaAdapter(enabled=True, router=bad_router))
        with patch(
            "backend.app.recommendation.decision_module.evaluate_product",
            return_value={"product_id": "MOCK", "decision": "PASS", "reasons": [], "flags": []},
        ):
            res_bad = bad_mod.decide("CUST_0001", top_k=2)
        self.assertTrue(res_bad["fallback_used"])
        self.assertIn("PROD_HALLUCINATED", res_bad["fallback_reason"])

        # Malformed non-dict
        mal_router = Mock()
        mal_router.predict.return_value = "malformed_string"
        mal_mod = self._setup_decision_module(candidates, LayaAdapter(enabled=True, router=mal_router))
        with patch(
            "backend.app.recommendation.decision_module.evaluate_product",
            return_value={"product_id": "MOCK", "decision": "PASS", "reasons": [], "flags": []},
        ):
            res_mal = mal_mod.decide("CUST_0001", top_k=2)
        self.assertTrue(res_mal["fallback_used"])
        self.assertIn("malformed", res_mal["fallback_reason"].lower())

    def test_04_timeout_handling_falls_back_cleanly(self):
        def slow_predict(*_a, **_kw):
            time.sleep(0.25)
            return {"answers": {"selected_product_id": {"choice": "PROD_A"}}}

        slow_router = Mock()
        slow_router.predict.side_effect = slow_predict
        adapter = LayaAdapter(enabled=True, timeout_seconds=0.05)
        adapter._get_router = lambda: slow_router

        with self.assertRaises(RuntimeError) as ctx:
            adapter.choose([{"product_id": "PROD_A", "product_name": "Item A", "recommendation_score": 0.9}])
        self.assertIn("timed out", str(ctx.exception).lower())

    def test_05_shortlist_capped_and_only_feasible_candidates_sent(self):
        candidates = [_make_candidate(f"PROD_{i}", 0.95 - i * 0.05) for i in range(8)]
        candidates.insert(1, _make_candidate("PROD_EXCL", 0.99))

        seen_criteria = []

        def mock_predict(prompt, questions):
            nonlocal seen_criteria
            seen_criteria = list(questions["selected_product_id"]["criteria"].keys())
            return {"answers": {"selected_product_id": {"choice": seen_criteria[0]}}}

        mock_router = Mock()
        mock_router.predict.side_effect = mock_predict
        adapter = LayaAdapter(enabled=True, router=mock_router, max_candidates=3)
        module = self._setup_decision_module(candidates, adapter)

        def mock_policy(product_id, **_):
            if product_id == "PROD_EXCL":
                return {"product_id": product_id, "decision": "EXCLUDE", "reasons": ["Out of stock"], "flags": []}
            return {"product_id": product_id, "decision": "PASS", "reasons": [], "flags": []}

        with patch("backend.app.recommendation.decision_module.evaluate_product", side_effect=mock_policy):
            result = module.decide("CUST_0001", top_k=5)

        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(len(seen_criteria), 3)
        self.assertNotIn("PROD_EXCL", seen_criteria)

    def test_06_lightweight_status_check_does_not_load_model_and_routes_work(self):
        from backend.app.api.routes.decisions import (
            DecisionOptimizationRequest,
            DecisionOptimizationResponse,
            decision_engine_status,
            legacy_decision_status,
            laya_decision,
        )

        LayaAdapter.reset_shared_instance()
        with patch.dict(os.environ, {"LAYA_ENABLED": "true"}):
            status_payload = decision_engine_status()
            alias_payload = legacy_decision_status()

        self.assertEqual(status_payload["engine"], "laya")
        self.assertTrue(status_payload["configured"])
        self.assertFalse(status_payload["loaded"])
        self.assertTrue(status_payload["vega_disabled"])
        self.assertFalse(status_payload["preload"])
        self.assertEqual(alias_payload, status_payload)
        self.assertIsNone(LayaAdapter._cached_router)

        req = DecisionOptimizationRequest(customer_id="CUST_0001", top_k=5)
        mock_feasible = [
            {"product_id": "PROD_FEASIBLE_1", "policy_decision": "PASS", "unit_price": 50.0},
            {"product_id": "PROD_FEASIBLE_2", "policy_decision": "PASS", "unit_price": 75.0},
        ]
        mock_db = MagicMock()
        with (
            patch("backend.app.api.routes.decisions.DecisionModule") as mock_dm,
            patch("backend.app.api.routes.decisions.AuditService") as mock_audit,
        ):
            mock_audit.return_value.log_decision_audit.return_value = "audit_laya_1"
            mock_dm.return_value.decide.return_value = {
                "status": "SUCCESS",
                "customer_id": "CUST_0001",
                "candidate_count": 3,
                "feasible_count": 2,
                "excluded_count": 1,
                "top_k_requested": 5,
                "recommendations": [mock_feasible[0]],
                "feasible_candidates": mock_feasible,
                "excluded_candidates": [],
                "all_evaluated_candidates": mock_feasible,
                "decision_method": "LAYA",
                "laya_status": "SUCCESS",
                "selected_product": mock_feasible[0],
                "decision_weights": {"relevance": 0.45, "margin": 0.25, "diversity": 0.15, "friction": 0.15},
                "objective_scores": {},
                "final_ranking": [],
                "decision_explanation": "Laya selected PROD_FEASIBLE_1.",
                "fallback_used": False,
                "fallback_reason": None,
                "final_validation": {"decision": "PASS"},
            }
            result = laya_decision(request=req, db=mock_db)

        self.assertIsInstance(result, DecisionOptimizationResponse)
        self.assertEqual(result.decision_id, "audit_laya_1")
        self.assertEqual(result.decision_method, "LAYA")
        self.assertEqual(result.selected_product["product_id"], "PROD_FEASIBLE_1")
        self.assertEqual(len(result.feasible_candidates), 2)


if __name__ == "__main__":
    unittest.main()
