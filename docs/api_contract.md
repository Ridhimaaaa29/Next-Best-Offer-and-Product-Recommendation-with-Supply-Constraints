# API Contract Specification
## Next-Best-Offer and Product Recommendation with Supply Constraints

### Base URL
`/api/v1`

---

### Endpoints

#### 1. Service Health Check
* **Path**: `GET /health` (or `GET /api/v1/health`)
* **Response `200 OK`**:
```json
{
  "status": "healthy",
  "app_version": "1.0.0",
  "database_connected": true,
  "ml_model_loaded": true,
  "ml_model_name": "Gradient Boosting Classifier"
}
```

---

#### 2. Generate Next-Best-Offer Recommendations
* **Path**: `POST /api/v1/recommend`
* **Request Headers**: `Content-Type: application/json`
* **Request Body**:
```json
{
  "customer_id": "CUST_0001",
  "top_k": 5,
  "reward_context": false,
  "promotion_context": false,
  "express_context": false,
  "include_excluded": true
}
```
* **Validation Rules**:
  - `customer_id`: Required string (length 1–50). Unknown customers return `404 Not Found`.
  - `top_k`: Integer between 1 and 50 (default: 5).
  - Extra unknown fields return `422 Unprocessable Content`.

* **Response `200 OK`**:
```json
{
  "status": "SUCCESS",
  "customer_id": "CUST_0001",
  "candidate_count": 20,
  "feasible_count": 18,
  "excluded_count": 2,
  "recommendations": [
    {
      "product_id": "PROD_0012",
      "product_name": "Wireless Noise-Canceling Headphones",
      "category": "Electronics",
      "subcategory": "Audio",
      "brand": "SonicWave",
      "unit_price": 149.99,
      "product_rating": 4.8,
      "product_popularity": 0.92,
      "product_status": "active",
      "recommendation_score": 0.8842,
      "policy_decision": "PASS",
      "policy_reasons": [],
      "score_breakdown": {
        "category_affinity_score": 0.90,
        "popularity_score": 0.92,
        "rating_score": 0.96,
        "interaction_bonus": 0.80,
        "composite_score": 0.8842,
        "reason_codes": [
          "Matches customer preferred category 'Electronics'",
          "Top customer review rating (4.8/5.0)",
          "ML Conversion Propensity: 0.8842 (Gradient Boosting Classifier)"
        ]
      }
    }
  ],
  "excluded_candidates": [
    {
      "product_id": "PROD_0002",
      "product_name": "Smart Fitness Watch",
      "category": "Electronics",
      "recommendation_score": 0.8712,
      "policy_decision": "EXCLUDE",
      "policy_reasons": ["Product is out of stock."]
    }
  ]
}
```
