# Synthetic Data Layer (`data/synthetic/`)

This directory houses the complete, self-contained synthetic dataset ecosystem for the **Next-Best-Offer and Product Recommendation with Supply Constraints** project.

All files are purely synthetic, internally coherent, and free from external dependencies or unverified assumptions.

---

## 1. Directory Structure

```
data/synthetic/
├── customers.csv                      # Customer profiles, loyalty tiers & category preferences (500 rows)
├── products.csv                       # Master product catalogue across 5 departments (52 rows)
├── transactions.csv                   # Chronological line-item purchase history (7,466 rows)
├── baskets.csv                        # Market basket co-occurrence container for association mining (7,466 rows)
├── customer_product_interactions.csv  # User-item frequency, spend & recency affinity matrix (4,151 rows)
├── operational_catalogue.csv          # Real-time stock, margins, lead times & supply constraints (52 rows)
├── policy_rules.csv                   # Deterministic business rules for inventory/margin filtering (7 rows)
└── README.md                          # Directory guide
```

---

## 2. Table Summary & Schema Quick-Reference

| File | Rows | Columns | Primary Key | Foreign Keys / Cross References |
| :--- | :---: | :---: | :--- | :--- |
| `customers.csv` | 500 | 12 | `customer_id` | — |
| `products.csv` | 52 | 10 | `product_id` | — |
| `transactions.csv` | 7,466 | 10 | `(transaction_id, product_id)` | `customer_id` $\rightarrow$ `customers`, `product_id` $\rightarrow$ `products` |
| `baskets.csv` | 7,466 | 5 | `(basket_id, product_id)` | `transaction_id` $\rightarrow$ `transactions`, `customer_id` $\rightarrow$ `customers` |
| `customer_product_interactions.csv` | 4,151 | 9 | `(customer_id, product_id)` | `customer_id` $\rightarrow$ `customers`, `product_id` $\rightarrow$ `products` |
| `operational_catalogue.csv` | 52 | 18 | `product_id` | `product_id` $\rightarrow$ `products` (1-to-1) |
| `policy_rules.csv` | 7 | 9 | `rule_id` | Evaluated across `operational_catalogue` |

---

## 3. Deliberate Test Cases for Constraint Verification

- **Fully Feasible Item:** `PROD_0001` (Headphones: Stock 320, Margin 45%, Reward Eligible) $\rightarrow$ **PASS**
- **Out of Stock Item:** `PROD_0002` (Speaker: Stock = 0) $\rightarrow$ **EXCLUDE** (`insufficient_inventory`)
- **Unknown Stock Item:** `PROD_0003` (Earbuds: Stock = `NaN`) $\rightarrow$ **EXCLUDE** (`unknown_inventory`)
- **Low Stock Item:** `PROD_0004` (Headphones: Stock = 3 $\le$ Reorder 20) $\rightarrow$ **FLAG / LOW STOCK**
- **Reward Ineligible Item:** `PROD_0007` (Charger: `reward_eligible = False`) $\rightarrow$ **EXCLUDE** on reward context
- **Low Margin Item:** `PROD_0036` (Bamboo Desktop Cable & Device Organizer: Margin 5.0% $< 10\%$) $\rightarrow$ **EXCLUDE** (`low_margin`)
- **Discontinued Item:** `PROD_0044` (Legacy 30-Pin Charging Cable Vintage: `discontinued`, Stock 420) $\rightarrow$ **EXCLUDE** (`discontinued_product`)

---

## 4. Documentation

Detailed architectural relationships, generation mechanics, and foreign key verification are documented in:
👉 [`docs/synthetic_data_plan.md`](file:///f:/Next-Best-Offer-and-Product-Recommendation-with-Supply-Constraints/docs/synthetic_data_plan.md)
