"""
Propensity Model Trainer & Cross-Validation Tuner
Project: Next-Best-Offer and Product Recommendation with Supply Constraints

Implements:
1. Feature preprocessor with ColumnTransformer (OneHotEncoder for categoricals, StandardScaler for numericals).
2. Hyperparameter Grid Tuning using 5-Fold Stratified Cross-Validation on Development set only:
   - Logistic Regression
   - Random Forest Classifier
   - Gradient Boosting Classifier
3. Model comparison using Validation PR-AUC (Average Precision) and ROC-AUC.
4. Threshold selection on validation predictions using optimal F1-score.
5. Serialization of best model artifact via joblib.
"""

import os
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple
from pathlib import Path

from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.model_selection import StratifiedKFold, GridSearchCV
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    brier_score_loss,
    log_loss,
    precision_recall_curve,
    f1_score,
    accuracy_score,
    precision_score,
    recall_score,
    confusion_matrix,
)

from backend.app.ml.dataset_builder import PropensityDatasetBuilder


NUMERICAL_FEATURES = [
    "reward_points",
    "hist_total_orders",
    "hist_total_spend",
    "hist_aov",
    "unit_price",
    "unit_cost",
    "product_rating",
    "product_popularity",
    "hist_product_popularity",
    "hist_interaction_count",
    "hist_total_quantity",
    "hist_total_spend_interaction",
    "hist_recency_days",
    "is_preferred_category",
]

CATEGORICAL_FEATURES = [
    "membership_tier",
    "category",
    "subcategory",
]


def build_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERICAL_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
        ]
    )


class PropensityTrainer:
    def __init__(self, random_seed: int = 42):
        self.random_seed = random_seed
        self.cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=random_seed)
        self.models_dir = Path("models")
        self.models_dir.mkdir(exist_ok=True)

    def train_and_tune_all(
        self,
        dev_df: pd.DataFrame,
    ) -> Dict[str, Any]:
        """
        Executes hyperparameter tuning across the three model families strictly on dev_df.
        """
        X = dev_df[NUMERICAL_FEATURES + CATEGORICAL_FEATURES]
        y = dev_df["target"].values

        results = {}

        # -------------------------------------------------------------
        # 1. Logistic Regression
        # -------------------------------------------------------------
        print("\n[Tuning 1/3] Logistic Regression...")
        lr_pipe = Pipeline([
            ("preprocessor", build_preprocessor()),
            ("classifier", LogisticRegression(random_state=self.random_seed, max_iter=1000)),
        ])
        lr_param_grid = {
            "classifier__C": [0.01, 0.1, 1.0, 10.0],
            "classifier__penalty": ["l2"],
            "classifier__solver": ["lbfgs"],
        }
        lr_search = GridSearchCV(
            lr_pipe,
            lr_param_grid,
            cv=self.cv,
            scoring="average_precision",
            n_jobs=-1,
            refit=True,
        )
        lr_search.fit(X, y)
        results["Logistic Regression"] = {
            "best_estimator": lr_search.best_estimator_,
            "best_params": lr_search.best_params_,
            "best_cv_pr_auc": float(lr_search.best_score_),
        }
        print(f"  Best params: {lr_search.best_params_}")
        print(f"  Best CV PR-AUC: {lr_search.best_score_:.4f}")

        # -------------------------------------------------------------
        # 2. Random Forest Classifier
        # -------------------------------------------------------------
        print("\n[Tuning 2/3] Random Forest Classifier...")
        rf_pipe = Pipeline([
            ("preprocessor", build_preprocessor()),
            ("classifier", RandomForestClassifier(random_state=self.random_seed)),
        ])
        rf_param_grid = {
            "classifier__n_estimators": [50, 100],
            "classifier__max_depth": [4, 8, None],
            "classifier__min_samples_split": [2, 5],
        }
        rf_search = GridSearchCV(
            rf_pipe,
            rf_param_grid,
            cv=self.cv,
            scoring="average_precision",
            n_jobs=-1,
            refit=True,
        )
        rf_search.fit(X, y)
        results["Random Forest"] = {
            "best_estimator": rf_search.best_estimator_,
            "best_params": rf_search.best_params_,
            "best_cv_pr_auc": float(rf_search.best_score_),
        }
        print(f"  Best params: {rf_search.best_params_}")
        print(f"  Best CV PR-AUC: {rf_search.best_score_:.4f}")

        # -------------------------------------------------------------
        # 3. Gradient Boosting Classifier
        # -------------------------------------------------------------
        print("\n[Tuning 3/3] Gradient Boosting Classifier...")
        gb_pipe = Pipeline([
            ("preprocessor", build_preprocessor()),
            ("classifier", GradientBoostingClassifier(random_state=self.random_seed)),
        ])
        gb_param_grid = {
            "classifier__n_estimators": [50, 100],
            "classifier__learning_rate": [0.01, 0.05, 0.1],
            "classifier__max_depth": [3, 5],
        }
        gb_search = GridSearchCV(
            gb_pipe,
            gb_param_grid,
            cv=self.cv,
            scoring="average_precision",
            n_jobs=-1,
            refit=True,
        )
        gb_search.fit(X, y)
        results["Gradient Boosting"] = {
            "best_estimator": gb_search.best_estimator_,
            "best_params": gb_search.best_params_,
            "best_cv_pr_auc": float(gb_search.best_score_),
        }
        print(f"  Best params: {gb_search.best_params_}")
        print(f"  Best CV PR-AUC: {gb_search.best_score_:.4f}")

        # Select Best Model based on Validation PR-AUC
        best_name = max(results, key=lambda k: results[k]["best_cv_pr_auc"])
        best_model = results[best_name]["best_estimator"]

        # Calculate Out-of-Fold / Validation Predictions on dev set to find optimal threshold
        y_prob_val = np.zeros(len(y))
        for train_idx, val_idx in self.cv.split(X, y):
            fold_model = results[best_name]["best_estimator"]
            fold_model.fit(X.iloc[train_idx], y[train_idx])
            y_prob_val[val_idx] = fold_model.predict_proba(X.iloc[val_idx])[:, 1]

        # Determine optimal threshold on validation predictions using F1
        precisions, recalls, thresholds = precision_recall_curve(y, y_prob_val)
        f1_scores = 2 * (precisions * recalls) / (precisions + recalls + 1e-9)
        best_thresh_idx = np.argmax(f1_scores)
        optimal_threshold = float(thresholds[best_thresh_idx]) if best_thresh_idx < len(thresholds) else 0.50

        # Save metadata and best model artifact
        save_path = self.models_dir / "nbo_propensity_best_model.joblib"
        artifact = {
            "model_name": best_name,
            "pipeline": best_model,
            "best_params": results[best_name]["best_params"],
            "cv_pr_auc": results[best_name]["best_cv_pr_auc"],
            "optimal_threshold": optimal_threshold,
            "numerical_features": NUMERICAL_FEATURES,
            "categorical_features": CATEGORICAL_FEATURES,
        }
        joblib.dump(artifact, save_path)
        print(f"\n[WINNER] Selected: {best_name} (CV PR-AUC: {results[best_name]['best_cv_pr_auc']:.4f})")
        print(f"  Optimal Validation Decision Threshold: {optimal_threshold:.4f}")
        print(f"  Model saved to {save_path}")

        return {
            "tuning_results": results,
            "winner_name": best_name,
            "optimal_threshold": optimal_threshold,
            "artifact_path": str(save_path),
        }
