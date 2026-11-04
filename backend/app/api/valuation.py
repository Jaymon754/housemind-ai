"""Valuation and explanation endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas.requests import ValuationRequest
from ..services.model_service import get_model_service

router = APIRouter(prefix="/valuation", tags=["valuation"])


@router.post("/analyze")
def analyze(payload: ValuationRequest) -> dict:
    try:
        return get_model_service().analyze(payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"估值分析失败：{type(exc).__name__}") from exc


@router.post("/predict")
def predict(payload: ValuationRequest) -> dict:
    try:
        return get_model_service().quick_predict(payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"预测失败：{type(exc).__name__}") from exc


@router.post("/explain")
def explain(payload: ValuationRequest) -> dict:
    try:
        result = get_model_service().analyze(payload)
        return {
            "estimate": result["estimate"],
            "explanation": result["explanation"],
            "confidence": result["confidence"],
            "model": result["model"],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"解释生成失败：{type(exc).__name__}") from exc
