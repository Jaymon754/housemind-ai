"""Shared test fixtures. The app is started once because model/RAG loading is expensive."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def valuation_payload() -> dict:
    return {
        "zipcode": "98115",
        "sqft_living": 1840,
        "sqft_lot": 5000,
        "bedrooms": 3,
        "bathrooms": 2,
        "floors": 1,
        "condition": 3,
        "grade": 7,
        "yr_built": 1962,
        "yr_renovated": 0,
        "waterfront": 0,
        "view": 0,
        "sqft_basement": 0,
        "asking_price": 599000,
    }
