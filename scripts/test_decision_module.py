"""
Unit & Integration Tests for Deterministic Decision Module (Day 3 Step 2)
Tests:
1. Normal customer with feasible recommendations.
2. Known reward-ineligible product (PROD_0007) is rejected when reward_context=True.
3. PROD_0002 (known out-of-stock case) can never appear in final recommendations.
4. PROD_0036 (known low-margin case) can never appear in final recommendations.
5. PROD_0044 (known discontinued case) can never appear in final recommendations.
6. Unknown customer handling (raises ValueError).
7. All candidates rejected handling (returns ALL_CANDIDATES_EXCLUDED with 0 recs).
8. Deterministic ordering by recommendation score descending and product_id ascending.
9. Final recommendations are always 100% policy-feasible (policy_decision == 'PASS').
10. Missing operational catalogue record handling (fail-safe to EXCLUDE).
"""

import unittest
from backend.app.recommendation.decision_module import DecisionModule, make_decision


class TestDecisionModule(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.module = DecisionModule()

    def test_01_normal_customer_feasible_recommendations(self):
        """Test standard customer flow produces feasible recommendations."""
        res = self.module.decide("CUST_0001", top_k=5, reward_context=False)
        self.assertEqual(res["customer_id"], "CUST_0001")
        self.assertIn(res["status"], ["SUCCESS", "ALL_CANDIDATES_EXCLUDED"])
        self.assertGreater(res["candidate_count"], 0)

        # Verify all final recommendations are strictly PASS
        for rec in res["recommendations"]:
            self.assertEqual(rec["policy_decision"], "PASS")
            self.assertEqual(len(rec["policy_reasons"]), 0)

    def test_02_reward_ineligible_rejection(self):
        """
        PROD_0007 (65W GaN Compact Wall Charger) is reward_eligible = False.
        Under reward_context=False it passes; under reward_context=True it MUST be EXCLUDED.
        """
        # Under normal context, PROD_0007 should pass
        res_normal = self.module.decide("CUST_0001", top_k=5, reward_context=False)
        normal_rec_ids = [r["product_id"] for r in res_normal["recommendations"]]
        self.assertIn("PROD_0007", normal_rec_ids)

        # Under reward context, PROD_0007 MUST be excluded
        res_reward = self.module.decide("CUST_0001", top_k=5, reward_context=True)
        reward_rec_ids = [r["product_id"] for r in res_reward["recommendations"]]
        self.assertNotIn("PROD_0007", reward_rec_ids)

        # Confirm it appears in excluded_candidates with the exact reason
        excluded_ids = [x["product_id"] for x in res_reward["excluded_candidates"]]
        self.assertIn("PROD_0007", excluded_ids)
        prod_7_item = next(x for x in res_reward["excluded_candidates"] if x["product_id"] == "PROD_0007")
        self.assertIn("Product is not reward eligible.", prod_7_item["policy_reasons"])

    def test_03_out_of_stock_never_recommended(self):
        """PROD_0002 has 0 stock and must NEVER reach final recommendations."""
        mock_candidates = [
            {
                "product_id": "PROD_0002",
                "product_name": "Bluetooth Portable Speaker",
                "category": "Electronics",
                "subcategory": "Audio",
                "brand": "SoundWave",
                "unit_price": 59.99,
                "product_rating": 4.50,
                "product_popularity": 0.99,  # Very high popularity
                "product_status": "active",
            }
        ]
        res = self.module.decide("CUST_0001", top_k=5, injected_candidates=mock_candidates)
        self.assertEqual(len(res["recommendations"]), 0)
        self.assertEqual(res["excluded_count"], 1)
        self.assertIn("Product is out of stock.", res["excluded_candidates"][0]["policy_reasons"])

    def test_04_low_margin_never_recommended(self):
        """PROD_0036 has gross_margin 5% (< 10%) and must NEVER reach final recommendations."""
        mock_candidates = [
            {
                "product_id": "PROD_0036",
                "product_name": "Bamboo Desktop Cable & Device Organizer",
                "category": "Home & Living",
                "subcategory": "Organization",
                "brand": "EcoLiving",
                "unit_price": 19.99,
                "product_rating": 4.80,
                "product_popularity": 0.95,
                "product_status": "active",
            }
        ]
        res = self.module.decide("CUST_0001", top_k=5, injected_candidates=mock_candidates)
        self.assertEqual(len(res["recommendations"]), 0)
        self.assertEqual(res["excluded_count"], 1)
        reasons_str = " ".join(res["excluded_candidates"][0]["policy_reasons"])
        self.assertIn("below the 10% minimum", reasons_str)

    def test_05_discontinued_product_never_recommended(self):
        """PROD_0044 status is 'discontinued' and must NEVER reach final recommendations."""
        mock_candidates = [
            {
                "product_id": "PROD_0044",
                "product_name": "Legacy 30-Pin Charging Cable Vintage",
                "category": "Electronics",
                "subcategory": "Accessories",
                "brand": "VoltTech",
                "unit_price": 14.99,
                "product_rating": 4.10,
                "product_popularity": 0.85,
                "product_status": "discontinued",
            }
        ]
        res = self.module.decide("CUST_0001", top_k=5, injected_candidates=mock_candidates)
        self.assertEqual(len(res["recommendations"]), 0)
        self.assertEqual(res["excluded_count"], 1)
        reasons_str = " ".join(res["excluded_candidates"][0]["policy_reasons"])
        self.assertIn("not active", reasons_str)

    def test_06_unknown_customer_handling(self):
        """Unknown customer ID must raise a descriptive ValueError."""
        with self.assertRaises(ValueError) as ctx:
            self.module.decide("CUST_NON_EXISTENT_9999", top_k=5)
        self.assertIn("Customer not found", str(ctx.exception))

    def test_07_all_candidates_rejected_handling(self):
        """When all candidates fail policy checks, status is ALL_CANDIDATES_EXCLUDED with 0 recs."""
        infeasible_candidates = [
            {
                "product_id": "PROD_0002",  # Stock = 0
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
                "product_id": "PROD_0003",  # Stock = NULL
                "product_name": "Wireless Noise-Cancelling Earbuds",
                "category": "Electronics",
                "subcategory": "Audio",
                "brand": "AudioPro",
                "unit_price": 89.99,
                "product_rating": 4.60,
                "product_popularity": 0.88,
                "product_status": "active",
            },
        ]
        res = self.module.decide("CUST_0001", top_k=5, injected_candidates=infeasible_candidates)
        self.assertEqual(res["status"], "ALL_CANDIDATES_EXCLUDED")
        self.assertEqual(res["feasible_count"], 0)
        self.assertEqual(res["excluded_count"], 2)
        self.assertEqual(len(res["recommendations"]), 0)

    def test_08_deterministic_ordering(self):
        """Feasible candidates must be deterministically sorted descending by score."""
        res = self.module.decide("CUST_0001", top_k=10, reward_context=False)
        recs = res["recommendations"]
        if len(recs) > 1:
            scores = [r["recommendation_score"] for r in recs]
            self.assertEqual(scores, sorted(scores, reverse=True))

    def test_09_final_recommendations_are_always_feasible(self):
        """Absolute safety invariant: every item in recommendations has policy_decision == 'PASS'."""
        for cust_id in ["CUST_0001", "CUST_0170", "CUST_0459"]:
            res = self.module.decide(cust_id, top_k=10)
            for rec in res["recommendations"]:
                self.assertEqual(rec["policy_decision"], "PASS")

    def test_10_missing_operational_catalogue_handling(self):
        """If a product has no operational record, it must fail-safe to EXCLUDE without crashing."""
        ghost_candidate = [
            {
                "product_id": "PROD_GHOST_9999",
                "product_name": "Phantom Gadget",
                "category": "Electronics",
                "subcategory": "Audio",
                "brand": "GhostBrand",
                "unit_price": 100.0,
                "product_rating": 5.0,
                "product_popularity": 1.0,
                "product_status": "active",
            }
        ]
        res = self.module.decide("CUST_0001", top_k=5, injected_candidates=ghost_candidate)
        self.assertEqual(len(res["recommendations"]), 0)
        self.assertEqual(res["excluded_count"], 1)
        self.assertEqual(res["excluded_candidates"][0]["policy_decision"], "EXCLUDE")
        self.assertIn("missing or unverified", res["excluded_candidates"][0]["policy_reasons"][0])


if __name__ == "__main__":
    unittest.main()
