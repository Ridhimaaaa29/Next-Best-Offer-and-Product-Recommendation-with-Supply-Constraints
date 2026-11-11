# Synthetic Data Architecture & Ecosystem Documentation
## Next-Best-Offer and Product Recommendation with Supply Constraints

### 1. Architectural Overview & Design Philosophy

The synthetic data layer in `data/synthetic/` constitutes a **100% self-contained, internally coherent e-commerce and supply-chain simulation environment**. 

> [!IMPORTANT]
> **Why External Datasets are Reference-Only:**
> Real-world transaction benchmarks (such as UCI Online Retail or Olist) lack verified operational constraints—they do not provide real-time warehouse inventory counts, item-level supplier replenishment lead times, exact gross margin structures, or reward point redemption policies. To prevent unverified joins, identifier mismatches, or target leakage, the entire Next-Best-Offer MVP runs cleanly on this unified synthetic foundation.

```
customers
   │ (1:N)
   ▼
transactions ──(1:1)──► baskets
   │
   ▼
customer_product_interactions
   │
   ▼ [Recommendation Engine Candidates]
   │
products ◄──(1:1)──► operational_catalogue ◄── policy_rules
   │                                                 │
   └──────────────► Deterministic Policy Filter ◄────┘
                           │
                           ▼ [Feasible Candidate Offers]
                    Weighted Multi-Objective Decision Engine
                           │
                           ▼
                    Next-Best-Offer Actionable Output
```

---

### 2. Dataset Specifications & Schemas

#### 2.1 `customers.csv` (500 rows, 12 columns)
- **Primary Key:** `customer_id`
- **Purpose:** Represents individual registered shoppers with distinct behavioral archetypes, purchasing power, and loyalty tiers.
- **Attributes:**
  - `customer_id` (PK, string): Formatted as `CUST_0001` to `CUST_0500`.
  - `customer_segment` (string): Archetypes (`High-Value Enthusiast`, `Tech & Gadget Aficionado`, `Health & Wellness Regular`, `Casual Budget Shopper`, `Occasional Gifter`).
  - `age_group` (string): `18-24`, `25-34`, `35-44`, `45-54`, `55+`.
  - `location` (string): Standard metro locations (`New York, NY`, `Austin, TX`, `Seattle, WA`, etc.).
  - `membership_tier` (string): Loyalty tier (`Bronze`, `Silver`, `Gold`, `Platinum`).
  - `reward_points` (integer): Accumulated points balance ($0$ to $15,000$).
  - `preferred_category` (string): Primary department preference driving affinity models.
  - `average_order_value` (numeric): Derived average spend per checkout order.
  - `total_orders` (integer): Cumulative historical order count ($1$ to $20$).
  - `total_spend` (numeric): Lifetime customer gross monetary spend.
  - `last_purchase_date` (timestamp): Most recent order date.
  - `customer_status` (string): `active` or `dormant`.

#### 2.2 `products.csv` (52 rows, 10 columns)
- **Primary Key:** `product_id`
- **Purpose:** Synthetic merchandise master catalogue spanning 5 curated departments and 12 distinct subcategories.
- **Attributes:**
  - `product_id` (PK, string): Formatted as `PROD_0001` to `PROD_0052`.
  - `product_name` (string): Realistic commercial title (e.g., `Italian Espresso Machine Compact`).
  - `category` (string): High-level category (`Electronics`, `Coffee & Kitchen`, `Health & Fitness`, `Home & Living`, `Beauty & Skincare`).
  - `subcategory` (string): Granular grouping (`Brewing`, `Audio`, `Skincare`, `Equipment`, etc.).
  - `brand` (string): Coherent synthetic brand identity (`BaristaCraft`, `AudioMax`, `ZenFit`, `GlowLab`).
  - `unit_price` (numeric): Retail selling price ($8.99 to $1,899.99).
  - `unit_cost` (numeric): Manufacturing / wholesale acquisition cost.
  - `product_rating` (numeric): Customer satisfaction score ($3.8$ to $4.9$).
  - `product_popularity` (numeric): Base popularity frequency weight ($0.20$ to $0.96$).
  - `product_status` (string): Operational lifecycle state (`active`, `discontinued`).

#### 2.3 `transactions.csv` (7,466 rows, 10 columns)
- **Primary Key:** `(transaction_id, product_id)`
- **Foreign Keys:** `customer_id` $\rightarrow$ `customers.customer_id`, `product_id` $\rightarrow$ `products.product_id`
- **Purpose:** Chronological line-item log of historical consumer checkouts across a 22-month timeline (Jan 2025 to Oct 2026).
- **Attributes:**
  - `transaction_id` (string): Unique checkout invoice identifier (`TXN_000001` to `TXN_003655`).
  - `customer_id` (FK, string): Purchasing customer ID.
  - `transaction_date` (timestamp): Exact checkout timestamp.
  - `product_id` (FK, string): Purchased product SKU.
  - `quantity` (integer): Item units ordered.
  - `unit_price` (numeric): Applicable base unit price at checkout.
  - `discount_pct` (numeric): Member tier discount applied ($0.05$ to $0.15$).
  - `final_amount` (numeric): Net line transaction total.
  - `payment_method` (string): `credit_card`, `apple_pay`, `rewards_points`, `debit_card`.
  - `order_status` (string): `completed` (97%) or `returned` (3%).

#### 2.4 `baskets.csv` (7,466 rows, 5 columns)
- **Primary Key:** `(basket_id, product_id)`
- **Foreign Keys:** `transaction_id` $\rightarrow$ `transactions.transaction_id`, `product_id` $\rightarrow$ `products.product_id`, `customer_id` $\rightarrow$ `customers.customer_id`
- **Purpose:** Basket-level market basket container designed specifically for Association Rule Mining (Apriori, FP-Growth, support, confidence, lift) and co-purchase analysis.
- **Attributes:**
  - `basket_id` (string): Co-purchase container identifier (`BSK_000001` to `BSK_003655`).
  - `transaction_id` (FK, string): Linked checkout order.
  - `customer_id` (FK, string): Linked customer.
  - `product_id` (FK, string): Item co-occurring in the basket.
  - `quantity` (integer): Units in basket.

#### 2.5 `customer_product_interactions.csv` (4,151 rows, 9 columns)
- **Primary Key:** `(customer_id, product_id)`
- **Foreign Keys:** `customer_id` $\rightarrow$ `customers.customer_id`, `product_id` $\rightarrow$ `products.product_id`
- **Purpose:** Aggregated behavioral matrix for collaborative filtering, affinity scoring, and repeat-exclusion ranking.
- **Attributes:**
  - `customer_id` (PK, FK, string)
  - `product_id` (PK, FK, string)
  - `interaction_count` (integer): Number of completed purchases.
  - `last_interaction_date` (timestamp): Timestamp of most recent interaction.
  - `purchase_frequency` (integer): Completed purchase frequency.
  - `total_quantity` (integer): Total units accumulated.
  - `total_spend` (numeric): Total spend accumulated for this SKU.
  - `category_preference_score` (numeric): High ($0.90$) if matching customer's preferred category, standard ($0.45$) otherwise.
  - `recency_score` (numeric): Time-decay score $\exp(-\Delta days / 120)$, bounding recency in $[0, 1]$.

#### 2.6 `operational_catalogue.csv` (52 rows, 18 columns)
- **Primary Key:** `product_id`
- **Foreign Key:** `product_id` $\rightarrow$ `products.product_id` (1:1 correspondence)
- **Purpose:** Real-time warehouse and operations snapshot supplying supply facts to the policy engine.
- **Attributes:**
  - `product_id` (PK, string)
  - `available_stock` (numeric): Warehouse physical inventory count. Includes **0.0** (out of stock) and **NaN** (unknown stock).
  - `inventory_status` (string): `available`, `low_stock`, `out_of_stock`, `unknown`.
  - `reorder_point` (integer): Reorder trigger point ($10, 20, 30$).
  - `unit_price` (numeric): Selling price.
  - `unit_cost` (numeric): Operational cost.
  - `gross_margin_pct` (numeric): Percentage profit margin: $(price - cost) / price$.
  - `supplier_id` (string): Vendor identifier (`SUPP_001` to `SUPP_008`).
  - `supplier_lead_days` (integer): Replenishment delivery lead time ($2$ to $21$ days).
  - `warehouse_id` (string): Fulfilling fulfillment center (`WH_EAST_01`, `WH_WEST_02`, etc.).
  - `fulfilment_class` (string): `Standard`, `Express`, `Heavy/Bulky`, `Fragile`.
  - `shipping_days` (integer): Expected standard transit time ($1$ to $10$ days).
  - `reward_eligible` (boolean): Flag for reward offers.
  - `max_discount_pct` (numeric): Maximum allowable promotional concession.
  - `promotion_eligible` (boolean): General promotional status.
  - `data_source` (string): Provenance tracking tag (`synthetic_operational_engine_v1`).
  - `last_updated_at` (timestamp): Freshness timestamp.
  - `data_freshness_status` (string): `verified_fresh`.

#### 2.7 `policy_rules.csv` (6 rows, 9 columns)
- **Primary Key:** `rule_id`
- **Purpose:** Configurable deterministic business rules evaluated by the policy engine to prune infeasible candidate products.
- **Attributes:**
  - `rule_id` (PK, string)
  - `rule_name` (string): Business rule title.
  - `rule_type` (string): `inventory`, `margin`, `reward_eligibility`, `fulfilment`, `promotional`.
  - `threshold` (string): Configured boundary value.
  - `operator` (string): Comparison operator (`>`, `IS_NOT_NULL`, `>=`, `==`, `<=`).
  - `action` (string): Enforcement action (`EXCLUDE`, `FLAG_OR_EXCLUDE_EXPRESS`).
  - `priority` (integer): Rule execution order ($1$ to $5$).
  - `enabled` (boolean): Active state toggle.
  - `description` (text): Commercial rationale and compliance mandate.

---

### 3. Intentional Behavioral Patterns Generated

1. **Category Affinity Skew**:
   - Customers belonging to the `Tech & Gadget Aficionado` segment generate orders heavily concentrated in `Electronics` (Audio, Accessories, Wearables).
   - Customers in `Health & Wellness Regular` skew towards `Health & Fitness` (Equipment, Supplements).
2. **Complementary Market Basket Bundles**:
   - The generator explicitly injects high co-purchase frequencies for natural bundles:
     - *Coffee Connoisseur:* Espresso Machine (`PROD_0012`) + Burr Grinder (`PROD_0013`) + Coffee Beans (`PROD_0016`) + Filters (`PROD_0018`).
     - *Personal Audio:* Noise-Cancelling Headphones (`PROD_0001`) + USB-C Cable (`PROD_0005`) + Case (`PROD_0008`).
     - *Fitness Core:* Yoga Mat (`PROD_0023`) + Resistance Bands (`PROD_0025`) + Shaker Bottle (`PROD_0029`).
     - *Supplement Routine:* Whey Protein Powder (`PROD_0030`) + Shaker Bottle (`PROD_0032`).
3. **Monetary Value Skews**:
   - `High-Value Enthusiast` members make between 8 and 20 orders with average order values $> \$250$.
   - `Casual Budget Shoppers` make 2 to 6 orders with lower basket sizes.

---

### 4. Deliberate Operational Edge Cases (Hard Constraint Verification)

To prove that **the recommendation engine generates candidates, but the policy engine enforces mandatory constraints**, the operational catalogue contains deterministic edge cases:

| Product ID | Product Name | Condition Configured | Expected Policy Engine Action |
| :--- | :--- | :--- | :--- |
| `PROD_0001` | Noise-Cancelling Headphones | Stock = 320, Margin = 45%, Reward = True | **PASSED (Feasible)** — Valid for Next-Best-Offer |
| `PROD_0002` | Bluetooth Pocket Speaker | Stock = 0.0 (`out_of_stock`) | **EXCLUDED** (Reason: `Known inventory is insufficient`) |
| `PROD_0003` | True Wireless Earbuds | Stock = `NaN` (`unknown`) | **EXCLUDED** (Reason: `Inventory status is unknown / unverified`) |
| `PROD_0004` | Studio Monitor Headphones | Stock = 3.0, Reorder = 20 | **FLAGGED / EXPEDITED** (Low stock alert) |
| `PROD_0007` | 65W GaN Wall Charger | `reward_eligible = False` | **EXCLUDED** from reward redemption campaigns |
| `PROD_0013` | Burr Coffee Grinder | Stock = 0.0 | **EXCLUDED** (Tests cross-sell bundle breakage when partner item is OOS) |
| `PROD_0036` | Gold Wireless Headphones | Margin = 5.0% ($< 10\%$) | **EXCLUDED** (Reason: `Gross margin below minimum threshold (10%)`) |
| `PROD_0037` | Legacy 30-Pin Cable | `discontinued`, Stock = 0 | **EXCLUDED** (Discontinued product lifecycle) |
| `PROD_0038` | Commercial Espresso Bar | Bulky, Shipping Days = 10 | **FLAGGED** (Violates express shipping SLA $\le 7$ days) |

---

### 5. Automated Validation & Integrity Results

All 7 synthetic tables were validated with strict relational checks:
- **Customer Integrity:** 100% of transaction `customer_id` values exist in `customers.csv`.
- **Product Integrity:** 100% of transaction `product_id` values exist in `products.csv`.
- **Basket Consistency:** 100% of basket line items match valid transactions.
- **Catalogue Coverage:** `operational_catalogue.csv` achieves 100% 1-to-1 parity with `products.csv` (52 of 52 SKUs).
- **Behavioral Consistency:** All interaction records correspond to valid active customers and SKUs.
