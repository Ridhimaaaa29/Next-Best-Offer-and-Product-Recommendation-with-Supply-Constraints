"""
Focused Tests for Mandatory Laya Integration
Project: Next-Best-Offer and Product Recommendation with Supply Constraints

Covers:
1. Successful selection: Laya chooses from feasible candidates, passes revalidation, and is placed as Next-Best-Offer.
2. Infeasible selection rejection: Authoritative policy engine rejects Laya's chosen candidate on revalidation.
3. Malformed output: Laya returns invalid structures or unrecognized choices, safely failing without crash.
4. Laya unavailability: Explicit, safe failure/status returned; never silently reported as Laya success.
5. Candidate feasibility invariant: Laya is ONLY passed candidates that passed the deterministic policy engine.
6. API endpoint integration: `/decisions/laya` returns typed responses with explicit failure/success status.
"""

import unittest
from unittest.mock import MagicMock, Mock, patch

from backend.app.decision.laya_adapter import LayaAdapter
from backend.app.recommendation.decision_module import DecisionModule
from backend.app.recommendation.recommendation_model import (
    ScoreExplanation,
    ScoredCandidate,
)


def _make_candidate(product_id: str, score: float = 0.85) -> ScoredCandidate:
    return ScoredCandidate(
        product_id=product_id,
        product_name=f"Product {product_id}",
        category="Electronics",
        subcategory="Audio",
        brand="BrandX",
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

    def _setup_decision_module(self, candidates, laya_adapter):
        recommender = Mock()
        recommender.rank_candidates.return_value = candidates
        module = DecisionModule(recommender=recommender, laya_adapter=laya_adapter)
        module._validate_customer_exists = Mock()
        return module

    # --------------------------------------------------------------------------
    # 1. Successful Selection & Revalidation
    # --------------------------------------------------------------------------
    def test_01_successful_selection_and_revalidation(self):
        """Laya selects a feasible candidate, revalidation passes, returned as #1 offer."""
        candidates = [
            _make_candidate("PROD_A", 0.90),
            _make_candidate("PROD_B", 0.85),
            _make_candidate("PROD_C", 0.70),
        ]

        # Mock Router predicting PROD_B
        mock_router = Mock()
        mock_router.predict.return_value = {
            "answers": {
                "selected_product_id": {"choice": "PROD_B"}
            }
        }

        adapter = LayaAdapter(enabled=True, router=mock_router)
        module = self._setup_decision_module(candidates, adapter)

        # Policy engine passes all products
        with patch(
            "backend.app.recommendation.decision_module.evaluate_product",
            return_value={"product_id": "MOCK", "decision": "PASS", "reasons": [], "flags": []},
        ) as mock_eval:
            result = module.decide("CUST_0001", top_k=3, use_laya=True)

        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["decision_method"], "LAYA")
        self.assertEqual(result["laya_status"], "SUCCESS")
        self.assertIsNotNone(result["laya_selected_product"])
        self.assertEqual(result["laya_selected_product"]["product_id"], "PROD_B")

        # Laya's selected candidate is placed at position 1 (Next-Best-Offer)
        recs = result["recommendations"]
        self.assertEqual(len(recs), 3)
        self.assertEqual(recs[0]["product_id"], "PROD_B")
        self.assertEqual(recs[1]["product_id"], "PROD_A")
        self.assertEqual(recs[2]["product_id"], "PROD_C")

        # Verify revalidation was called on PROD_B
        called_products = [call.kwargs.get("product_id") for call in mock_eval.call_args_list]
        self.assertIn("PROD_B", called_products)

    # --------------------------------------------------------------------------
    # 2. Infeasible Selection Rejection (Authoritative Policy Revalidation)
    # --------------------------------------------------------------------------
    def test_02_infeasible_selection_rejected_by_policy_revalidation(self):
        """If Laya's choice fails authoritative revalidation, it must be rejected."""
        candidates = [
            _make_candidate("PROD_FEASIBLE_1", 0.90),
            _make_candidate("PROD_FEASIBLE_2", 0.85),
        ]

        # Router selects PROD_FEASIBLE_1
        mock_router = Mock()
        mock_router.predict.return_value = {
            "answers": {
                "selected_product_id": {"choice": "PROD_FEASIBLE_1"}
            }
        }
        adapter = LayaAdapter(enabled=True, router=mock_router)
        module = self._setup_decision_module(candidates, adapter)

        # Simulate policy passing during initial candidate evaluation,
        # but failing during revalidation (e.g. stock depleted or rule trigger)
        call_count = 0

        def dynamic_policy(product_id, **kwargs):
            nonlocal call_count
            call_count += 1
            # Initial evaluations (call 1 and 2) pass
            if call_count <= 2:
                return {"product_id": product_id, "decision": "PASS", "reasons": [], "flags": []}
            # Revalidation evaluation fails!
            return {
                "product_id": product_id,
                "decision": "EXCLUDE",
                "reasons": ["Product is out of stock on revalidation."],
                "flags": [],
            }

        with patch(
            "backend.app.recommendation.decision_module.evaluate_product",
            side_effect=dynamic_policy,
        ):
            result = module.decide("CUST_0001", top_k=2, use_laya=True)

        self.assertEqual(result["status"], "LAYA_SELECTION_INFEASIBLE")
        self.assertEqual(result["decision_method"], "POLICY_REJECTED")
        self.assertEqual(result["laya_status"], "REVALIDATION_FAILED")
        self.assertIn("failed authoritative policy revalidation", result["laya_fallback_reason"])
        self.assertEqual(result["recommendations"], [])
        self.assertIsNone(result["laya_selected_product"])

    # --------------------------------------------------------------------------
    # 3. Malformed Output Detection
    # --------------------------------------------------------------------------
    def test_03_malformed_output_non_dict(self):
        """Laya returning non-dict is safely caught and returns LAYA_FAILED."""
        candidates = [_make_candidate("PROD_A", 0.90)]
        mock_router = Mock()
        mock_router.predict.return_value = "invalid non-dict output"

        adapter = LayaAdapter(enabled=True, router=mock_router)
        module = self._setup_decision_module(candidates, adapter)

        with patch(
            "backend.app.recommendation.decision_module.evaluate_product",
            return_value={"product_id": "PROD_A", "decision": "PASS", "reasons": [], "flags": []},
        ):
            result = module.decide("CUST_0001", top_k=1, use_laya=True)

        self.assertEqual(result["status"], "LAYA_FAILED")
        self.assertEqual(result["decision_method"], "FAILED")
        self.assertEqual(result["laya_status"], "MALFORMED_OUTPUT")
        self.assertEqual(result["recommendations"], [])
        self.assertIn("malformed", result["laya_fallback_reason"].lower())

    def test_04_malformed_output_missing_choice(self):
        """Laya returning missing or invalid answers structure fails safely."""
        candidates = [_make_candidate("PROD_A", 0.90)]
        mock_router = Mock()
        mock_router.predict.return_value = {"answers": {}}  # missing selected_product_id

        adapter = LayaAdapter(enabled=True, router=mock_router)
        module = self._setup_decision_module(candidates, adapter)

        with patch(
            "backend.app.recommendation.decision_module.evaluate_product",
            return_value={"product_id": "PROD_A", "decision": "PASS", "reasons": [], "flags": []},
        ):
            result = module.decide("CUST_0001", top_k=1, use_laya=True)

        self.assertEqual(result["status"], "LAYA_FAILED")
        self.assertEqual(result["laya_status"], "MALFORMED_OUTPUT")
        self.assertEqual(result["recommendations"], [])

    def test_05_unrecognized_candidate_choice(self):
        """Laya returning a product ID not in feasible candidates fails safely."""
        candidates = [_make_candidate("PROD_A", 0.90)]
        mock_router = Mock()
        mock_router.predict.return_value = {
            "answers": {"selected_product_id": {"choice": "PROD_HALLUCINATED_999"}}
        }

        adapter = LayaAdapter(enabled=True, router=mock_router)
        module = self._setup_decision_module(candidates, adapter)

        with patch(
            "backend.app.recommendation.decision_module.evaluate_product",
            return_value={"product_id": "PROD_A", "decision": "PASS", "reasons": [], "flags": []},
        ):
            result = module.decide("CUST_0001", top_k=1, use_laya=True)

        self.assertEqual(result["status"], "LAYA_UNAVAILABLE")
        self.assertEqual(result["laya_status"], "UNAVAILABLE")
        self.assertIn("PROD_HALLUCINATED_999", result["laya_fallback_reason"])
        self.assertEqual(result["recommendations"], [])

    # --------------------------------------------------------------------------
    # 4. Laya Unavailability Handling
    # --------------------------------------------------------------------------
    def test_06_laya_disabled_in_config(self):
        """When Laya is disabled, decide() reports explicit LAYA_UNAVAILABLE status."""
        candidates = [_make_candidate("PROD_A", 0.90)]
        adapter = LayaAdapter(enabled=False)
        module = self._setup_decision_module(candidates, adapter)

        with patch(
            "backend.app.recommendation.decision_module.evaluate_product",
            return_value={"product_id": "PROD_A", "decision": "PASS", "reasons": [], "flags": []},
        ):
            result = module.decide("CUST_0001", top_k=1, use_laya=True)

        self.assertEqual(result["status"], "LAYA_UNAVAILABLE")
        self.assertEqual(result["decision_method"], "FAILED")
        self.assertEqual(result["laya_status"], "UNAVAILABLE")
        self.assertEqual(result["recommendations"], [])
        self.assertIn("disabled", result["laya_fallback_reason"].lower())

    def test_07_laya_router_runtime_error(self):
        """When Laya Router raises RuntimeError during prediction, fails safely."""
        candidates = [_make_candidate("PROD_A", 0.90)]
        mock_router = Mock()
        mock_router.predict.side_effect = RuntimeError("Checkpoint weights corrupted or missing")

        adapter = LayaAdapter(enabled=True, router=mock_router)
        module = self._setup_decision_module(candidates, adapter)

        with patch(
            "backend.app.recommendation.decision_module.evaluate_product",
            return_value={"product_id": "PROD_A", "decision": "PASS", "reasons": [], "flags": []},
        ):
            result = module.decide("CUST_0001", top_k=1, use_laya=True)

        self.assertEqual(result["status"], "LAYA_UNAVAILABLE")
        self.assertEqual(result["laya_status"], "UNAVAILABLE")
        self.assertIn("Checkpoint weights corrupted", result["laya_fallback_reason"])
        self.assertEqual(result["recommendations"], [])

    # --------------------------------------------------------------------------
    # 5. Policy Feasibility Invariant
    # --------------------------------------------------------------------------
    def test_08_laya_only_receives_policy_feasible_candidates(self):
        """Verify Laya is never invoked with candidates that failed policy checks."""
        candidates = [
            _make_candidate("PROD_PASS_1", 0.90),
            _make_candidate("PROD_FAIL_STOCK", 0.85),
            _make_candidate("PROD_PASS_2", 0.80),
        ]

        received_options = []

        def mock_predict(prompt, questions):
            nonlocal received_options
            options = questions["selected_product_id"]["criteria"]
            received_options = list(options.keys())
            return {"answers": {"selected_product_id": {"choice": "PROD_PASS_1"}}}

        mock_router = Mock()
        mock_router.predict.side_effect = mock_predict
        adapter = LayaAdapter(enabled=True, router=mock_router)
        module = self._setup_decision_module(candidates, adapter)

        def mock_policy(product_id, **_):
            if product_id == "PROD_FAIL_STOCK":
                return {"product_id": product_id, "decision": "EXCLUDE", "reasons": ["Out of stock"], "flags": []}
            return {"product_id": product_id, "decision": "PASS", "reasons": [], "flags": []}

        with patch(
            "backend.app.recommendation.decision_module.evaluate_product",
            side_effect=mock_policy,
        ):
            result = module.decide("CUST_0001", top_k=2, use_laya=True)

        self.assertEqual(result["status"], "SUCCESS")
        # Ensure Laya was passed ONLY the 2 passing candidates
        self.assertIn("PROD_PASS_1", received_options)
        self.assertIn("PROD_PASS_2", received_options)
        self.assertNotIn("PROD_FAIL_STOCK", received_options)

    # --------------------------------------------------------------------------
    # 6. Configuration Precedence for LAYA_CACHE_DIR
    # --------------------------------------------------------------------------
    def test_09_cache_dir_precedence(self):
        """Verify LAYA_CACHE_DIR environment variable overrides default settings, and constructor overrides env."""
        import os
        from pathlib import Path

        # 1. Environment variable override
        with patch.dict(os.environ, {"LAYA_CACHE_DIR": "C:\\custom\\env\\laya_cache"}):
            adapter = LayaAdapter()
            self.assertEqual(adapter._cache_dir, Path("C:\\custom\\env\\laya_cache"))

        # 2. Constructor parameter override over environment variable
        with patch.dict(os.environ, {"LAYA_CACHE_DIR": "C:\\custom\\env\\laya_cache"}):
            adapter_param = LayaAdapter(cache_dir="C:\\param\\laya_cache")
            self.assertEqual(adapter_param._cache_dir, Path("C:\\param\\laya_cache"))

    # --------------------------------------------------------------------------
    # 7. Lightweight Status Check (No Model Download/Initialization)
    # --------------------------------------------------------------------------
    def test_10_lightweight_status_check(self):
        """Verify /laya/status is lightweight and does NOT initialize or download Laya model."""
        adapter = LayaAdapter(enabled=True)
        # Calling status_info must not set _cached_router or load model
        status_info = adapter.status_info()

        self.assertTrue(status_info["configured"])
        self.assertTrue(status_info["enabled"])
        self.assertFalse(status_info["loaded"])
        self.assertIsNone(LayaAdapter._cached_router)

    # --------------------------------------------------------------------------
    # 8. Mandatory Laya Cannot Be Bypassed with use_laya=False
    # --------------------------------------------------------------------------
    def test_11_use_laya_false_is_forbidden(self):
        """Primary recommendation pipeline must reject callers trying to set use_laya=False."""
        candidates = [_make_candidate("PROD_A", 0.90)]
        module = self._setup_decision_module(candidates, LayaAdapter())

        with self.assertRaises(ValueError) as ctx:
            module.decide("CUST_0001", use_laya=False)

        self.assertIn("mandatory", str(ctx.exception).lower())
        self.assertIn("cannot be bypassed", str(ctx.exception).lower())

    # --------------------------------------------------------------------------
    # 9. API HTTP Status Code Mapping for Laya Decision Failures
    # --------------------------------------------------------------------------
    def test_12_recommendations_endpoint_maps_failures_to_http_codes(self):
        """Verify non-success HTTP status codes (503/502) are set for Laya failures with structured body."""
        from fastapi import Response
        from backend.app.api.routes.recommendations import generate_recommendations
        from backend.app.api.schemas.recommendation import RecommendationRequest, RecommendationResponse

        req = RecommendationRequest(customer_id="CUST_0001", top_k=5)
        mock_db = MagicMock()

        # 1. Test LAYA_UNAVAILABLE maps to HTTP 503 Service Unavailable
        resp_503 = Response()
        with patch("backend.app.api.routes.recommendations.DecisionModule") as mock_dm, \
             patch("backend.app.api.routes.recommendations.AuditService"):
            mock_dm.return_value.decide.return_value = {
                "status": "LAYA_UNAVAILABLE",
                "customer_id": "CUST_0001",
                "candidate_count": 2,
                "feasible_count": 2,
                "excluded_count": 0,
                "top_k_requested": 5,
                "recommendations": [],
                "feasible_candidates": [{"product_id": "PROD_A", "policy_decision": "PASS"}],
                "excluded_candidates": [],
                "all_evaluated_candidates": [],
                "decision_method": "FAILED",
                "laya_status": "UNAVAILABLE",
                "laya_fallback_reason": "Laya package is not installed",
            }
            result_503 = generate_recommendations(req=req, response=resp_503, db=mock_db)

            self.assertEqual(resp_503.status_code, 503)
            self.assertIsInstance(result_503, RecommendationResponse)
            self.assertEqual(result_503.status, "LAYA_UNAVAILABLE")
            self.assertEqual(result_503.decision_method, "FAILED")
            self.assertEqual(result_503.recommendations, [])

        # 2. Test LAYA_FAILED maps to HTTP 502 Bad Gateway
        resp_502 = Response()
        with patch("backend.app.api.routes.recommendations.DecisionModule") as mock_dm, \
             patch("backend.app.api.routes.recommendations.AuditService"):
            mock_dm.return_value.decide.return_value = {
                "status": "LAYA_FAILED",
                "customer_id": "CUST_0001",
                "candidate_count": 2,
                "feasible_count": 2,
                "excluded_count": 0,
                "top_k_requested": 5,
                "recommendations": [],
                "feasible_candidates": [{"product_id": "PROD_A", "policy_decision": "PASS"}],
                "excluded_candidates": [],
                "all_evaluated_candidates": [],
                "decision_method": "FAILED",
                "laya_status": "MALFORMED_OUTPUT",
                "laya_fallback_reason": "Malformed output",
            }
            result_502 = generate_recommendations(req=req, response=resp_502, db=mock_db)

            self.assertEqual(resp_502.status_code, 502)
            self.assertIsInstance(result_502, RecommendationResponse)
            self.assertEqual(result_502.status, "LAYA_FAILED")

    # --------------------------------------------------------------------------
    # 10. Decisions Laya Endpoint Returns Actual Feasible Candidate List
    # --------------------------------------------------------------------------
    def test_13_decisions_laya_returns_feasible_list(self):
        """Verify /decisions/laya returns the actual feasible candidate list without undefined variables."""
        from backend.app.api.routes.decisions import laya_decision, LayaDecisionRequest, LayaDecisionResponse

        req = LayaDecisionRequest(customer_id="CUST_0001", top_k=5)
        mock_feasible = [
            {"product_id": "PROD_FEASIBLE_1", "policy_decision": "PASS", "unit_price": 50.0},
            {"product_id": "PROD_FEASIBLE_2", "policy_decision": "PASS", "unit_price": 75.0},
        ]

        with patch("backend.app.api.routes.decisions.DecisionModule") as mock_dm:
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
                "all_evaluated_candidates": mock_feasible + [{"product_id": "PROD_EX", "policy_decision": "EXCLUDE"}],
                "decision_method": "LAYA",
                "laya_status": "SUCCESS",
                "laya_selected_product": mock_feasible[0],
                "laya_revalidation": {"decision": "PASS"},
                "laya_fallback_reason": None,
            }
            result = laya_decision(request=req)

            self.assertIsInstance(result, LayaDecisionResponse)
            self.assertEqual(result.status, "SUCCESS")
            self.assertEqual(len(result.feasible_candidates), 2)
            self.assertEqual(result.feasible_candidates[0]["product_id"], "PROD_FEASIBLE_1")
            self.assertEqual(result.selected_product["product_id"], "PROD_FEASIBLE_1")


if __name__ == "__main__":
    unittest.main()
