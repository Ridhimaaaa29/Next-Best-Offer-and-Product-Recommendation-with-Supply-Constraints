# Architecture Overview
## Next-Best-Offer and Product Recommendation with Supply Constraints

### 1. High-Level Architecture
The system decouples **customer demand/preference modeling** from **supply/operational constraints** to guarantee zero-defect, actionable recommendations.

```
       Customer Context
              ↓
      Candidate Generation (Unseen products in customer's preferred category)
              ↓
    ML / Heuristic Scoring (Gradient Boosting Conversion Propensity)
              ↓
  Deterministic Policy Engine (Stock > 0, Margin >= 10%, Active Status, Context Rules)
              ↓
    Deterministic Ranker (Feasible items sorted by Score DESC, Product ID ASC)
              ↓
    Top-K Output with Audit Log (Includes pass items and reason-annotated exclusions)
```

### 2. Core Subsystems

#### A. Backend Application (`backend/app/`)
* **`api/routes/`**: FastAPI REST endpoints (`health.py`, `recommendations.py`, `products.py`, `evaluation.py`, `decisions.py`).
* **`api/schemas/`**: Strict Pydantic v2 data models with `extra="forbid"` on requests.
* **`recommendation/`**:
  * `candidate_generator.py`: Generates candidate products from preferred category excluding prior interactions.
  * `recommendation_model.py`: Gradient Boosting ML propensity scoring with fallback to explainable heuristic weighting.
  * `policy_engine.py`: Deterministic evaluator for business and supply rules.
  * `decision_module.py`: High-level orchestrator executing the full decision pipeline.
* **`domain/`**: Granular business rule definitions (`inventory.py`, `margin.py`, `eligibility.py`, `fulfilment.py`).
* **`decision/`**: Decision optimization primitives (`objectives.py`, `constraints.py`, `baseline_ranker.py`, `validator.py`).
* **`middleware/` & `guardrails/`**: Request ID tracking, timing, structured error handling, and strict output invariant checks.
* **`db/`**: Neon PostgreSQL connection management via SQLAlchemy and raw psycopg.

#### B. Data Pipeline (`data/`)
* **Synthetic Ecosystem**: Generated via `scripts/generate_synthetic_ecosystem.py` and stored in Neon PostgreSQL (7 normalized tables).
* **Processed & Raw**: Historical retail datasets for EDA and baseline benchmarking.

#### C. Machine Learning Engine
* Model: **Gradient Boosting Classifier** (`HistGradientBoostingClassifier`).
* Cross-Validation PR-AUC: **0.7467** (5-Fold Stratified CV).
* Holdout Test ROC-AUC: **0.7470**, PR-AUC: **0.7460**.
* Strict chronological cutoff at `2026-06-01` ensures zero future leakage.
