"""
Pytest configuration and fixtures for API testing
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.config import settings


@pytest.fixture(scope="session")
def client():
    """Provides a TestClient connected to the FastAPI app."""
    with TestClient(app) as c:
        yield c
