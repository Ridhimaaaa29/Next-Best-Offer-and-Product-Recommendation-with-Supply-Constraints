# Data Dictionary & Synthetic Catalogue Assumptions

## 1. Provenance & Dataset Mapping Overview

| Dataset | File Path | Provenance | Core Purpose |
| :--- | :--- | :--- | :--- |
| **Cleaned Transactions** | `data/processed/cleaned_transactions.csv.gz` | UCI Online Retail II (2009-2011) | Basket analysis, customer-item frequency, out-of-time evaluation |
| **Baskets Table** | `data/processed/baskets.csv.gz` | Aggregated from cleaned transactions | Transaction basket level co-occurrence, basket size & revenue |
| **Customer Interactions** | `data/processed/customer_interactions.csv.gz` | Aggregated from cleaned transactions | Historical repeat purchases, customer lifetime value, personalized filtering |
| **Synthetic Operational Catalogue** | `data/synthetic/operational_catalogue.csv` | Synthetic generation conditioned on real SKUs & prices | Mandatory supply-chain constraints: stock, margin, supplier lead time, reward eligibility |

---

## 2. Operational Catalogue Schema (`data/synthetic/operational_catalogue.csv`)

As required by **Project 4 Specification Section 4.3**:

| Field | Data Type | Source | Description & Business Meaning |
| :--- | :--- | :--- | :--- |
| `product_id` | `VARCHAR(64)` | Real (StockCode) | Unique product SKU identifier from retail transactions. |
| `description` | `TEXT` | Real (Description) | Clean product title / description. |
| `category` | `VARCHAR(64)` | Synthetic | E-commerce taxonomy (`Home & Kitchen`, `Gifts & Novelties`, `Stationery & Cards`, etc.). |
| `unit_price` | `NUMERIC(10,2)` | Real (Median Price) | Observed median selling price per unit. |
| `unit_cost` | `NUMERIC(10,2)` | Synthetic | Operational wholesale/manufacturing cost per unit ($unit\_price \times (1 - margin)$). |
| `gross_margin` | `NUMERIC(5,3)` | Synthetic | Product profit margin percentage: $(price - cost) / price$. |
| `available_stock` | `NUMERIC(10,2)` | Synthetic | Real-time warehouse inventory count. **Crucial**: Contains `NULL / NaN` to test unverified inventory. |
| `reorder_point` | `INTEGER` | Synthetic | Inventory threshold triggering procurement replenishment (10, 20, 50, 100 units). |
| `supplier_lead_days`| `INTEGER` | Synthetic | Verified vendor replenishment lead time in business days. |
| `fulfilment_class` | `VARCHAR(32)` | Synthetic | Operational handling class (`Standard`, `Express`, `Heavy/Bulky`, `Fragile`). |
| `reward_eligible` | `BOOLEAN` | Synthetic | Whether product qualifies for loyalty discounts and points redemption. |
| `max_discount_pct` | `NUMERIC(4,2)` | Synthetic | Ceiling discount percentage permitted without causing negative operating margin. |
| `data_source` | `VARCHAR(64)` | Metadata | Provenance tracking tag (`synthetic_catalogue_seed42`). |
| `last_updated_at` | `TIMESTAMP` | Metadata | Operational timestamp freshness check. |

---

## 3. Explicit Operational Test Cases Configured

In strict compliance with **Section 4.3 & 13.3 (Data Integrity & Edge-case requirements)**:
1. **Available Stock Test Case**: Standard in-stock product ($available\_stock > reorder\_point$, healthy margin, reward eligible) $\rightarrow$ Expected result: **Eligible**.
2. **Zero Stock (Out-of-Stock) Test Case**: $available\_stock = 0.0$ $\rightarrow$ Expected result: **Excluded by Policy Engine** (Reason: `Known inventory is insufficient`).
3. **Low Stock Test Case**: $1 \le available\_stock < reorder\_point$ $\rightarrow$ Expected result: **Flagged for expedited replenishment**.
4. **Unknown / Missing Inventory Test Case**: $available\_stock = NULL / NaN$ $\rightarrow$ Expected result: **Marked Unknown & Excluded from actionable offers** (Reason: `Inventory status is unknown`).
5. **Low Margin Test Case**: $gross\_margin < 0.10$ $\rightarrow$ Expected result: **Excluded by margin policy** (Reason: `Gross margin below minimum threshold`).
6. **Reward Ineligible Test Case**: $reward\_eligible = FALSE$ $\rightarrow$ Expected result: **Filtered out when context is promotional/reward redemption**.

---

## 4. Cleaning Rules & Data Quality Exclusions

- **Cancellations / Returns**: All invoices starting with `'C'` or items with $Quantity \le 0$ were excluded from positive basket modeling.
- **Bad Prices**: Transactions with $Price \le 0$ (bad accounting, giveaways, system tests) were filtered out.
- **Guest / Missing Users**: Missing `Customer_ID` records (~22.7%) excluded from personalized customer matrix (retained in general item-frequency if needed).
- **Non-merchandise SKUs**: Excluded manual administrative codes (`POST`, `D`, `M`, `BANK CHARGES`, `CRUK`, `AMAZONFEE`).
