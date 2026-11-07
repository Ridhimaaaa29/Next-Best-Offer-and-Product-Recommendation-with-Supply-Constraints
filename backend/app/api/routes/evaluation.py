"""Read-only offline evaluation report endpoint."""

import csv
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter

router = APIRouter(tags=["Evaluation"])


PROJECT_ROOT = Path(__file__).resolve().parents[4]


@router.get("/evaluation/metrics", summary="Get saved offline evaluation metrics")
def get_evaluation_metrics() -> dict[str, Any]:
    csv_path = PROJECT_ROOT / "reports" / "day3_evaluation_results.csv"
    rows: list[dict[str, str]] = []
    if csv_path.exists():
        with csv_path.open(newline="", encoding="utf-8") as file:
            rows = list(csv.DictReader(file))
    ml_path = PROJECT_ROOT / "reports" / "ml_model_evaluation.md"
    ml_text = ml_path.read_text(encoding="utf-8") if ml_path.exists() else ""
    patterns = {
        "model": r"The winning model family is \*\*(.+?)\*\*",
        "cv_pr_auc": r"achieving \*\*PR-AUC of ([0-9.]+)\*\*",
        "holdout_pr_auc": r"PR-AUC of \*\*([0-9.]+)",
        "holdout_roc_auc": r"ROC-AUC: ([0-9.]+)",
    }
    ml_metrics = {
        key: match.group(1)
        for key, pattern in patterns.items()
        if (match := re.search(pattern, ml_text))
    }
    return {
        "source": "offline_saved_reports",
        "recommendation_metrics": rows,
        "ml_classification_metrics": ml_metrics,
    }
