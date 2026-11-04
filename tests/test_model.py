from __future__ import annotations

from backend.app.services.model_service import get_model_service


def test_model_artifacts_and_metrics():
    service = get_model_service()
    assert service.model is not None
    assert service.metrics["xgboost"]["mae"] > 0
    assert service.metrics["xgboost"]["r2"] > 0.8


def test_model_is_deterministic():
    service = get_model_service()
    payload = {
        "zipcode": "98052",
        "sqft_living": 2000,
        "sqft_lot": 7200,
        "bedrooms": 3,
        "bathrooms": 2,
        "floors": 1,
        "condition": 3,
        "grade": 7,
        "yr_built": 1985,
        "yr_renovated": 0,
        "waterfront": 0,
        "view": 0,
        "sqft_basement": 0,
        "asking_price": None,
    }
    from backend.app.schemas.requests import ValuationRequest
    request = ValuationRequest(**payload)
    first = service.analyze(request)["estimate"]["value"]
    second = service.analyze(request)["estimate"]["value"]
    assert first == second
