"""Rental underwriting endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas.requests import InvestmentRequest, ScenarioRequest
from ..services.investment_service import scenario_analysis, underwrite
from ..services.model_service import get_model_service

router = APIRouter(prefix="/investment", tags=["investment"])


@router.post("/calculate")
def calculate(payload: InvestmentRequest) -> dict:
    try:
        return underwrite(payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"投资测算失败：{type(exc).__name__}") from exc


@router.post("/scenarios")
def scenarios(payload: ScenarioRequest) -> dict:
    try:
        return scenario_analysis(payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"情景分析失败：{type(exc).__name__}") from exc


@router.get("/presets")
def presets() -> dict:
    service = get_model_service()
    definitions = [
        ("西雅图北区 · 联排", "98115", 25, 6.5),
        ("东区 · 独栋", "98052", 30, 6.25),
        ("南金县 · 现金流", "98056", 25, 6.75),
    ]
    presets = []
    for label, zipcode, down, rate in definitions:
        stats = service.zip_stats.get(zipcode)
        if not stats:
            continue
        price = int(stats["median_price"])
        rent = round(price * 0.0052 / 50) * 50
        presets.append(
            {
                "label": label,
                "zipcode": zipcode,
                "region": stats.get("region"),
                "purchase_price": price,
                "monthly_rent": rent,
                "down_payment_pct": down,
                "interest_rate": rate,
                "note": "以该邮编样本中位价和 0.52% 月租演示假设生成，可在表单中修改。",
            }
        )
    return {"presets": presets, "defaults": InvestmentRequest().model_dump()}
