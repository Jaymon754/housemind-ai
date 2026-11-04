"""Build the pre-aggregated analytics payload used by the data cockpit.

Run after train.py:
    .venv/bin/python ml/build_dashboard.py
"""
from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd

from common import ARTIFACT_DIR, load_king_county, write_json

CONDITION_LABELS = {1: "较差", 2: "一般", 3: "平均", 4: "良好", 5: "优秀"}


def main() -> None:
    frame = load_king_county()
    print(f"Building cockpit aggregates for {len(frame):,} sales …")

    # 30 equal-width USD bins, trimmed at the 99.5th percentile for a readable chart.
    cap = int(frame["price"].quantile(0.995) // 25_000 * 25_000)
    edges = list(range(0, cap + 25_000, 25_000))
    counts, _ = np.histogram(frame["price"], bins=edges)
    histogram = [
        {"bin": f"{edges[i] // 1000}–{edges[i + 1] // 1000}k", "low": edges[i], "count": int(counts[i])}
        for i in range(len(counts))
    ]

    region_group = frame.groupby("region").agg(
        count=("price", "size"),
        median_price=("price", "median"),
        mean_price=("price", "mean"),
        median_ppsf=("price_per_sqft", "median"),
        median_area=("sqft_living", "median"),
    ).sort_values("median_price", ascending=False)
    regions = [
        {
            "region": str(region),
            "count": int(row["count"]),
            "share_pct": round(float(row["count"] / len(frame) * 100), 1),
            "median_price": int(row["median_price"]),
            "mean_price": int(row["mean_price"]),
            "median_ppsf": round(float(row["median_ppsf"]), 2),
            "median_area": int(row["median_area"]),
        }
        for region, row in region_group.iterrows()
    ]

    monthly = frame.groupby("sale_month").agg(
        count=("price", "size"),
        median_price=("price", "median"),
        median_ppsf=("price_per_sqft", "median"),
    )
    trend = [
        {
            "month": str(month),
            "label": f"{str(month)[5:7]}月",
            "count": int(row["count"]),
            "median_price": int(row["median_price"]),
            "median_ppsf": round(float(row["median_ppsf"]), 2),
        }
        for month, row in monthly.iterrows()
    ]

    condition_group = frame.groupby("condition").agg(count=("price", "size"), median_price=("price", "median"))
    conditions = [
        {
            "condition": int(condition),
            "label": CONDITION_LABELS.get(int(condition), str(condition)),
            "count": int(row["count"]),
            "median_price": int(row["median_price"]),
        }
        for condition, row in condition_group.iterrows()
    ]

    grade_group = frame.groupby("grade").agg(count=("price", "size"), median_price=("price", "median"))
    grades = [
        {"grade": int(grade), "count": int(row["count"]), "median_price": int(row["median_price"])}
        for grade, row in grade_group.iterrows()
    ]

    zip_group = frame.groupby("zipcode").agg(
        count=("price", "size"), median_price=("price", "median"), median_ppsf=("price_per_sqft", "median")
    )
    zip_group = zip_group[zip_group["count"] >= 30].sort_values("median_price", ascending=False)
    top_zips = [
        {
            "zipcode": str(int(zipcode)),
            "count": int(row["count"]),
            "median_price": int(row["median_price"]),
            "median_ppsf": round(float(row["median_ppsf"]), 1),
        }
        for zipcode, row in zip_group.head(8).iterrows()
    ]

    # Deterministic samples keep the payload small while preserving spatial shape.
    rng = np.random.default_rng(42)
    map_sample = frame.iloc[rng.choice(len(frame), size=min(1700, len(frame)), replace=False)]
    map_points = [
        {
            "lat": round(float(row["lat"]), 4),
            "lon": round(float(row["long"]), 4),
            "price": int(row["price"]),
            "area": int(row["sqft_living"]),
            "region": row["region"],
        }
        for _, row in map_sample.iterrows()
    ]
    area_sample = frame.iloc[rng.choice(len(frame), size=min(900, len(frame)), replace=False)]
    area_points = [
        {
            "area": int(row["sqft_living"]),
            "price": int(row["price"]),
            "bedrooms": int(row["bedrooms"]),
            "grade": int(row["grade"]),
            "region": row["region"],
        }
        for _, row in area_sample.iterrows()
    ]

    # Price-per-square-foot bands by area bucket.
    frame["area_bucket"] = pd.cut(
        frame["sqft_living"], [0, 1200, 1600, 2000, 2600, 3400, 5000, 20_000],
        labels=["<1.2k", "1.2–1.6k", "1.6–2.0k", "2.0–2.6k", "2.6–3.4k", "3.4–5k", "5k+"],
    )
    area_bands = frame.groupby("area_bucket", observed=True).agg(
        count=("price", "size"), median_price=("price", "median"), median_ppsf=("price_per_sqft", "median")
    )
    area_price = [
        {
            "band": str(band),
            "count": int(row["count"]),
            "median_price": int(row["median_price"]),
            "median_ppsf": round(float(row["median_ppsf"]), 1),
        }
        for band, row in area_bands.iterrows()
    ]

    waterfront = frame[frame["waterfront"] == 1]["price"].median()
    inland = frame[frame["waterfront"] == 0]["price"].median()
    renovated = frame[frame["has_renovated"] == 1]["price"].median()
    not_renovated = frame[frame["has_renovated"] == 0]["price"].median()
    peak = monthly["median_price"].idxmax()
    trough = monthly["median_price"].idxmin()

    payload = {
        "dataset": "King County House Sales",
        "period": {
            "start": frame["sale_date"].min().strftime("%Y-%m-%d"),
            "end": frame["sale_date"].max().strftime("%Y-%m-%d"),
        },
        "overview": {
            "total_sales": int(len(frame)),
            "median_price": int(frame["price"].median()),
            "average_price": int(frame["price"].mean()),
            "median_ppsf": round(float(frame["price_per_sqft"].median()), 1),
            "average_area": int(frame["sqft_living"].mean()),
            "median_area": int(frame["sqft_living"].median()),
            "zipcodes": int(frame["zipcode"].nunique()),
            "waterfront_share_pct": round(float(frame["waterfront"].mean() * 100), 2),
            "renovated_share_pct": round(float(frame["has_renovated"].mean() * 100), 1),
        },
        "market_pulse": {
            "waterfront_median": int(waterfront),
            "inland_median": int(inland),
            "waterfront_premium_pct": round(float((waterfront / inland - 1) * 100), 1),
            "renovated_median": int(renovated),
            "not_renovated_median": int(not_renovated),
            "renovated_descriptive_gap_pct": round(float((renovated / not_renovated - 1) * 100), 1),
            "peak_month": str(peak),
            "peak_median": int(monthly.loc[peak, "median_price"]),
            "trough_month": str(trough),
            "trough_median": int(monthly.loc[trough, "median_price"]),
            "note": "滨水与翻新差异为未控制混杂因素的描述性统计，不代表因果溢价。",
        },
        "histogram": histogram,
        "regions": regions,
        "trend": trend,
        "conditions": conditions,
        "grades": grades,
        "top_zipcodes": top_zips,
        "map_points": map_points,
        "area_points": area_points,
        "area_price_bands": area_price,
        "quality": {
            "raw_rows": 21_613,
            "clean_rows": int(len(frame)),
            "duplicate_sale_ids_removed": 177,
            "missing_values_after_clean": int(frame[["price", "sqft_living", "grade", "lat", "long"]].isna().sum().sum()),
            "cleaning_rules": [
                "按成交 ID 去重",
                "移除卧室数为 0 或大于 10 的结构异常记录",
                "移除室内面积小于 300 sqft 或价格低于 5 万美元的记录",
                "保留高价与大面积真实成交，不做价格截尾",
            ],
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(ARTIFACT_DIR / "dashboard.json", payload)
    print(f"dashboard.json written: {len(payload['map_points'])} map points, {len(payload['trend'])} months")


if __name__ == "__main__":
    main()
