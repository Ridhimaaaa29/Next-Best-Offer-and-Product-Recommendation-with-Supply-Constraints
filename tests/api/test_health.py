"""
API Tests for Health Endpoint
"""


def test_health_endpoint_root(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "app_version" in data
    assert "database_connected" in data
    assert "ml_model_loaded" in data


def test_health_endpoint_v1(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["database_connected"] is True
    assert data["ml_model_loaded"] is True
