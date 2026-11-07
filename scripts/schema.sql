-- ============================================================
-- Next-Best-Offer & Product Recommendation
-- Core Synthetic MVP Database Schema
-- PostgreSQL / Neon
-- ============================================================

-- ------------------------------------------------------------
-- 1. CUSTOMERS
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    customer_segment VARCHAR(100) NOT NULL,
    age_group VARCHAR(50) NOT NULL,
    location VARCHAR(100) NOT NULL,
    membership_tier VARCHAR(50) NOT NULL,
    reward_points INTEGER NOT NULL,
    preferred_category VARCHAR(100) NOT NULL,
    customer_status VARCHAR(50) NOT NULL,
    total_orders INTEGER NOT NULL,
    total_spend NUMERIC(12, 2) NOT NULL,
    last_purchase_date DATE NOT NULL,
    average_order_value NUMERIC(12, 2) NOT NULL
);


-- ------------------------------------------------------------
-- 2. PRODUCTS
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS products (
    product_id VARCHAR(50) PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    subcategory VARCHAR(100) NOT NULL,
    brand VARCHAR(100) NOT NULL,
    unit_price NUMERIC(12, 2) NOT NULL,
    unit_cost NUMERIC(12, 2) NOT NULL,
    product_rating NUMERIC(4, 2) NOT NULL,
    product_popularity NUMERIC(8, 4) NOT NULL,
    product_status VARCHAR(50) NOT NULL
);


-- ------------------------------------------------------------
-- 3. TRANSACTIONS
-- One transaction can contain multiple products.
-- Therefore the PK is (transaction_id, product_id).
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id VARCHAR(50) NOT NULL,
    customer_id VARCHAR(50) NOT NULL,
    transaction_date TIMESTAMP NOT NULL,
    product_id VARCHAR(50) NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(12, 2) NOT NULL,
    discount_pct NUMERIC(6, 4) NOT NULL,
    final_amount NUMERIC(12, 2) NOT NULL,
    payment_method VARCHAR(50) NOT NULL,
    order_status VARCHAR(50) NOT NULL,

    PRIMARY KEY (transaction_id, product_id),

    FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id),

    FOREIGN KEY (product_id)
        REFERENCES products(product_id)
);


-- ------------------------------------------------------------
-- 4. BASKETS
-- One basket can contain multiple products.
-- Therefore the PK is (basket_id, product_id).
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS baskets (
    basket_id VARCHAR(50) NOT NULL,
    transaction_id VARCHAR(50) NOT NULL,
    customer_id VARCHAR(50) NOT NULL,
    product_id VARCHAR(50) NOT NULL,
    quantity INTEGER NOT NULL,

    PRIMARY KEY (basket_id, product_id),

    FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id),

    FOREIGN KEY (product_id)
        REFERENCES products(product_id)
);


-- ------------------------------------------------------------
-- 5. CUSTOMER-PRODUCT INTERACTIONS
-- One row per customer-product pair.
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS customer_product_interactions (
    customer_id VARCHAR(50) NOT NULL,
    product_id VARCHAR(50) NOT NULL,
    interaction_count INTEGER NOT NULL,
    last_interaction_date TIMESTAMP NOT NULL,
    purchase_frequency INTEGER NOT NULL,
    total_quantity INTEGER NOT NULL,
    total_spend NUMERIC(12, 2) NOT NULL,
    category_preference_score NUMERIC(8, 4) NOT NULL,
    recency_score NUMERIC(8, 4) NOT NULL,

    PRIMARY KEY (customer_id, product_id),

    FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id),

    FOREIGN KEY (product_id)
        REFERENCES products(product_id)
);


-- ------------------------------------------------------------
-- 6. OPERATIONAL CATALOGUE
-- Product-level operational and business constraints.
--
-- available_stock is intentionally nullable:
--   0    = known out of stock
--   NULL = inventory unknown
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS operational_catalogue (
    product_id VARCHAR(50) PRIMARY KEY,
    available_stock NUMERIC(12, 2),
    inventory_status VARCHAR(50) NOT NULL,
    reorder_point INTEGER NOT NULL,
    unit_price NUMERIC(12, 2) NOT NULL,
    unit_cost NUMERIC(12, 2) NOT NULL,
    gross_margin_pct NUMERIC(6, 4) NOT NULL,
    supplier_id VARCHAR(50) NOT NULL,
    supplier_lead_days INTEGER NOT NULL,
    warehouse_id VARCHAR(50) NOT NULL,
    fulfilment_class VARCHAR(50) NOT NULL,
    shipping_days INTEGER NOT NULL,
    reward_eligible BOOLEAN NOT NULL,
    max_discount_pct NUMERIC(6, 4) NOT NULL,
    promotion_eligible BOOLEAN NOT NULL,
    data_source VARCHAR(100) NOT NULL,
    last_updated_at TIMESTAMP NOT NULL,
    data_freshness_status VARCHAR(50) NOT NULL,

    FOREIGN KEY (product_id)
        REFERENCES products(product_id)
);


-- ------------------------------------------------------------
-- 7. POLICY RULES
-- Deterministic business-policy configuration.
-- threshold remains TEXT because the source CSV contains
-- different rule value types and NULL thresholds.
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS policy_rules (
    rule_id VARCHAR(50) PRIMARY KEY,
    rule_name VARCHAR(255) NOT NULL,
    rule_type VARCHAR(100) NOT NULL,
    threshold TEXT,
    operator VARCHAR(50) NOT NULL,
    action VARCHAR(100) NOT NULL,
    priority INTEGER NOT NULL,
    enabled BOOLEAN NOT NULL,
    description TEXT NOT NULL
);