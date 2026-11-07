from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from backend.app.api.routes import recommendations
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.recommendation.decision_module import DecisionModule


def _successful_decision(customer_id, top_k, **_):
    return {
        "status": "NO_CANDIDATES",
        "customer_id": customer_id,
        "candidate_count": 0,
        "feasible_count": 0,
        "excluded_count": 0,
        "recommendations": [],
        "excluded_candidates": [],
        "message": f"No candidate products found for customer {customer_id}.",
    }


def test_decision_module_accepts_session_and_validates_existing_customer():
    customer = object()
    session = Mock()
    session.query.return_value.filter.return_value.first.return_value = customer
    module = DecisionModule(session=session)

    module._validate_customer_exists("CUST_TEST")

    session.query.assert_called_once()


def test_decision_module_passes_session_to_recommendation_model():
    session = Mock()

    module = DecisionModule(session=session)

    assert module.recommender.session is session


def test_decision_module_missing_customer_preserves_exact_error():
    session = Mock()
    session.query.return_value.filter.return_value.first.return_value = None
    module = DecisionModule(session=session)

    with pytest.raises(ValueError, match=r"^Customer not found: CUST_MISSING$"):
        module._validate_customer_exists("CUST_MISSING")


def test_decision_module_database_failure_preserves_runtime_error_translation():
    session = Mock()
    session.query.side_effect = SQLAlchemyError("database unavailable")
    module = DecisionModule(session=session)

    with pytest.raises(
        RuntimeError,
        match=r"^Database query error while checking customer CUST_TEST:",
    ):
        module._validate_customer_exists("CUST_TEST")


def test_route_creates_fresh_module_with_shared_session_and_closes_each_session(monkeypatch):
    sessions = []
    modules = []

    def override_get_db():
        session = Mock()
        sessions.append(session)
        try:
            yield session
        finally:
            session.close()

    class FakeDecisionModule:
        def __init__(self, *, session):
            modules.append((self, session))

        def decide(self, **kwargs):
            return _successful_decision(**kwargs)

    monkeypatch.setattr(recommendations, "DecisionModule", FakeDecisionModule)
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            first = client.post(
                "/api/v1/recommend",
                json={"customer_id": "CUST_TEST", "top_k": 1},
            )
            second = client.post(
                "/api/v1/recommend",
                json={"customer_id": "CUST_TEST", "top_k": 1},
            )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(modules) == 2
    assert modules[0][1] is sessions[0]
    assert modules[1][1] is sessions[1]
    assert modules[0][0] is not modules[1][0]
    assert sessions[0].close.call_count == 1
    assert sessions[1].close.call_count == 1


def test_route_closes_session_when_decision_fails(monkeypatch):
    session = Mock()

    def override_get_db():
        try:
            yield session
        finally:
            session.close()

    class FailingDecisionModule:
        def __init__(self, *, session: object):
            assert session is not None

        def decide(self, **_):
            raise RuntimeError("decision failed")

    monkeypatch.setattr(recommendations, "DecisionModule", FailingDecisionModule)
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/recommend",
                json={"customer_id": "CUST_TEST", "top_k": 1},
            )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 500
    assert session.close.call_count == 1
