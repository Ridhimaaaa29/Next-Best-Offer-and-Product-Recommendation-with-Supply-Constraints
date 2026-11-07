"""
Recommender & ML Experiment Evaluation CLI Script
Project: Next-Best-Offer and Product Recommendation with Supply Constraints

Canonical entrypoint that delegates execution to the comprehensive evaluation harness
in `scripts.evaluate_ml_experiments.evaluate_ml_experiments()`.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.evaluate_ml_experiments import evaluate_ml_experiments

if __name__ == "__main__":
    evaluate_ml_experiments()
