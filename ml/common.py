"""Shared data preparation utilities for HouseMind AI experiments.

The three public datasets are intentionally kept separate: they describe
different housing markets, target definitions and time periods.  No model is
trained on a concatenation of them.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "Datasets"
ARTIFACT_DIR = ROOT / "ml" / "artifacts"
REPORT_DIR = ROOT / "ml" / "reports"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

RANDOM_STATE = 42
SALE_YEAR = 2015

FEATURES = [
    "bedrooms",
    "bathrooms",
    "sqft_living",
    "sqft_lot",
    "floors",
    "waterfront",
    "view",
    "condition",
    "grade",
    "sqft_above",
    "sqft_basement",
    "yr_built",
    "yr_renovated",
    "lat",
    "long",
    "sqft_living15",
    "sqft_lot15",
    "house_age",
    "has_renovated",
    "living_lot_ratio",
    "bath_bed_ratio",
    "zip_market_value",
]

FEATURE_LABELS = {
    "bedrooms": "卧室数量",
    "bathrooms": "卫浴数量",
    "sqft_living": "室内面积",
    "sqft_lot": "土地面积",
    "floors": "楼层数",
    "waterfront": "滨水属性",
    "view": "景观等级",
    "condition": "房屋状况",
    "grade": "建筑等级",
    "sqft_above": "地上面积",
    "sqft_basement": "地下室面积",
    "yr_built": "建造年份",
    "yr_renovated": "翻新年份",
    "lat": "纬度",
    "long": "经度",
    "sqft_living15": "周边平均室内面积",
    "sqft_lot15": "周边平均土地面积",
    "house_age": "房龄",
    "has_renovated": "是否翻新",
    "living_lot_ratio": "容积率代理",
    "bath_bed_ratio": "卫浴卧室比",
    "zip_market_value": "邮编市场基准价",
}

FEATURE_UNITS = {
    "sqft_living": "sqft",
    "sqft_lot": "sqft",
    "sqft_above": "sqft",
    "sqft_basement": "sqft",
    "sqft_living15": "sqft",
    "sqft_lot15": "sqft",
    "house_age": "年",
    "zip_market_value": "USD",
    "lat": "°",
    "long": "°",
}


def _numeric(frame: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for col in cols:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    return frame


def load_king_county() -> pd.DataFrame:
    """Load, de-duplicate and lightly clean the King County sales data.

    Cleaning is deliberately conservative.  Only impossible structural values
    (zero bedrooms, 33-bedroom data-entry anomaly) and exact duplicate sale IDs
    are removed.  Luxury homes and outliers are retained because they are real
    market observations.
    """
    path = DATA_DIR / "King County House Sales.csv"
    frame = pd.read_csv(path)
    frame = frame.drop_duplicates(subset="id").copy()
    frame = frame[
        (frame["bedrooms"].between(1, 10))
        & (frame["bathrooms"].between(0.5, 8))
        & (frame["sqft_living"] >= 300)
        & (frame["price"] >= 50_000)
    ].copy()
    frame["sale_date"] = pd.to_datetime(frame["date"], format="%Y%m%dT%H%M%S")
    frame["sale_year"] = frame["sale_date"].dt.year
    frame["sale_month"] = frame["sale_date"].dt.to_period("M").astype(str)
    frame["has_renovated"] = (frame["yr_renovated"] > 0).astype(int)
    frame["house_age"] = (frame["sale_year"] - frame["yr_built"]).clip(lower=0)
    frame["living_lot_ratio"] = frame["sqft_living"] / frame["sqft_lot"].clip(lower=1)
    frame["bath_bed_ratio"] = frame["bathrooms"] / frame["bedrooms"].clip(lower=1)
    frame["price_per_sqft"] = frame["price"] / frame["sqft_living"].clip(lower=1)
    frame["region"] = frame.apply(lambda row: region_for(row["lat"], row["long"]), axis=1)
    return frame


def region_for(lat: float, lon: float) -> str:
    """Assign a human-readable Greater Seattle submarket from coordinates.

    These are analysis groupings, not official municipal boundaries.
    """
    if lat < 47.52 and lon >= -122.25:
        return "南金县"
    if lon >= -122.27 and lat >= 47.52:
        return "东区"
    if lat >= 47.74:
        return "北金县"
    if lat <= 47.40:
        return "南金县"
    if lon <= -122.38:
        return "西雅图西岸"
    if lat >= 47.56:
        return "西雅图北区"
    return "西雅图中南部"


def build_zip_stats(frame: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Smoothed zip-code market baseline learned on the training split only."""
    global_median = float(frame["price"].median())
    grouped = frame.groupby("zipcode").agg(
        count=("price", "size"),
        median_price=("price", "median"),
        median_ppsf=("price_per_sqft", "median"),
        lat=("lat", "median"),
        long=("long", "median"),
        region=("region", lambda values: values.mode().iloc[0]),
    )
    result: dict[str, dict[str, float]] = {}
    for zipcode, row in grouped.iterrows():
        weight = min(int(row["count"]), 80) / 80
        smoothed = weight * float(row["median_price"]) + (1 - weight) * global_median
        result[str(int(zipcode))] = {
            "count": int(row["count"]),
            "median_price": round(float(row["median_price"])),
            "median_ppsf": round(float(row["median_ppsf"]), 2),
            "market_value": round(float(smoothed)),
            "lat": round(float(row["lat"]), 5),
            "long": round(float(row["long"]), 5),
            "region": str(row["region"]),
        }
    return result


def engineer_features(
    frame: pd.DataFrame,
    zip_stats: dict[str, dict[str, float]],
) -> pd.DataFrame:
    """Create the exact 22 features consumed by the price model."""
    data = frame.copy()
    defaults = {
        "bedrooms": 3,
        "bathrooms": 2,
        "sqft_living": 2_000,
        "sqft_lot": 7_200,
        "floors": 1,
        "waterfront": 0,
        "view": 0,
        "condition": 3,
        "grade": 7,
        "sqft_above": np.nan,
        "sqft_basement": 0,
        "yr_built": 1985,
        "yr_renovated": 0,
        "lat": np.nan,
        "long": np.nan,
        "sqft_living15": np.nan,
        "sqft_lot15": np.nan,
    }
    for col, default in defaults.items():
        if col not in data:
            data[col] = default
        data[col] = pd.to_numeric(data[col], errors="coerce")

    # Use the zip centroid only when coordinates are not supplied.
    zipcodes = data.get("zipcode", pd.Series(["98052"] * len(data))).astype(str).str.replace(r"\.0$", "", regex=True)
    data["zipcode"] = zipcodes
    for idx in data.index:
        stats = zip_stats.get(zipcodes.loc[idx], {})
        if pd.isna(data.at[idx, "lat"]) and stats:
            data.at[idx, "lat"] = stats["lat"]
        if pd.isna(data.at[idx, "long"]) and stats:
            data.at[idx, "long"] = stats["long"]
    data["lat"] = data["lat"].fillna(47.56)
    data["long"] = data["long"].fillna(-122.28)

    data["sqft_basement"] = data["sqft_basement"].fillna(0).clip(lower=0)
    data["sqft_above"] = data["sqft_above"].fillna(
        (data["sqft_living"] - data["sqft_basement"]).clip(lower=0)
    )
    data["sqft_living15"] = data["sqft_living15"].fillna(data["sqft_living"])
    data["sqft_lot15"] = data["sqft_lot15"].fillna(data["sqft_lot"])
    data["yr_renovated"] = data["yr_renovated"].fillna(0)
    data["has_renovated"] = (data["yr_renovated"] > 0).astype(int)
    data["house_age"] = (SALE_YEAR - data["yr_built"]).clip(lower=0)
    data["living_lot_ratio"] = data["sqft_living"] / data["sqft_lot"].clip(lower=1)
    data["bath_bed_ratio"] = data["bathrooms"] / data["bedrooms"].clip(lower=1)
    data["zip_market_value"] = data["zipcode"].map(
        {key: value["market_value"] for key, value in zip_stats.items()}
    )
    data["zip_market_value"] = data["zip_market_value"].fillna(
        float(np.median([v["market_value"] for v in zip_stats.values()]))
    )

    # Basic plausibility clipping prevents absurd API inputs from destabilising
    # tree traversal while preserving the observed market range.
    data["bedrooms"] = data["bedrooms"].clip(1, 10)
    data["bathrooms"] = data["bathrooms"].clip(0.5, 8)
    data["sqft_living"] = data["sqft_living"].clip(300, 12_000)
    data["sqft_lot"] = data["sqft_lot"].clip(500, 1_500_000)
    data["sqft_above"] = data["sqft_above"].clip(300, 9_500)
    data["sqft_basement"] = data["sqft_basement"].clip(0, 5_000)
    data["grade"] = data["grade"].clip(1, 13)
    data["condition"] = data["condition"].clip(1, 5)
    data["view"] = data["view"].clip(0, 4)
    data["waterfront"] = data["waterfront"].clip(0, 1)
    data["yr_built"] = data["yr_built"].clip(1900, 2015)
    return data[FEATURES]


def to_jsonable(value: Any) -> Any:
    """Convert numpy/pandas scalars and non-finite floats for JSON output."""
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(to_jsonable(payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def price_bin(price: float) -> str:
    bins = [0, 300_000, 500_000, 750_000, 1_000_000, 2_000_000, float("inf")]
    labels = ["<30万", "30–50万", "50–75万", "75–100万", "100–200万", "200万+"]
    for index in range(len(bins) - 1):
        if bins[index] <= price < bins[index + 1]:
            return labels[index]
    return labels[-1]
