"""Shared test fixtures. The app is started once because model/RAG loading is expensive."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

# Tests must be deterministic and offline: never call paid DeepSeek / Qwen
# endpoints just because the developer's local .env contains a key.
os.environ["DEEPSEEK_API_KEY"] = ""
os.environ["VISION_API_KEY"] = ""

from backend.main import app  # noqa: E402


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
