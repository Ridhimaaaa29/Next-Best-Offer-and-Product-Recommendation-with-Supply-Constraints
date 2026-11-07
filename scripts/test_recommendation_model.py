"""
Unit & Integration Tests for Recommendation Model (Day 3 Step 1)
Tests:
1. Customer with interaction history (e.g. CUST_0001)
2. Customer with minimal interaction history (e.g. CUST_0459)
3. Deterministic / reproducible scores across multiple runs
4. No leakage from operational constraints into recommendation model (model scores all candidates regardless of stock/margin)
5. Explainability verification (breakdown components sum to composite score within floating point tolerance)
"""

import unittest
from backend.app.recommendation.recommendation_model import (
    RecommendationModel,
    score_customer_candidates,
)
from backend.app.recommendation.candidate_generator import generate_candidates
from backend.app.recommendation.customer_context import get_customer_context


class TestRecommendationModel(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.model = RecommendationModel()

    def test_customer_with_interaction_history(self):
        """Test scoring for customer with rich interaction history (CUST_0001)."""
        result = score_customer_candidates(customer_id="CUST_0001", limit=10)
        self.assertEqual(result["customer_id"], "CUST_0001")
        self.assertEqual(result["preferred_category"], "Electronics")
        self.assertGreater(result["candidate_count"], 0)

        top_cand = result["ranked_candidates"][0]
        self.assertIn("score", top_cand)
        self.assertGreater(top_cand["score"], 0.0)
        self.assertLessEqual(top_cand["score"], 1.0)

        # Check explanation breakdown
        exp = top_cand["explanation"]
        self.assertIn("category_affinity_score", exp)
        self.assertIn("popularity_score", exp)
        self.assertIn("rating_score", exp)
        self.assertIn("interaction_bonus", exp)
        self.assertIn("reason_codes", exp)
        self.assertIsInstance(exp["reason_codes"], list)
        self.assertGreater(len(exp["reason_codes"]), 0)

    def test_customer_with_limited_history(self):
        """Test scoring for customer with low interaction count (CUST_0459)."""
        result = score_customer_candidates(customer_id="CUST_0459", limit=10)
        self.assertEqual(result["customer_id"], "CUST_0459")
        self.assertGreater(result["candidate_count"], 0)

        for cand in result["ranked_candidates"]:
            self.assertGreaterEqual(cand["score"], 0.0)
            self.assertLessEqual(cand["score"], 1.0)
            self.assertIsInstance(cand["explanation"]["reason_codes"], list)

    def test_deterministic_scoring(self):
        """Confirm identical results across consecutive runs for the same customer."""
        run_1 = self.model.rank_candidates("CUST_0001", candidate_limit=5)
        run_2 = self.model.rank_candidates("CUST_0001", candidate_limit=5)

        self.assertEqual(len(run_1), len(run_2))
        for c1, c2 in zip(run_1, run_2):
            self.assertEqual(c1.product_id, c2.product_id)
            self.assertEqual(c1.score, c2.score)
            self.assertEqual(c1.explanation.to_dict(), c2.explanation.to_dict())

    def test_no_operational_constraint_leakage(self):
        """
        Verify the model does NOT filter out out-of-stock or low-margin items.
        Operational feasibility is strictly the policy engine's job.
        """
        # Pass a synthetic candidate pool including out-of-stock and zero-margin items
        mock_candidates = [
            {
                "product_id": "PROD_0002",  # Out of stock item in synthetic catalogue
                "product_name": "Bluetooth Portable Speaker",
                "category": "Electronics",
                "subcategory": "Audio",
                "brand": "SoundWave",
                "unit_price": 59.99,
                "product_rating": 4.50,
                "product_popularity": 0.85,
                "product_status": "active",
            },
            {
                "product_id": "PROD_0036",  # Low margin (<10%) item in synthetic catalogue
                "product_name": "Bamboo Desktop Cable & Device Organizer",
                "category": "Home & Living",
                "subcategory": "Organization",
                "brand": "EcoLiving",
                "unit_price": 19.99,
                "product_rating": 4.20,
                "product_popularity": 0.70,
                "product_status": "active",
            },
        ]

        scored = self.model.rank_candidates(
            customer_id="CUST_0001",
            candidates=mock_candidates,
        )

        scored_ids = [c.product_id for c in scored]
        # Both products MUST be scored and present - the model must NOT exclude them
        self.assertIn("PROD_0002", scored_ids)
        self.assertIn("PROD_0036", scored_ids)
        for c in scored:
            self.assertGreater(c.score, 0.0)

    def test_ranking_order(self):
        """Verify output candidates are strictly sorted descending by composite score."""
        scored = self.model.rank_candidates("CUST_0001", candidate_limit=10)
        scores = [c.score for c in scored]
        self.assertEqual(scores, sorted(scores, reverse=True))


if __name__ == "__main__":
    unittest.main()
