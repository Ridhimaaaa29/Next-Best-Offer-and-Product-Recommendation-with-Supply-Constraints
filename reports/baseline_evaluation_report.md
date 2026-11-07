# Day 2 Deliverables: Baseline Evaluation Report & Analysis
## Project 4: Next-Best-Offer and Product Recommendation with Supply Constraints

### 1. Executive Summary & Objective
For Day 2 of the 7-day sprint, we established the foundational data processing pipeline, created the synthetic operational catalogue under real-world supply constraints, performed exploratory data analysis (EDA), and benchmarked the **Popularity-based Recommendation Baseline** against an out-of-time chronological evaluation holdout set.

---

### 2. Dataset Preparation & Cleaning Summary

Using the primary transaction dataset (**UCI Online Retail II**, spanning Dec 2009 to Dec 2011):

| Data Stage | Record Count | % of Raw | Description |
| :--- | :--- | :--- | :--- |
| **Raw Ingested Records** | 1,067,371 | 100.0% | Combined Year 2009-2010 and Year 2010-2011 sheets |
| **Cancellations / Negative Qty** | -22,951 | 2.15% | Orders starting with 'C' and non-positive quantities |
| **Invalid / Zero Prices** | -6,207 | 0.58% | Bookkeeping adjustments, free samples, erroneous prices |
| **Missing Customer IDs** | -243,007 | 22.77% | Guest checkouts without registered user identifiers |
| **Non-Merchandise Codes** | -5,351 | 0.50% | Postage (`POST`), Manual (`M`, `D`), Bank fees, Amazon fees |
| **Duplicate Transaction Lines**| -36,550 | 3.42% | Identical timestamp, invoice, customer, and SKU entries |
| **Cleaned Valid Records** | **766,382** | **71.80%** | **High-integrity verified transaction log** |

- **Unique Active Customers**: 5,862
- **Unique Merchandise SKUs**: 4,625
- **Unique Baskets (Invoices)**: 36,645
- **Storage & Relational Structure**: Saved in compressed format (`data/processed/cleaned_transactions.csv.gz`, `baskets.csv.gz`, `customer_interactions.csv.gz`) and indexed relational SQLite database (`data/nbo_database.sqlite`).

---

### 3. Synthetic Operational Catalogue (Supply Constraints)

In compliance with **Project 4 Section 4.3**, because real-world supply metrics are not in the raw retail log, we generated `data/synthetic/operational_catalogue.csv` for all 4,625 SKUs:

- **Inventory Breakdown**:
  - Available Stock ($> 0$ units): **3,704 products (80.1%)**
  - Out of Stock ($= 0$ units): **472 products (10.2%)** — *Mandatory policy exclusion test*
  - Unknown Inventory (`NaN / NULL`): **449 products (9.7%)** — *Mandatory unknown inventory test*
- **Financial Margins**:
  - Mean gross profit margin: **39.8%**
  - Configured low margin test SKUs ($< 10\%$): Verified for exclusion under margin rules
- **Reward Eligibility**:
  - Eligible: 85.0%
  - Ineligible: 15.0%

---

### 4. Baseline Model Implementation & Chronological Evaluation

#### 4.1 Chronological Split (No Target Leakage)
- **Train Window**: 2009-12-01 to 2011-08-31 (**601,071 transactions**)
- **Test Holdout Window**: 2011-09-01 to 2011-12-09 (**165,311 transactions**)
- **Evaluated Population**: **2,339 active repeat customers** who purchased in the out-of-time test window.
- **Deduplication Policy**: Previously purchased products by each customer were excluded from their candidate recommendations (`exclude_purchased = True`).

#### 4.2 Benchmark Results (Popularity Baseline)

| Model | Top-K | Precision@K | Recall@K | HitRate@K | Catalog Coverage |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Popularity Baseline** | **@5** | **0.0378** (3.78%) | **0.0055** (0.55%) | **0.1582** (15.82%) | **0.0102** (1.02%) |
| **Popularity Baseline** | **@10** | **0.0327** (3.27%) | **0.0090** (0.90%) | **0.2317** (23.17%) | **0.0190** (1.90%) |

---

### 5. Key Findings & Baseline Limitations

1. **Severe Catalog Stagnation (Coverage < 2%)**:
   - The popularity baseline repeatedly serves the exact same top 10–20 products globally. Over 98% of the retailer's 4,625 SKUs receive zero exposure.
2. **Hit Rate Ceiling (15.8% @ 5)**:
   - Only 15.8% of repeat customers purchase one of the globally popular items in their holdout period, demonstrating high demand for personalization.
3. **Operational Infeasibility**:
   - A naive popularity model recommends products regardless of warehouse inventory. In our operational catalogue, if a top-selling product hits zero inventory or has unverified stock status, naive rankers fail business requirements.
4. **Planned Day 3 & Day 4 Improvements**:
   - Item-item Co-occurrence & Association Rule Mining (Lift, Confidence).
   - Collaborative filtering / Customer-affinity cosine similarity.
   - Deterministic policy filtering (Stock availability, Gross margin $\ge 10\%$, Reward eligibility).
