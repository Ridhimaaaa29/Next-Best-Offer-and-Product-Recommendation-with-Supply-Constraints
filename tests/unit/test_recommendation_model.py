"""
Unit & Integration Tests for Recommendation Model (isolated from live Neon DB).
Tests:
1. Customer with rich interaction history (Gradient Boosting / scoring pipeline)
2. Customer with minimal interaction history
3. Deterministic / reproducible scores across consecutive runs
4. No leakage from operational constraints into recommendation model
5. Strict descending ranking order
"""

from datetime import datetime, timezone
import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.models import Base, Customer, CustomerProductInteraction, Product
from backend.app.recommendation.recommendation_model import (
    RecommendationModel,
    score_customer_candidates,
)


def _seed_sqlite_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionCls = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionCls()
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)

    db.add_all(
        [
            Customer(
                customer_id="CUST_0001",
                customer_segment="High-Value Enthusiast",
                age_group="25-34",
                location="Austin, TX",
                membership_tier="Gold",
                reward_points=1200,
                preferred_category="Electronics",
                average_order_value=140.0,
                total_orders=8,
                total_spend=1120.0,
                last_purchase_date=now,
                customer_status="active",
            ),
            Customer(
                customer_id="CUST_0459",
                customer_segment="Casual Budget Shopper",
                age_group="18-24",
                location="Seattle, WA",
                membership_tier="Bronze",
                reward_points=50,
                preferred_category="Electronics",
                average_order_value=40.0,
                total_orders=1,
                total_spend=40.0,
                last_purchase_date=now,
                customer_status="active",
            ),
        ]
    )
    products = [
        Product(
            product_id="PROD_0001",
            product_name="Wireless Headphones",
            category="Electronics",
            subcategory="Audio",
            brand="AudioMax",
            unit_price=149.99,
            unit_cost=80.0,
            product_rating=4.8,
            product_popularity=0.92,
            product_status="active",
        ),
        Product(
            product_id="PROD_0003",
            product_name="USB-C Studio Mic",
            category="Electronics",
            subcategory="Audio",
            brand="AudioMax",
            unit_price=89.99,
            unit_cost=45.0,
            product_rating=4.6,
            product_popularity=0.81,
            product_status="active",
        ),
        Product(
            product_id="PROD_0004",
            product_name="4K Action Camera",
            category="Electronics",
            subcategory="Cameras",
            brand="LensPro",
            unit_price=249.99,
            unit_cost=140.0,
            product_rating=4.4,
            product_popularity=0.75,
            product_status="active",
        ),
    ]
    db.add_all(products)
    db.add(
        CustomerProductInteraction(
            customer_id="CUST_0001",
            product_id="PROD_9999",
            interaction_count=5,
            last_interaction_date=now,
            purchase_frequency=2,
            total_quantity=3,
            total_spend=250.0,
            category_preference_score=0.85,
            recency_score=0.90,
        )
    )
    db.commit()
    return engine, SessionCls, db


def _mock_psycopg_candidates(rows_by_cust):
    def _connect(_url):
        conn = MagicMock()
        cur = conn.cursor.return_value.__enter__.return_value
        state = {"cust": None}

        def _exec(sql, params=()):
            if "preferred_category" in sql and "FROM customers" in sql:
                state["cust"] = params[0]
            else:
                state["cust"] = params[1] if len(params) > 1 else state["cust"]

        def _fetchone():
            c = state["cust"]
            return ("Electronics",) if c in rows_by_cust else None

        def _fetchall():
            return rows_by_cust.get(state["cust"], [])

        cur.execute.side_effect = _exec
        cur.fetchone.side_effect = _fetchone
        cur.fetchall.side_effect = _fetchall
        conn.__enter__.return_value = conn
        return conn

    return _connect


class TestRecommendationModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine, cls.SessionCls, cls.db = _seed_sqlite_session()
        cls.model = RecommendationModel(session=cls.db)
        rows = [
            ("PROD_0001", "Wireless Headphones", "Electronics", "Audio", "AudioMax", 149.99, 4.8, 0.92, "active"),
            ("PROD_0003", "USB-C Studio Mic", "Electronics", "Audio", "AudioMax", 89.99, 4.6, 0.81, "active"),
            ("PROD_0004", "4K Action Camera", "Electronics", "Cameras", "LensPro", 249.99, 4.4, 0.75, "active"),
        ]
        cls.rows_by_cust = {"CUST_0001": rows, "CUST_0459": rows}

    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        cls.engine.dispose()

    def test_customer_with_interaction_history(self):
        from contextlib import contextmanager

        @contextmanager
        def _db_ctx():
            yield self.db

        with (
            patch("backend.app.recommendation.recommendation_model.get_db_context", side_effect=_db_ctx),
            patch("backend.app.recommendation.candidate_generator.psycopg.connect", side_effect=_mock_psycopg_candidates(self.rows_by_cust)),
        ):
            result = score_customer_candidates(customer_id="CUST_0001", limit=10)
        self.assertEqual(result["customer_id"], "CUST_0001")
        self.assertEqual(result["preferred_category"], "Electronics")
        self.assertGreater(result["candidate_count"], 0)
        top_cand = result["ranked_candidates"][0]
        self.assertGreater(top_cand["score"], 0.0)
        self.assertLessEqual(top_cand["score"], 1.0)
        exp = top_cand["explanation"]
        for key in ("category_affinity_score", "popularity_score", "rating_score", "interaction_bonus", "reason_codes"):
            self.assertIn(key, exp)
        self.assertGreater(len(exp["reason_codes"]), 0)

    def test_customer_with_limited_history(self):
        from contextlib import contextmanager

        @contextmanager
        def _db_ctx():
            yield self.db

        with (
            patch("backend.app.recommendation.recommendation_model.get_db_context", side_effect=_db_ctx),
            patch("backend.app.recommendation.candidate_generator.psycopg.connect", side_effect=_mock_psycopg_candidates(self.rows_by_cust)),
        ):
            result = score_customer_candidates(customer_id="CUST_0459", limit=10)
        self.assertEqual(result["customer_id"], "CUST_0459")
        self.assertGreater(result["candidate_count"], 0)
        for cand in result["ranked_candidates"]:
            self.assertGreaterEqual(cand["score"], 0.0)
            self.assertLessEqual(cand["score"], 1.0)

    def test_deterministic_scoring(self):
        with patch("backend.app.recommendation.candidate_generator.psycopg.connect", side_effect=_mock_psycopg_candidates(self.rows_by_cust)):
            run_1 = self.model.rank_candidates("CUST_0001", candidate_limit=5)
            run_2 = self.model.rank_candidates("CUST_0001", candidate_limit=5)
        self.assertEqual(len(run_1), len(run_2))
        for c1, c2 in zip(run_1, run_2):
            self.assertEqual(c1.product_id, c2.product_id)
            self.assertEqual(c1.score, c2.score)
            self.assertEqual(c1.explanation.to_dict(), c2.explanation.to_dict())

    def test_no_operational_constraint_leakage(self):
        mock_candidates = [
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
                "product_id": "PROD_0036",
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
        scored = self.model.rank_candidates(customer_id="CUST_0001", candidates=mock_candidates)
        scored_ids = [c.product_id for c in scored]
        self.assertIn("PROD_0002", scored_ids)
        self.assertIn("PROD_0036", scored_ids)
        for c in scored:
            self.assertGreater(c.score, 0.0)

    def test_ranking_order(self):
        with patch("backend.app.recommendation.candidate_generator.psycopg.connect", side_effect=_mock_psycopg_candidates(self.rows_by_cust)):
            scored = self.model.rank_candidates("CUST_0001", candidate_limit=10)
        scores = [c.score for c in scored]
        self.assertEqual(scores, sorted(scores, reverse=True))


if __name__ == "__main__":
    unittest.main()
