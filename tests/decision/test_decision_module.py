"""
Unit & Integration Tests for Supply-Constrained Decision Module (isolated from live Neon DB).
Tests:
1. Normal customer with feasible recommendations.
2. Reward-ineligible product (PROD_0007) rejected when reward_context=True.
3. Out-of-stock (PROD_0002) never reaches final recommendations.
4. Low-margin (<10%) (PROD_0036) never reaches final recommendations.
5. Discontinued (PROD_0044) never reaches final recommendations.
6. Unknown customer handling (raises ValueError).
7. All candidates rejected handling (returns ALL_CANDIDATES_EXCLUDED with 0 recs).
8. Deterministic ordering when top offer selected consistently.
9. Final recommendations are always 100% policy-feasible (policy_decision == 'PASS').
10. Missing operational catalogue record handling (fail-safe to EXCLUDE).
11-15. Exact top-k, equal score tie-break, no-candidates, excluded payload, high-scoring excluded isolation.
"""

from datetime import datetime, timezone
import unittest
from unittest.mock import MagicMock, Mock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.models import Base, Customer, OperationalCatalogue, Product
from backend.app.decision.laya_adapter import LayaAdapter
from backend.app.decision.weighted_engine import WeightedDecisionEngine
from backend.app.recommendation import candidate_generator, policy_engine
from backend.app.recommendation.decision_module import DecisionModule
from backend.app.recommendation.recommendation_model import (
    ScoreExplanation,
    ScoredCandidate,
)


def _scored_candidate(product_id, score, product_status="active"):
    return ScoredCandidate(
        product_id=product_id,
        product_name=f"Product {product_id}",
        category="Electronics",
        subcategory="Accessories",
        brand="TestBrand",
        unit_price=10.0,
        product_rating=4.0,
        product_popularity=0.8,
        product_status=product_status,
        score=score,
        explanation=ScoreExplanation(
            category_affinity_score=0.8,
            popularity_score=0.8,
            rating_score=0.8,
            interaction_bonus=0.2,
            composite_score=score,
            reason_codes=["test score"],
        ),
    )


def _decision_module_with_candidates(candidates):
    recommender = Mock()
    recommender.rank_candidates.return_value = candidates
    # Lightweight deterministic Laya stub picking first feasible candidate
    laya_stub = LayaAdapter(
        enabled=True,
        custom_selector=lambda items: {"product_id": items[0]["product_id"]},
    )
    module = DecisionModule(
        recommender=recommender,
        laya_adapter=laya_stub,
        decision_engine=WeightedDecisionEngine(enabled=True),
    )
    module._validate_customer_exists = Mock()
    module._load_operational_map = Mock(return_value={})
    return module


def _passing_policy(product_id, **_):
    return {
        "product_id": product_id,
        "decision": "PASS",
        "reasons": [],
        "flags": [],
    }


def _excluded_policy(product_id, reason="Product is out of stock."):
    return {
        "product_id": product_id,
        "decision": "EXCLUDE",
        "reasons": [reason],
        "flags": [],
    }


def _seed_isolated_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionCls = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionCls()
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)

    for cid in ("CUST_0001", "CUST_0170", "CUST_0459"):
        db.add(
            Customer(
                customer_id=cid,
                customer_segment="High-Value Enthusiast",
                age_group="25-34",
                location="Austin, TX",
                membership_tier="Gold",
                reward_points=1200,
                preferred_category="Electronics",
                average_order_value=140.0,
                total_orders=5,
                total_spend=700.0,
                last_purchase_date=now,
                customer_status="active",
            )
        )

    catalogue = {
        "PROD_0001": ("Wireless Headphones", "Electronics", "Audio", "AudioMax", 149.99, 4.8, 0.92, "active", 30, "available", 0.45, 2, True, True, "verified_fresh", 0.25),
        "PROD_0002": ("Bluetooth Portable Speaker", "Electronics", "Audio", "SoundWave", 59.99, 4.5, 0.85, "active", 0, "out_of_stock", 0.40, 3, True, True, "verified_fresh", 0.15),
        "PROD_0003": ("Wireless Noise-Cancelling Earbuds", "Electronics", "Audio", "AudioPro", 89.99, 4.6, 0.88, "active", None, "unknown", 0.42, 3, True, True, "verified_fresh", 0.15),
        "PROD_0007": ("65W GaN Compact Wall Charger", "Electronics", "Accessories", "VoltTech", 39.99, 4.7, 0.90, "active", 40, "available", 0.50, 2, False, True, "verified_fresh", 0.20),
        "PROD_0009": ("Smart Home Plug", "Electronics", "Smart Home", "HomeLink", 29.99, 4.4, 0.78, "active", 25, "available", 0.35, 3, True, True, "verified_fresh", 0.20),
        "PROD_0036": ("Bamboo Desktop Cable Organizer", "Home & Living", "Organization", "EcoLiving", 19.99, 4.2, 0.70, "active", 20, "available", 0.05, 4, True, True, "verified_fresh", 0.10),
        "PROD_0044": ("Legacy 30-Pin Charging Cable", "Electronics", "Accessories", "VoltTech", 14.99, 4.1, 0.65, "discontinued", 15, "available", 0.30, 5, True, True, "verified_fresh", 0.10),
    }

    for pid, vals in catalogue.items():
        (name, cat, sub, brand, price, rating, pop, pstatus, stock, inv_st, margin, ship, rew, promo, fresh, max_disc) = vals
        db.add(
            Product(
                product_id=pid,
                product_name=name,
                category=cat,
                subcategory=sub,
                brand=brand,
                unit_price=price,
                unit_cost=price * (1 - margin),
                product_rating=rating,
                product_popularity=pop,
                product_status=pstatus,
            )
        )
        db.add(
            OperationalCatalogue(
                product_id=pid,
                available_stock=stock,
                inventory_status=inv_st,
                reorder_point=10,
                unit_price=price,
                unit_cost=price * (1 - margin),
                gross_margin_pct=margin,
                supplier_id="SUP_01",
                supplier_lead_days=ship,
                warehouse_id="WH_01",
                fulfilment_class="standard",
                shipping_days=ship,
                reward_eligible=rew,
                max_discount_pct=max_disc,
                promotion_eligible=promo,
                data_source="unit_test",
                last_updated_at=now,
                data_freshness_status=fresh,
            )
        )
    db.commit()
    return engine, SessionCls, catalogue


class TestDecisionModule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine, cls.SessionCls, cls.catalogue = _seed_isolated_db()
        cls.session = cls.SessionCls()

        def _fake_psycopg_connect(_url):
            conn = MagicMock()
            cur = conn.cursor.return_value.__enter__.return_value
            state = {"mode": None, "cust": None, "pid": None}

            def _exec(sql, params=()):
                low = sql.lower()
                if "from customers" in low:
                    state["mode"] = "cust"
                    state["cust"] = params[0] if params else None
                elif "operational_catalogue" in low:
                    state["mode"] = "policy"
                    state["pid"] = params[0] if params else None
                else:
                    state["mode"] = "cands"

            def _fetchone():
                if state["mode"] == "cust":
                    return (
                        ("Electronics",)
                        if state["cust"] in ("CUST_0001", "CUST_0170", "CUST_0459")
                        else None
                    )
                if state["mode"] == "policy":
                    vals = cls.catalogue.get(state["pid"])
                    if not vals:
                        return None
                    return (
                        state["pid"],
                        vals[7],
                        vals[8],
                        vals[9],
                        vals[10],
                        vals[11],
                        vals[12],
                        vals[13],
                        vals[14],
                        vals[15],
                    )
                return None

            def _fetchall():
                rows = [
                    (pid, vals[0], vals[1], vals[2], vals[3], vals[4], vals[5], vals[6], vals[7])
                    for pid, vals in cls.catalogue.items()
                    if vals[1] == "Electronics" and vals[7] == "active"
                ]
                rows.sort(key=lambda r: (-r[7], -r[6], r[0]))
                return rows

            cur.execute.side_effect = _exec
            cur.fetchone.side_effect = _fetchone
            cur.fetchall.side_effect = _fetchall
            conn.__enter__.return_value = conn
            return conn

        cls._patches = [
            patch("psycopg.connect", side_effect=_fake_psycopg_connect),
        ]
        for p in cls._patches:
            p.start()

        cls.laya_stub = LayaAdapter(
            enabled=True,
            custom_selector=lambda items: {"product_id": max(items, key=lambda x: x["recommendation_score"])["product_id"]},
        )
        cls.module = DecisionModule(
            session=cls.session,
            laya_adapter=cls.laya_stub,
            decision_engine=WeightedDecisionEngine(enabled=True),
        )

    @classmethod
    def tearDownClass(cls):
        for p in cls._patches:
            p.stop()
        cls.session.close()
        cls.engine.dispose()

    def test_01_normal_customer_feasible_recommendations(self):
        res = self.module.decide("CUST_0001", top_k=5, reward_context=False)
        self.assertEqual(res["customer_id"], "CUST_0001")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertGreater(res["candidate_count"], 0)
        for rec in res["recommendations"]:
            self.assertEqual(rec["policy_decision"], "PASS")
            self.assertEqual(len(rec["policy_reasons"]), 0)

    def test_02_reward_ineligible_rejection(self):
        res_normal = self.module.decide("CUST_0001", top_k=5, reward_context=False)
        self.assertIn("PROD_0007", [r["product_id"] for r in res_normal["recommendations"]])

        res_reward = self.module.decide("CUST_0001", top_k=5, reward_context=True)
        self.assertNotIn("PROD_0007", [r["product_id"] for r in res_reward["recommendations"]])
        prod_7_item = next(x for x in res_reward["excluded_candidates"] if x["product_id"] == "PROD_0007")
        self.assertIn("Product is not reward eligible.", prod_7_item["policy_reasons"])

    def test_03_out_of_stock_never_recommended(self):
        mock_candidates = [
            {
                "product_id": "PROD_0002",
                "product_name": "Bluetooth Portable Speaker",
                "category": "Electronics",
                "subcategory": "Audio",
                "brand": "SoundWave",
                "unit_price": 59.99,
                "product_rating": 4.50,
                "product_popularity": 0.99,
                "product_status": "active",
            }
        ]
        res = self.module.decide("CUST_0001", top_k=5, injected_candidates=mock_candidates)
        self.assertEqual(len(res["recommendations"]), 0)
        self.assertEqual(res["excluded_count"], 1)
        self.assertIn("Product is out of stock.", res["excluded_candidates"][0]["policy_reasons"])

    def test_04_low_margin_never_recommended(self):
        mock_candidates = [
            {
                "product_id": "PROD_0036",
                "product_name": "Bamboo Desktop Cable Organizer",
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
        mock_candidates = [
            {
                "product_id": "PROD_0044",
                "product_name": "Legacy 30-Pin Charging Cable",
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
        with self.assertRaises(ValueError) as ctx:
            self.module.decide("CUST_NON_EXISTENT_9999", top_k=5)
        self.assertIn("Customer not found", str(ctx.exception))

    def test_07_all_candidates_rejected_handling(self):
        infeasible_candidates = [
            {
                "product_id": "PROD_0002",
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
                "product_id": "PROD_0003",
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
        res = self.module.decide("CUST_0001", top_k=10, reward_context=False)
        recs = res["recommendations"]
        if len(recs) > 1:
            scores = [r["recommendation_score"] for r in recs]
            self.assertEqual(scores, sorted(scores, reverse=True))

    def test_09_final_recommendations_are_always_feasible(self):
        for cust_id in ["CUST_0001", "CUST_0170", "CUST_0459"]:
            res = self.module.decide(cust_id, top_k=10)
            for rec in res["recommendations"]:
                self.assertEqual(rec["policy_decision"], "PASS")

    def test_10_missing_operational_catalogue_handling(self):
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

    def test_11_exact_top_k_selects_highest_ranked_feasible_candidates(self):
        candidates = [
            _scored_candidate("PROD_C", 0.90),
            _scored_candidate("PROD_A", 0.80),
            _scored_candidate("PROD_B", 0.70),
        ]
        module = _decision_module_with_candidates(candidates)

        with patch(
            "backend.app.recommendation.decision_module.evaluate_product",
            side_effect=_passing_policy,
        ):
            result = module.decide("CUST_TEST", top_k=2)

        self.assertEqual(
            [item["product_id"] for item in result["recommendations"]],
            ["PROD_C", "PROD_A"],
        )
        self.assertEqual(len(result["recommendations"]), 2)
        self.assertTrue(all(item["policy_decision"] == "PASS" for item in result["recommendations"]))

    def test_12_equal_scores_are_tie_broken_by_product_id(self):
        candidates = [
            _scored_candidate("PROD_Z", 0.75),
            _scored_candidate("PROD_A", 0.75),
            _scored_candidate("PROD_M", 0.75),
        ]
        recommender = Mock()
        recommender.rank_candidates.return_value = candidates
        module = DecisionModule(
            recommender=recommender,
            laya_adapter=LayaAdapter(enabled=False),
            decision_engine=WeightedDecisionEngine(enabled=False),
        )
        module._validate_customer_exists = Mock()
        module._load_operational_map = Mock(return_value={})

        with patch(
            "backend.app.recommendation.decision_module.evaluate_product",
            side_effect=_passing_policy,
        ):
            result = module.decide("CUST_TEST", top_k=3)

        self.assertEqual(
            [item["product_id"] for item in result["recommendations"]],
            ["PROD_A", "PROD_M", "PROD_Z"],
        )

    def test_13_no_candidates_response(self):
        module = _decision_module_with_candidates([])

        result = module.decide("CUST_TEST", top_k=2)

        self.assertEqual(result["status"], "NO_CANDIDATES")
        self.assertEqual(result["candidate_count"], 0)
        self.assertEqual(result["feasible_count"], 0)
        self.assertEqual(result["excluded_count"], 0)
        self.assertEqual(result["recommendations"], [])
        self.assertEqual(result["excluded_candidates"], [])
        self.assertEqual(result["message"], "No candidate products found for customer CUST_TEST.")

    def test_14_excluded_candidate_retains_complete_payload(self):
        candidate = _scored_candidate("PROD_EXCLUDED", 0.95)
        module = _decision_module_with_candidates([candidate])

        with patch(
            "backend.app.recommendation.decision_module.evaluate_product",
            return_value=_excluded_policy("PROD_EXCLUDED"),
        ):
            result = module.decide("CUST_TEST", top_k=1)

        excluded = result["excluded_candidates"][0]
        required_keys = {
            "product_id",
            "product_name",
            "category",
            "subcategory",
            "brand",
            "unit_price",
            "product_rating",
            "product_popularity",
            "product_status",
            "recommendation_score",
            "score_explanation",
            "policy_decision",
            "policy_reasons",
            "policy_flags",
        }
        self.assertTrue(required_keys.issubset(set(excluded)))
        self.assertEqual(excluded["policy_decision"], "EXCLUDE")
        self.assertEqual(excluded["policy_reasons"], ["Product is out of stock."])
        self.assertEqual(excluded["policy_flags"], [])
        self.assertEqual(result["recommendations"], [])

    def test_15_high_scoring_excluded_candidate_never_reaches_recommendations(self):
        candidates = [
            _scored_candidate("PROD_INFEASIBLE", 0.99),
            _scored_candidate("PROD_FEASIBLE", 0.60),
        ]
        module = _decision_module_with_candidates(candidates)

        def evaluate(product_id, **_):
            if product_id == "PROD_INFEASIBLE":
                return _excluded_policy(product_id)
            return _passing_policy(product_id)

        with patch(
            "backend.app.recommendation.decision_module.evaluate_product",
            side_effect=evaluate,
        ):
            result = module.decide("CUST_TEST", top_k=1)

        self.assertEqual([item["product_id"] for item in result["recommendations"]], ["PROD_FEASIBLE"])
        self.assertEqual([item["product_id"] for item in result["excluded_candidates"]], ["PROD_INFEASIBLE"])
        self.assertTrue(all(item["policy_decision"] == "PASS" for item in result["recommendations"]))


if __name__ == "__main__":
    unittest.main()
