"""Data cockpit and research endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..services.model_service import get_model_service
from .deps import read_json

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
def dashboard() -> dict:
    return read_json("dashboard.json")


@router.get("/research")
def research() -> dict:
    king = read_json("king_county_metrics.json")
    uci = read_json("uci_metrics.json")
    california = read_json("california_metrics.json")
    summary = read_json("training_summary.json")
    generalization = read_json("generalization.json")
    evaluation = read_json("evaluation.json")
    shap = read_json("global_shap.json")
    return {
        "king_county": {
            "dataset": king["dataset"],
            "rows": king["rows_clean"],
            "period": {"start": "2014-05", "end": "2015-05"},
            "split": king["split"],
            "models": king["models"],
            "best_model": king["best_model"],
            "best_model_label": king["best_model_label"],
            "baseline_lift_pct": king["baseline_lift_pct"],
            "interval": king["models"]["xgboost"]["interval"],
        },
        "uci": uci,
        "california": california,
        "generalization": generalization,
        "evaluation": evaluation,
        "shap": {"ranking": shap["ranking"], "method": shap["method"], "base_value_usd": shap["base_value_usd"]},
        "summary": summary,
        "disclaimer": "三个数据集地区、年代、币种与目标定义不同，禁止横向比较绝对误差。",
    }


@router.get("/market/{zipcode}")
def market(zipcode: str) -> dict:
    try:
        return get_model_service().market_for_zip(zipcode)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="该邮编不在金县训练样本中") from exc
