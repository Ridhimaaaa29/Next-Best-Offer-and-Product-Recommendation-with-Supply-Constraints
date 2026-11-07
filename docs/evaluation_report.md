# Evaluation Report
## Next-Best-Offer and Product Recommendation with Supply Constraints

### 1. Methodology & Validation Setup
Evaluation is conducted strictly out-of-time (chronological evaluation) to prevent lookahead target leakage:
- **Development/Training Period**: Transactions strictly before `2026-06-01`.
- **Holdout Test Period**: `2026-06-01` to `2026-10-24`.
- **Target Population**: Repeat customers with interaction history prior to cutoff and purchase activity in the evaluation window.

---

### 2. Downstream Recommendation Performance Comparison

| Pipeline | K | Precision@K | Recall@K | HitRate@K | Catalogue Coverage | Policy Compliance | Infeasible Recs |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Day-2 Popularity Baseline** | 5 | 0.0464 | 0.0656 | 0.1630 | 23.08% | 100.0% | 0 |
| **Day-3 Heuristic Pipeline** | 5 | 0.1530 | 0.1921 | 0.4890 | 86.54% | 100.0% | 0 |
| **Day-3 ML Propensity Pipeline** | 5 | **0.1782** | **0.2245** | **0.5412** | **88.46%** | **100.0%** | **0** |
| **Day-2 Popularity Baseline** | 10 | 0.0522 | 0.1397 | 0.3619 | 36.54% | 98.20% | 65 |
| **Day-3 Heuristic Pipeline** | 10 | 0.0856 | 0.2170 | 0.5083 | 86.54% | 100.0% | 0 |
| **Day-3 ML Propensity Pipeline** | 10 | **0.0984** | **0.2512** | **0.5738** | **90.38%** | **100.0%** | **0** |

---

### 3. Classification Metrics (Untouched Test Holdout)
- **Winning ML Model**: Gradient Boosting Classifier
- **5-Fold CV PR-AUC**: `0.7467`
- **Test Set ROC-AUC**: `0.7470`
- **Test Set PR-AUC**: `0.7460`
- **Optimal Decision Threshold**: $\tau^* = 0.5000$
- **Brier Score**: `0.1802` (Well-calibrated probabilities)
