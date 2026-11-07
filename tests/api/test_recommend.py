"""
API Tests for Recommendation Endpoint (/api/v1/recommend)
Verifies:
1. Valid recommendation request returns 200 and valid schema
2. Policy feasibility invariant (every rec has policy_decision == 'PASS')
3. Known excluded products (PROD_0002 out of stock, PROD_0036 low margin) never appear in recommendations
4. Reward context exclusion (PROD_0007 excluded when reward_context=True)
5. Non-existent customer returns 404
6. Invalid request body returns 422
7. Top-k bounds validation
"""


def test_valid_recommendation_request(client):
    payload = {
        "customer_id": "CUST_0001",
        "top_k": 5,
        "reward_context": False,
        "promotion_context": False,
        "express_context": False,
        "include_excluded": True,
    }
    response = client.post("/api/v1/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["customer_id"] == "CUST_0001"
    assert data["status"] in ["SUCCESS", "ALL_CANDIDATES_EXCLUDED"]
    assert "recommendations" in data
    assert len(data["recommendations"]) <= 5

    # Invariant: Every recommended product MUST be PASS
    for rec in data["recommendations"]:
        assert rec["policy_decision"] == "PASS"
        assert len(rec["policy_reasons"]) == 0
        assert "score_breakdown" in rec


def test_known_infeasible_products_never_recommended(client):
    """
    PROD_0002 is out-of-stock.
    PROD_0036 has gross margin < 10%.
    PROD_0044 is discontinued.
    None of these must ever appear in recommendations.
    """
    payload = {
        "customer_id": "CUST_0001",
        "top_k": 20,
    }
    response = client.post("/api/v1/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()
    rec_ids = [r["product_id"] for r in data["recommendations"]]
    assert "PROD_0002" not in rec_ids
    assert "PROD_0036" not in rec_ids
    assert "PROD_0044" not in rec_ids


def test_reward_context_enforcement(client):
    """
    PROD_0007 (Wall Charger) is reward_eligible = False.
    With reward_context=True, PROD_0007 must never appear in final recommendations.
    """
    payload = {
        "customer_id": "CUST_0001",
        "top_k": 20,
        "reward_context": True,
    }
    response = client.post("/api/v1/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()
    rec_ids = [r["product_id"] for r in data["recommendations"]]
    assert "PROD_0007" not in rec_ids


def test_unknown_customer_returns_404(client):
    payload = {
        "customer_id": "CUST_NON_EXISTENT_99999",
        "top_k": 5,
    }
    response = client.post("/api/v1/recommend", json=payload)
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


def test_invalid_top_k_returns_422(client):
    payload = {
        "customer_id": "CUST_0001",
        "top_k": 0,  # Invalid: ge=1
    }
    response = client.post("/api/v1/recommend", json=payload)
    assert response.status_code == 422


def test_extra_forbidden_fields_returns_422(client):
    payload = {
        "customer_id": "CUST_0001",
        "top_k": 5,
        "unauthorized_field": "hack",
    }
    response = client.post("/api/v1/recommend", json=payload)
    assert response.status_code == 422
