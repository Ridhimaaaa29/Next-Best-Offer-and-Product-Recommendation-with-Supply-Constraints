# Dataset Notes & Assumptions
## Next-Best-Offer and Product Recommendation with Supply Constraints

### 1. Data Ecosystem Overview
The project operates primarily on a synthetic retail ecosystem created to mirror real-world e-commerce dynamics with known supply constraints and customer behaviors. The authoritative database is **Neon PostgreSQL** consisting of 7 normalized relational tables.

### 2. Relational Schema Summary (7 Tables)

1. **`customers`** (300 rows):
   - Demographics, membership tiers (`Standard`, `Silver`, `Gold`, `Platinum`), reward points, preferred category, and lifetime historical spend.
2. **`products`** (52 rows):
   - Master catalog: `product_id`, `product_name`, `category`, `subcategory`, `brand`, `unit_price`, `product_rating`, `product_popularity`, and `product_status` (`active`, `discontinued`).
3. **`operational_catalogue`** (52 rows):
   - Operational supply attributes: `available_stock`, `inventory_status`, `gross_margin_pct`, `shipping_days`, `reward_eligible`, and `promotion_eligible`.
4. **`baskets`** (2,500 rows):
   - Basket headers with `customer_id`, timestamp, order channel, and payment type.
5. **`transactions`** (6,211 rows):
   - Line-item order details: `basket_id`, `product_id`, `quantity`, `unit_price`, `total_amount`, and timestamp.
6. **`customer_product_interactions`** (2,100 rows):
   - Aggregated customer-product interaction history, recency scores, purchase frequencies, and category preference scores.
7. **`policy_rules`** (6 rows):
   - Formal specification of deterministic business and operational constraints.

### 3. Key Assumptions & Constraints
* **Known Stock**: Products with `available_stock <= 0` or `available_stock IS NULL` are strictly excluded from recommendation.
* **Minimum Margin**: Products with `gross_margin_pct < 0.10` (10%) are excluded to protect profitability.
* **Negative Sampling**: For ML propensity training, negative pairs are sampled at a reproducible 3:1 ratio from unseen products during the observation window.
