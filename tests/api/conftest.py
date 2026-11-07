"""
Conftest for tests/api subpackage — imports client fixture from parent.
"""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c
