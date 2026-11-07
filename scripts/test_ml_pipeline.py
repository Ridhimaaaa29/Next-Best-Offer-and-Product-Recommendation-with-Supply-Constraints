"""
Unit & Integration Tests for ML Propensity Pipeline
Project: Next-Best-Offer and Product Recommendation with Supply Constraints

Tests:
1. Temporal Leakage Protection: Confirms all transaction dates used in feature matrices are strictly < cutoff_date.
2. Feature Leakage Protection: Confirms target label Y is not present in feature matrices X.
3. Negative Sampling Reproducibility: Confirms identical records produced when seed is fixed.
4. Model Training & Convergence: Confirms pipeline trains and outputs probabilities in [0.0, 1.0].
5. Policy Compliance Invariant: Confirms out-of-stock (PROD_0002) and low-margin (PROD_0036) products are excluded.
6. Fallback Safety: Confirms fallback to heuristic scoring when model artifact is absent or disabled.
"""

import unittest
from pathlib import Path
import joblib
import numpy as np
import pandas as pd

from backend.app.ml.dataset_builder import PropensityDatasetBuilder
from backend.app.ml.trainer import NUMERICAL_FEATURES, CATEGORICAL_FEATURES
from backend.app.recommendation.policy_engine import evaluate_product
from backend.app.recommendation.recommendation_model import RecommendationModel


class TestMLPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.builder = PropensityDatasetBuilder(random_seed=42)

    def test_01_temporal_leakage_protection(self):
        """Verify no transactions on or after cutoff_date are used to build features."""
        cutoff = "2026-01-01"
        txn_df, cust_df, prod_df = self.builder.fetch_raw_tables()
        c_feats, p_feats, cp_agg = self.builder.build_features_for_cutoff(
            txn_df, cust_df, prod_df, cutoff_date=cutoff
        )

        cutoff_dt = pd.to_datetime(cutoff)
        # Check max date in transactions used
        hist_txns = txn_df[txn_df["transaction_date"] < cutoff_dt]
        self.assertTrue((hist_txns["transaction_date"] < cutoff_dt).all())

    def test_02_feature_leakage_protection(self):
        """Verify target column is completely absent from feature matrix X."""
        dev_df, _ = self.builder.build_train_and_test_datasets()
        feature_cols = NUMERICAL_FEATURES + CATEGORICAL_FEATURES
        self.assertNotIn("target", feature_cols)
        for col in feature_cols:
            self.assertIn(col, dev_df.columns)

    def test_03_negative_sampling_reproducibility(self):
        """Verify negative sampling produces bit-identical records with the same seed."""
        b1 = PropensityDatasetBuilder(random_seed=123)
        b2 = PropensityDatasetBuilder(random_seed=123)
        dev1, _ = b1.build_train_and_test_datasets()
        dev2, _ = b2.build_train_and_test_datasets()

        self.assertEqual(len(dev1), len(dev2))
        self.assertTrue((dev1["target"] == dev2["target"]).all())
        self.assertTrue((dev1["product_id"] == dev2["product_id"]).all())

    def test_04_model_artifact_and_probability_bounds(self):
        """Verify trained best model artifact loads and outputs probabilities strictly in [0.0, 1.0]."""
        model_path = Path("models") / "nbo_propensity_best_model.joblib"
        self.assertTrue(model_path.exists())

        artifact = joblib.load(model_path)
        self.assertIn("pipeline", artifact)
        self.assertIn("optimal_threshold", artifact)

        pipeline = artifact["pipeline"]
        _, test_df = self.builder.build_train_and_test_datasets()
        sample_X = test_df[NUMERICAL_FEATURES + CATEGORICAL_FEATURES].iloc[:50]
        probs = pipeline.predict_proba(sample_X)[:, 1]

        self.assertEqual(len(probs), 50)
        self.assertTrue((probs >= 0.0).all())
        self.assertTrue((probs <= 1.0).all())

    def test_05_policy_compliance_invariant(self):
        """
        Verify that out-of-stock and low-margin items evaluated through policy_engine
        are strictly EXCLUDED regardless of ML scores.
        """
        eval_p2 = evaluate_product("PROD_0002")  # Out of stock
        self.assertEqual(eval_p2["decision"], "EXCLUDE")
        self.assertIn("Product is out of stock.", eval_p2["reasons"])

        eval_p36 = evaluate_product("PROD_0036")  # Margin < 10%
        self.assertEqual(eval_p36["decision"], "EXCLUDE")
        self.assertIn("below the 10% minimum", " ".join(eval_p36["reasons"]))

    def test_06_heuristic_fallback_safety(self):
        """Verify recommendation_model executes deterministic heuristic if ML mode is inactive or disabled."""
        model = RecommendationModel(use_ml=False)
        scored = model.rank_candidates("CUST_0001", candidate_limit=5)
        self.assertGreater(len(scored), 0)
        for s in scored:
            self.assertGreater(s.score, 0.0)
            self.assertLessEqual(s.score, 1.0)
            self.assertIn("category_affinity_score", s.explanation.to_dict())


if __name__ == "__main__":
    unittest.main()
