# ML Model Training & Evaluation Report
## Project: Next-Best-Offer and Product Recommendation with Supply Constraints

### 1. Executive Summary
This report documents the machine learning experiments for customer-offer purchase propensity modeling on the **Synthetic MVP Dataset (Neon PostgreSQL)**.

Three model families were trained and tuned on historical data prior to the cutoff date:
1. **Logistic Regression** (Linear baseline)
2. **Random Forest Classifier** (Non-linear bagging ensemble)
3. **Gradient Boosting Classifier** (Iterative gradient tree boosting)

The winning model family is **Gradient Boosting**, achieving **PR-AUC of 0.7467** during 5-Fold Stratified Cross-Validation on the development set, and **PR-AUC of 0.7094 (ROC-AUC: 0.8583)** on the untouched holdout test period.

---

### 2. Temporal Split & Leakage Prevention Strategy

* **Development Window (Training & Cross-Validation):**
  * Feature cutoff date: `2026-01-01` (Features built strictly using transactions before this date).
  * Target observation window: `2026-01-01` to `2026-05-31`.
  * Total development instances: 5,832 (1,458 positive, 4,374 negative).
* **Untouched Holdout Window (Final Test Evaluation):**
  * Feature cutoff date: `2026-06-01` (Features built strictly using transactions before this date).
  * Target observation window: `2026-06-01` to `2026-10-24`.
  * Total test instances: 5,524 (1,381 positive, 4,143 negative).
* **Negative-Label Semantics:**
  * $Y = 1$: Customer purchased the product during the target window.
  * $Y = 0$: Customer did **not** purchase the product in the target window.
  * Negative instances were sampled at a reproducible **3:1 ratio** using fixed seed (`seed=42`).
  * *Methodological Note:* The 3:1 ratio is strictly an experimental negative-sampling choice to construct a well-calibrated training distribution, NOT an observed real-world conversion ratio.

---

### 3. Hyperparameter Tuning & Cross-Validation Comparison

Tuning was conducted using **5-Fold Stratified Cross-Validation** strictly inside the development set:

| Model Family | Best Hyperparameters | 5-Fold CV PR-AUC | Selection Status |
| :--- | :--- | :---: | :---: |
| **Logistic Regression** | `C=10.0, penalty='l2', solver='lbfgs'` | 0.7399 | Baseline |
| **Random Forest** | `max_depth=8, min_samples_split=2, n_estimators=50` | 0.7437 | Candidate |
| **Gradient Boosting** | `learning_rate=0.05, max_depth=5, n_estimators=50` | **0.7467** | **WINNER (Selected)** |

* **Optimal Decision Threshold (Validation F1):** $\tau^* = 0.2522$

---

### 4. Classification Performance on Untouched Holdout Test Set

Evaluated across 5,524 holdout customer-product interaction pairs:

| Classification Metric | At Default Threshold ($\tau = 0.50$) | At Optimal Threshold ($\tau^* = 0.2522$) | Description |
| :--- | :---: | :---: | :--- |
| **ROC-AUC** | **0.8583** | **0.8583** | Discriminative ability across all thresholds |
| **PR-AUC (Avg Precision)** | **0.7094** | **0.7094** | Precision-Recall trade-off |
| **Brier Score** | **0.1143** | **0.1143** | Mean squared probability error (calibration) |
| **Log-Loss** | **0.3726** | **0.3726** | Cross-entropy loss |
| **Accuracy** | 0.8436 | 0.8244 | Overall fraction of correct predictions |
| **Precision** | 0.7502 | 0.616 | Positive predictive value |
| **Recall** | 0.5612 | 0.79 | True positive rate |
| **F1-Score** | 0.6421 | **0.6923** | Harmonic mean of precision and recall |

#### Confusion Matrices:
* **Standard Threshold ($\tau = 0.50$):**
  * True Negatives: `3885`, False Positives: `258`
  * False Negatives: `606`, True Positives: `775`
* **Optimal Threshold ($\tau^* = 0.2522$):**
  * True Negatives: `3463`, False Positives: `680`
  * False Negatives: `290`, True Positives: `1091`

---

### 5. Downstream Recommendation Benchmark & Three-Way Comparison

| Pipeline | K | Precision@K | Recall@K | HitRate@K | Coverage@K | Policy_Compliance | Infeasible_Recs |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Day-2 Popularity Baseline | 5 | 0.0464 | 0.0656 | 0.163 | 0.2308 | 1.0 | 0 |
| Day-3 Heuristic Model | 5 | 0.153 | 0.1921 | 0.489 | 0.8654 | 1.0 | 0 |
| Day-3 ML Propensity (Gradient Boosting) | 5 | 0.1547 | 0.1967 | 0.5 | 0.8654 | 1.0 | 0 |
| Day-2 Popularity Baseline | 10 | 0.0522 | 0.1397 | 0.3619 | 0.3654 | 0.982 | 65 |
| Day-3 Heuristic Model | 10 | 0.0856 | 0.217 | 0.5083 | 0.8654 | 1.0 | 0 |
| Day-3 ML Propensity (Gradient Boosting) | 10 | 0.0856 | 0.217 | 0.5083 | 0.8654 | 1.0 | 0 |

---

### 6. Architectural Safety & Invariant Verification

1. **Policy Engine Authority (100% Policy Feasibility):**
   * The ML Propensity model generated conversion scores without knowledge of warehouse stock or supplier lead times.
   * Feasibility filtering via `policy_engine.py` strictly removed all out-of-stock items (such as `PROD_0002`) and low-margin items (`PROD_0036`).
   * **Infeasible items reaching final recommendation: ZERO.**
2. **Deterministic Heuristic Fallback:**
   * If the model artifact is missing or feature extraction fails, the pipeline seamlessly reverts to the deterministic Day-3 heuristic formula without downtime.

---

### 7. Reproducibility Command

To reproduce this benchmark and training run:
```bash
python scripts/evaluate_ml_experiments.py
```
