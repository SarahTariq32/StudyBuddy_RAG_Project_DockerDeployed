import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    """
    Shared TestClient for all API tests.
    """
    with TestClient(app) as client:
        yield client