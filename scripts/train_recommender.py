"""
Propensity Model Training CLI Script
Project: Next-Best-Offer and Product Recommendation with Supply Constraints

Canonical entrypoint that delegates execution to the core implementation
in `backend.app.ml.trainer.PropensityTrainer`.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.ml.dataset_builder import PropensityDatasetBuilder
from backend.app.ml.trainer import (
    PropensityTrainer,
    NUMERICAL_FEATURES,
    CATEGORICAL_FEATURES,
)


def main():
    print("=" * 70)
    print("PROPENSITY RECOMMENDER TRAINING (Canonical: backend.app.ml.trainer)")
    print("=" * 70)

    # 1. Fetch temporal datasets via canonical dataset builder
    print("\n1. Building development and holdout datasets...")
    builder = PropensityDatasetBuilder()
    dev_df, holdout_df = builder.build_temporal_datasets()

    print(f"   Dev dataset shape:     {dev_df.shape}")
    print(f"   Holdout dataset shape: {holdout_df.shape}")

    # 2. Invoke canonical trainer
    print("\n2. Executing 5-Fold Stratified Cross-Validation & Model Selection...")
    trainer = PropensityTrainer(random_seed=42)
    results = trainer.train_and_tune_all(dev_df)

    print("\n3. Training complete.")
    print(f"   Selected model:    {results['winner_name']}")
    print(f"   Optimal threshold: {results['optimal_threshold']:.4f}")
    print(f"   Saved artifact:    {results['artifact_path']}")


if __name__ == "__main__":
    main()
