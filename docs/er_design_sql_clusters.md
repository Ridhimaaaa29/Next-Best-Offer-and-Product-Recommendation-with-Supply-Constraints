# Database Entity-Relationship (ER) Schema & SQL Cluster Design

## Next-Best-Offer (NBO) and Product Recommendation with Supply Constraints

This document defines the Entity-Relationship (ER) design and SQL database
structure for the MVP. The schema is implemented in PostgreSQL using Neon.

The design is based on the project's synthetic MVP data and contains exactly
seven relational tables.

---

## 1. High-Level ER Diagram

```mermaid
erDiagram

    CUSTOMERS ||--o{ TRANSACTIONS : places
    PRODUCTS ||--o{ TRANSACTIONS : contains

    CUSTOMERS ||--o{ BASKETS : owns
    PRODUCTS ||--o{ BASKETS : contains

    CUSTOMERS ||--o{ CUSTOMER_PRODUCT_INTERACTIONS : has
    PRODUCTS ||--o{ CUSTOMER_PRODUCT_INTERACTIONS : tracked_in

    PRODUCTS ||--|| OPERATIONAL_CATALOGUE : has_operational_data

    CUSTOMERS {
        varchar customer_id PK
        varchar customer_segment
        varchar age_group
        varchar location
        varchar membership_tier
        integer reward_points
        varchar preferred_category
        varchar customer_status
        integer total_orders
        numeric total_spend
        date last_purchase_date
        numeric average_order_value
    }

    PRODUCTS {
        varchar product_id PK
        varchar product_name
        varchar category
        varchar subcategory
        varchar brand
        numeric unit_price
        numeric unit_cost
        numeric product_rating
        numeric product_popularity
        varchar product_status
    }

    TRANSACTIONS {
        varchar transaction_id PK
        varchar product_id PK
        varchar customer_id FK
        date transaction_date
        integer quantity
        numeric unit_price
        numeric discount_pct
        numeric final_amount
        varchar payment_method
        varchar order_status
    }

    BASKETS {
        varchar basket_id PK
        varchar product_id PK
        varchar transaction_id
        varchar customer_id FK
        integer quantity
    }

    CUSTOMER_PRODUCT_INTERACTIONS {
        varchar customer_id PK, FK
        varchar product_id PK, FK
        integer interaction_count
        date last_interaction_date
        numeric purchase_frequency
        integer total_quantity
        numeric total_spend
        numeric category_preference_score
        numeric recency_score
    }

    OPERATIONAL_CATALOGUE {
        varchar product_id PK, FK
        numeric available_stock
        varchar inventory_status
        integer reorder_point
        numeric unit_price
        numeric unit_cost
        numeric gross_margin_pct
        varchar supplier_id
        integer supplier_lead_days
        varchar warehouse_id
        varchar fulfilment_class
        integer shipping_days
        boolean reward_eligible
        numeric max_discount_pct
        boolean promotion_eligible
        varchar data_source
        timestamp last_updated_at
        varchar data_freshness_status
    }

    POLICY_RULES {
        varchar rule_id PK
        varchar rule_name
        varchar rule_type
        varchar threshold
        varchar operator
        varchar action
        integer priority
        boolean enabled
        varchar description
    }