"""Valuation, TreeSHAP explanation and comparable-sales service."""
from __future__ import annotations

import math
import sys
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.common import FEATURE_LABELS, build_zip_stats, engineer_features, load_king_county, region_for  # noqa: E402

from ..core.config import settings  # noqa: E402
from ..schemas.requests import ValuationRequest  # noqa: E402

DISPLAY_FEATURES = {
    "waterfront": lambda value: "滨水" if value >= 1 else "非滨水",
    "has_renovated": lambda value: "已翻新" if value >= 1 else "未翻新",
    "view": lambda value: ["无景观", "一般景观", "较好景观", "优质景观", "顶级景观"][int(np.clip(value, 0, 4))],
    "condition": lambda value: ["", "较差", "一般", "平均", "良好", "优秀"][int(np.clip(value, 1, 5))],
    "grade": lambda value: f"{int(value)} 级",
    "sqft_living": lambda value: f"{value:,.0f} sqft",
    "sqft_lot": lambda value: f"{value:,.0f} sqft",
    "house_age": lambda value: f"{value:.0f} 年",
    "zip_market_value": lambda value: f"${value:,.0f}",
    "floors": lambda value: f"{value:g} 层",
    "bedrooms": lambda value: f"{value:.0f} 间",
    "bathrooms": lambda value: f"{value:g} 间",
}


def _rounded(value: float, nearest: int = 1000) -> int:
    return int(round(value / nearest) * nearest)


class ModelService:
    def __init__(self) -> None:
        self.artifact = joblib.load(settings.artifact_dir / "king_county_xgb.joblib")
        self.model = self.artifact["model"]
        self.booster = self.model.get_booster()
        self.features: list[str] = self.artifact["features"]
        self.labels: dict[str, str] = self.artifact["feature_labels"]
        self.interval: dict[str, Any] = self.artifact["interval"]
        self.metrics: dict[str, Any] = self.artifact["metrics"]
        self.zip_stats: dict[str, dict[str, Any]] = self.artifact["zip_stats"]
        meta = __import__("json").loads((settings.artifact_dir / "runtime_meta.json").read_text())
        self.defaults: dict[str, Any] = meta.get("defaults", {})
        self.ranges: dict[str, Any] = meta.get("ranges", {})
        self.sale_period: dict[str, str] = meta.get("sale_period", {})
        self._frame = load_king_county()
        self._frame["zipcode"] = self._frame["zipcode"].astype(str).str.replace(r"\.0$", "", regex=True)
        # Enrich zip metadata with area/lot medians for sensible neighbourhood defaults.
        rich_stats = build_zip_stats(self._frame)
        for zipcode, stats in rich_stats.items():
            subset = self._frame[self._frame["zipcode"] == zipcode]
            if zipcode in self.zip_stats:
                self.zip_stats[zipcode].update(
                    {
                        "median_area": int(subset["sqft_living"].median()),
                        "median_lot": int(subset["sqft_lot"].median()),
                        "median_year": int(subset["yr_built"].median()),
                    }
                )
        self.rich_zip_stats = rich_stats
        self.global_median_price = float(self._frame["price"].median())
        self._zip_options = self._build_zip_options()

    def _build_zip_options(self) -> list[dict[str, Any]]:
        options = []
        for zipcode, stats in sorted(
            self.zip_stats.items(), key=lambda item: item[1].get("median_price", 0), reverse=True
        ):
            options.append(
                {
                    "zipcode": zipcode,
                    "region": region_for(stats.get("lat", 47.56), stats.get("long", -122.28)),
                    "median_price": int(stats.get("median_price", 0)),
                    "count": int(stats.get("count", 0)),
                    "median_ppsf": float(stats.get("median_ppsf", 0)),
                }
            )
        return options

    @property
    def zip_options(self) -> list[dict[str, Any]]:
        return self._zip_options

    def _record(self, request: ValuationRequest) -> dict[str, Any]:
        zipcode = request.zipcode
        stats = self.zip_stats.get(zipcode) or {}
        defaults = self.defaults
        lat = request.lat if request.lat is not None else stats.get("lat", 47.56)
        lon = request.long if request.long is not None else stats.get("long", -122.28)
        year = 2015
        area = float(request.sqft_living)
        basement = float(min(request.sqft_basement, max(area - 300, 0)))
        return {
            "zipcode": zipcode,
            "zip_market_value": stats.get("market_value", self.global_median_price),
            "bedrooms": request.bedrooms,
            "bathrooms": request.bathrooms,
            "sqft_living": area,
            "sqft_lot": request.sqft_lot,
            "floors": request.floors,
            "waterfront": request.waterfront,
            "view": request.view,
            "condition": request.condition,
            "grade": request.grade,
            "sqft_above": max(area - basement, 300),
            "sqft_basement": basement,
            "yr_built": request.yr_built,
            "yr_renovated": request.yr_renovated,
            "lat": lat,
            "long": lon,
            "sqft_living15": stats.get("median_area", defaults.get("sqft_living15", 1840)),
            "sqft_lot15": stats.get("median_lot", defaults.get("sqft_lot15", 7620)),
            "sale_year": year,
        }

    def _matrix(self, records: list[dict[str, Any]]) -> pd.DataFrame:
        frame = engineer_features(pd.DataFrame(records), self.zip_stats)
        return frame[self.features]

    def _raw_predict(self, X: pd.DataFrame) -> np.ndarray:
        # XGBoost 3.x + pandas 3.x can reject DataFrame feature names even when
        # they match the booster; the matrix is already ordered by self.features.
        return np.asarray(self.model.predict(X, validate_features=False), dtype=float)

    def _contributions(self, X: pd.DataFrame) -> tuple[np.ndarray, float]:
        matrix = xgb.DMatrix(X, feature_names=self.features)
        values = self.booster.predict(matrix, pred_contribs=True)
        return values[:, :-1], float(values[0, -1])

    def _warnings(self, request: ValuationRequest) -> list[str]:
        warnings: list[str] = []
        if request.zipcode not in self.zip_stats:
            warnings.append("该邮编不在 King County 训练样本中，已回退到区域经纬度与全局基准价，估值不确定性较高。")
        if request.sqft_living > 6000:
            warnings.append("室内面积超过样本 99% 分位，豪宅段误差通常更大。")
        if request.yr_built < 1920:
            warnings.append("1920 年前建造的房屋在样本中较少，历史保护与结构状况可能未被模型充分捕捉。")
        if request.waterfront:
            warnings.append("滨水属性样本稀少，溢价估计对具体岸线、景观和防洪条件高度敏感。")
        if request.grade >= 11:
            warnings.append("高建筑等级样本有限，定制装修与设计溢价可能超出模型可解释范围。")
        return warnings

    def _confidence(self, predicted: float, request: ValuationRequest, comps: list[dict]) -> dict[str, Any]:
        width_ratio = (self.interval["residual_q90"] - self.interval["residual_q10"]) / max(predicted, 1)
        score = 90.0
        if request.zipcode not in self.zip_stats:
            score -= 14
        score -= min(22, max(0, (width_ratio - 0.28) * 90))
        if len(comps) < 4:
            score -= 7
        if request.sqft_living > 5000 or request.grade >= 11:
            score -= 5
        if request.waterfront:
            score -= 4
        score = int(np.clip(round(score), 45, 92))
        label = "较高" if score >= 82 else "中等" if score >= 68 else "偏低"
        return {
            "score": score,
            "label": label,
            "basis": [
                "80% 区间由 5 折袋外残差分位数校准",
                f"找到 {len(comps)} 套可比成交",
                "输入位于训练分布内" if request.zipcode in self.zip_stats else "邮编超出训练分布",
            ],
        }

    def _comps(self, record: dict[str, Any], limit: int = 6) -> list[dict[str, Any]]:
        frame = self._frame
        area = record["sqft_living"]
        beds = record["bedrooms"]
        baths = record["bathrooms"]
        grade = record["grade"]
        lat, lon = record["lat"], record["long"]
        same_zip = frame[frame["zipcode"] == record["zipcode"]]
        pool = same_zip if len(same_zip) >= limit * 3 else frame
        area_ratio = np.abs(np.log(pool["sqft_living"].clip(lower=1) / max(area, 1)))
        distance = np.sqrt(
            ((pool["lat"] - lat) * 69.0) ** 2
            + ((pool["long"] - lon) * 69.0 * np.cos(np.radians(lat))) ** 2
        )
        score = (
            area_ratio * 0.92
            + np.abs(pool["bedrooms"] - beds) * 0.030
            + np.abs(pool["bathrooms"] - baths) * 0.035
            + np.abs(pool["grade"] - grade) * 0.012
            + np.clip(distance / 18, 0, 1) * 0.16
        )
        score = score - (pool["zipcode"] == record["zipcode"]).astype(float) * 0.06
        candidates = pool.assign(_score=score).nsmallest(limit * 3, "_score")
        candidates = candidates[candidates["sqft_living"].between(area * 0.55, area * 1.65)].head(limit)
        comps = []
        for _, row in candidates.iterrows():
            comps.append(
                {
                    "price": int(row["price"]),
                    "sqft_living": int(row["sqft_living"]),
                    "bedrooms": int(row["bedrooms"]),
                    "bathrooms": float(row["bathrooms"]),
                    "grade": int(row["grade"]),
                    "year_built": int(row["yr_built"]),
                    "zipcode": row["zipcode"],
                    "region": row["region"],
                    "price_per_sqft": round(float(row["price_per_sqft"]), 1),
                    "sold_at": row["sale_date"].strftime("%Y-%m-%d"),
                    "distance_miles": round(float(np.sqrt(((row["lat"] - lat) * 69) ** 2 + ((row["long"] - lon) * 69 * np.cos(np.radians(lat))) ** 2)), 2),
                    "similarity": int(np.clip(round(100 - float(row["_score"]) * 105), 55, 97)),
                    "same_zip": bool(row["zipcode"] == record["zipcode"]),
                }
            )
        comps.sort(key=lambda item: item["similarity"], reverse=True)
        return comps

    def _market(self, record: dict[str, Any], predicted: float) -> dict[str, Any]:
        zipcode = record["zipcode"]
        stats = self.zip_stats.get(zipcode) or {}
        region = region_for(record["lat"], record["long"])
        subset = self._frame[self._frame["zipcode"] == zipcode] if zipcode in self.zip_stats else self._frame[self._frame["region"] == region]
        ppsf = predicted / max(record["sqft_living"], 1)
        ppsf_series = subset["price_per_sqft"] if len(subset) else self._frame["price_per_sqft"]
        position = float((ppsf_series < ppsf).mean() * 100)
        months = subset.groupby("sale_month").agg(count=("price", "size"), median_price=("price", "median"))
        recent = months.tail(3)["median_price"].median() if len(months) else stats.get("median_price", predicted)
        early = months.head(3)["median_price"].median() if len(months) else recent
        trend_pct = (recent / early - 1) * 100 if early else 0
        return {
            "zipcode": zipcode,
            "region": region,
            "sales_count": int(len(subset)),
            "monthly_sales": round(float(len(subset) / 13), 1),
            "median_price": int(stats.get("median_price", subset["price"].median())),
            "median_ppsf": round(float(stats.get("median_ppsf", subset["price_per_sqft"].median())), 1),
            "predicted_ppsf": round(float(ppsf), 1),
            "ppsf_percentile": round(position, 1),
            "trend_pct_sample_period": round(float(trend_pct), 1),
            "trend_note": "样本期（2014-05 至 2015-05）内近三个月对前三个月的描述性变化，不是未来预测。",
        }

    def _assessment(self, request: ValuationRequest, predicted: float, interval: dict[str, float]) -> dict[str, Any] | None:
        if request.asking_price is None:
            return None
        asking = float(request.asking_price)
        difference = asking - predicted
        difference_pct = difference / predicted * 100
        if asking < interval["low"]:
            verdict, tone = "低于模型参考区间", "underpriced"
            message = "挂牌价低于模型 80% 参考区间，需重点核查房屋状况、产权、噪音或数据缺失等折价因素。"
        elif asking > interval["high"]:
            verdict, tone = "高于模型参考区间", "overpriced"
            message = "挂牌价高于模型 80% 参考区间，建议结合可比成交、装修与景观进行议价。"
        else:
            verdict, tone = "处于模型参考区间", "fair"
            message = "挂牌价落在模型 80% 参考区间内，可结合房屋状况和可比成交进一步判断。"
        return {
            "asking_price": int(asking),
            "difference": _rounded(difference, 500),
            "difference_pct": round(float(difference_pct), 1),
            "verdict": verdict,
            "tone": tone,
            "message": message,
        }

    def _feature_display(self, feature: str, value: Any) -> str:
        if feature in DISPLAY_FEATURES:
            try:
                return DISPLAY_FEATURES[feature](float(value))
            except Exception:
                pass
        if feature in {"lat", "long"}:
            return f"{float(value):.4f}"
        if feature in self.labels:
            return f"{value:g}" if isinstance(value, (int, float, np.floating)) else str(value)
        return str(value)

    def analyze(self, request: ValuationRequest) -> dict[str, Any]:
        record = self._record(request)
        X = self._matrix([record])
        predicted = float(self._raw_predict(X)[0])
        shap_values, base = self._contributions(X)
        low = max(30_000.0, predicted + float(self.interval["residual_q10"]))
        high = predicted + float(self.interval["residual_q90"])
        comps = self._comps(record)
        market = self._market(record, predicted)
        assessment = self._assessment(request, predicted, {"low": low, "high": high})
        warnings = self._warnings(request)

        contributions = []
        for index, feature in enumerate(self.features):
            amount = float(shap_values[0, index])
            contributions.append(
                {
                    "feature": feature,
                    "label": self.labels.get(feature, feature),
                    "value": record.get(feature),
                    "value_display": self._feature_display(feature, record.get(feature)),
                    "amount": round(amount, 2),
                    "direction": "positive" if amount >= 0 else "negative",
                    "share_pct": round(abs(amount) / max(predicted, 1) * 100, 2),
                }
            )
        contributions.sort(key=lambda item: abs(item["amount"]), reverse=True)

        positives = [item for item in contributions if item["amount"] > 0][:3]
        negatives = [item for item in contributions if item["amount"] < 0][:3]
        summary_bits = []
        if positives:
            summary_bits.append("主要支撑项为" + "、".join(f"{item['label']}（+${item['amount']:,.0f}）" for item in positives))
        if negatives:
            summary_bits.append("主要拖累项为" + "、".join(f"{item['label']}（${item['amount']:,.0f}）" for item in negatives))
        narrative = (
            f"模型估值为 ${_rounded(predicted):,}，80% 参考区间 ${_rounded(low):,}–${_rounded(high):,}。"
            + "；".join(summary_bits)
            + "。所有 SHAP 贡献值之和等于预测价减去模型基准值，可逐项核对。"
        )

        # Transparent counterfactual analysis using the same model.
        variants = []
        variant_specs = [
            ("室内面积增加 10%", {"sqft_living": min(12000, request.sqft_living * 1.10), "sqft_above": None, "sqft_basement": request.sqft_basement}),
            ("房屋状况提升 1 级", {"condition": min(5, request.condition + 1)}),
            ("建筑等级提升 1 级", {"grade": min(13, request.grade + 1)}),
            ("增加一次近期翻新", {"yr_renovated": 2015}),
        ]
        variant_records = []
        for _, changes in variant_specs:
            changed = {**record, **changes}
            if changes.get("sqft_above", "keep") is None:
                basement = min(changed["sqft_basement"], max(changed["sqft_living"] - 300, 0))
                changed["sqft_above"] = max(changed["sqft_living"] - basement, 300)
            variant_records.append(changed)
        variant_X = self._matrix(variant_records)
        variant_prices = self._raw_predict(variant_X)
        for (label, _), price in zip(variant_specs, variant_prices):
            delta = float(price) - predicted
            variants.append({"label": label, "delta": _rounded(delta, 100), "delta_pct": round(delta / predicted * 100, 1)})

        return {
            "input": request.model_dump(),
            "estimate": {
                "value": _rounded(predicted, 100),
                "raw_value": round(predicted, 2),
                "range_low": _rounded(low, 100),
                "range_high": _rounded(high, 100),
                "currency": "USD",
                "price_per_sqft": round(predicted / max(request.sqft_living, 1), 1),
                "interval_level": 0.80,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            "confidence": self._confidence(predicted, request, comps),
            "assessment": assessment,
            "market": market,
            "comparables": comps,
            "explanation": {
                "base_value": round(base, 2),
                "prediction": round(predicted, 2),
                "contributions": contributions,
                "positive": positives,
                "negative": negatives,
                "narrative": narrative,
                "method": "XGBoost pred_contribs / exact TreeSHAP",
                "what_if": variants,
            },
            "warnings": warnings,
            "assumptions": [
                "目标为 2014–2015 年金县住宅成交价，单位为美元。",
                "未提供的土地/邻域特征采用同邮编中位数作为代理变量。",
                "模型不进行现场勘察，不验证产权、结构安全、学区或租约。",
            ],
            "model": {
                "name": "XGBoost",
                "version": "1.0.0",
                "mae": self.metrics["xgboost"]["mae"],
                "r2": self.metrics["xgboost"]["r2"],
                "trained_at": self.artifact["trained_at"],
                "test_rows": self.artifact["test_rows"],
            },
        }

    def quick_predict(self, request: ValuationRequest) -> dict[str, Any]:
        record = self._record(request)
        X = self._matrix([record])
        value = float(self._raw_predict(X)[0])
        return {
            "predicted_price": _rounded(value, 100),
            "range_low": _rounded(max(30_000, value + self.interval["residual_q10"]), 100),
            "range_high": _rounded(value + self.interval["residual_q90"], 100),
            "price_per_sqft": round(value / max(request.sqft_living, 1), 1),
            "zipcode": request.zipcode,
            "region": self.zip_stats.get(request.zipcode, {}).get("region", region_for(record["lat"], record["long"])),
        }

    def market_for_zip(self, zipcode: str) -> dict[str, Any]:
        stats = self.zip_stats.get(zipcode)
        if not stats:
            raise KeyError(zipcode)
        subset = self._frame[self._frame["zipcode"] == zipcode]
        months = subset.groupby("sale_month").agg(count=("price", "size"), median_price=("price", "median"))
        return {
            "zipcode": zipcode,
            "region": stats.get("region"),
            "sales_count": int(len(subset)),
            "median_price": int(stats.get("median_price", 0)),
            "median_ppsf": round(float(stats.get("median_ppsf", 0)), 1),
            "median_area": int(subset["sqft_living"].median()),
            "waterfront_share_pct": round(float(subset["waterfront"].mean() * 100), 1),
            "renovated_share_pct": round(float(subset["has_renovated"].mean() * 100), 1),
            "trend": [
                {"month": str(month), "median_price": int(row["median_price"]), "count": int(row["count"])}
                for month, row in months.iterrows()
            ],
            "note": "基于 2014-05 至 2015-05 的历史成交样本。",
        }


@lru_cache(maxsize=1)
def get_model_service() -> ModelService:
    return ModelService()
