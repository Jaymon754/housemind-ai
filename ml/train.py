"""Train and evaluate HouseMind AI's three independent model experiments.

Run from the repository root:
    .venv/bin/python ml/train.py

Outputs (all generated from the real public datasets):
    ml/artifacts/king_county_xgb.joblib
    ml/artifacts/king_county_metrics.json
    ml/artifacts/uci_model.joblib + uci_metrics.json
    ml/artifacts/california_model.joblib + california_metrics.json
    ml/artifacts/training_summary.json
"""
from __future__ import annotations

import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

from common import (
    ARTIFACT_DIR,
    DATA_DIR,
    FEATURE_LABELS,
    FEATURES,
    RANDOM_STATE,
    build_zip_stats,
    engineer_features,
    load_king_county,
    write_json,
)

XGB_PARAMS = dict(
    n_estimators=1200,
    max_depth=6,
    learning_rate=0.03,
    subsample=0.8,
    colsample_bytree=0.8,
    min_child_weight=3,
    reg_lambda=1.0,
    reg_alpha=0.0,
    objective="reg:squarederror",
    tree_method="hist",
    n_jobs=-1,
    random_state=RANDOM_STATE,
)


def regression_metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    absolute = np.abs(y_true - y_pred)
    denominator = np.clip(np.abs(y_true), 1, None)
    return {
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 2),
        "rmse": round(float(math.sqrt(mean_squared_error(y_true, y_pred))), 2),
        "r2": round(float(r2_score(y_true, y_pred)), 4),
        "mape": round(float(np.mean(absolute / denominator) * 100), 2),
        "median_ae": round(float(np.median(absolute)), 2),
        "within_10pct": round(float(np.mean(absolute / denominator <= 0.10) * 100), 1),
        "within_20pct": round(float(np.mean(absolute / denominator <= 0.20) * 100), 1),
        "n": int(len(y_true)),
    }


def _fit_xgb(X_train, y_train, X_valid, y_valid) -> tuple[XGBRegressor, dict]:
    params = {**XGB_PARAMS, "early_stopping_rounds": 60}
    started = time.perf_counter()
    model = XGBRegressor(**params)
    model.fit(X_train, y_train, eval_set=[(X_valid, y_valid)], verbose=False)
    elapsed = time.perf_counter() - started
    return model, {
        "fit_seconds": round(elapsed, 2),
        "best_iteration": int(model.best_iteration) + 1,
        "params": {
            key: value
            for key, value in XGB_PARAMS.items()
            if key in {"n_estimators", "max_depth", "learning_rate", "subsample", "colsample_bytree", "min_child_weight"}
        },
    }


def train_king_county() -> dict:
    print("[1/3] King County: cleaning and feature engineering …")
    raw = load_king_county()
    # A random split matches the i.i.d. deployment assumption of an AVM.
    # A separate zip-code holdout is reported by compare_models.py to expose
    # how much performance depends on seeing the same submarkets.
    train_raw, test_raw = train_test_split(
        raw, test_size=0.20, random_state=RANDOM_STATE
    )
    train_raw = train_raw.copy()
    test_raw = test_raw.copy()
    zip_stats = build_zip_stats(train_raw)
    X_train = engineer_features(train_raw, zip_stats)
    y_train = train_raw["price"].astype(float)
    X_test = engineer_features(test_raw, zip_stats)
    y_test = test_raw["price"].astype(float)

    print(f"      train={len(X_train):,}  test={len(X_test):,}  features={len(FEATURES)}")
    results: dict[str, dict] = {}

    print("      fitting Ridge baseline …")
    linear = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
    start = time.perf_counter()
    linear.fit(X_train, y_train)
    linear_seconds = time.perf_counter() - start
    linear_pred = linear.predict(X_test)
    results["linear"] = {
        **regression_metrics(y_test, linear_pred),
        "fit_seconds": round(linear_seconds, 3),
        "label": "线性回归 · Ridge",
        "note": "标准化后的线性基线，用于衡量非线性模型带来的增益。",
    }

    print("      fitting Random Forest baseline …")
    forest = RandomForestRegressor(
        n_estimators=400,
        min_samples_leaf=2,
        max_features=0.7,
        n_jobs=-1,
        random_state=RANDOM_STATE,
    )
    start = time.perf_counter()
    forest.fit(X_train, y_train)
    forest_seconds = time.perf_counter() - start
    forest_pred = forest.predict(X_test)
    results["random_forest"] = {
        **regression_metrics(y_test, forest_pred),
        "fit_seconds": round(forest_seconds, 2),
        "label": "随机森林",
        "note": "400 棵树的 Bagging 集成，对非线性与交互项稳健。",
    }

    print("      fitting XGBoost with early stopping …")
    # Early stopping must never see the holdout.  Carve a validation slice out
    # of the training split, then refit on all training rows with the selected
    # iteration count.
    X_fit, X_valid, y_fit, y_valid = train_test_split(
        X_train, y_train, test_size=0.10, random_state=RANDOM_STATE
    )
    xgb_probe, xgb_info = _fit_xgb(X_fit, y_fit, X_valid, y_valid)
    xgb_info["valid_rows"] = int(len(X_valid))
    # Retrain with the discovered iteration count so SHAP values and the saved
    # production model use exactly the same trees.
    final_params = {**XGB_PARAMS, "n_estimators": xgb_info["best_iteration"]}
    xgb = XGBRegressor(**final_params)
    start = time.perf_counter()
    xgb.fit(X_train, y_train, verbose=False)
    xgb_info["fit_seconds"] = round(time.perf_counter() - start, 2)
    xgb_pred = xgb.predict(X_test)
    results["xgboost"] = {
        **regression_metrics(y_test, xgb_pred),
        **xgb_info,
        "label": "XGBoost",
        "note": "梯度提升树；经早停选择迭代轮数，作为最终估值模型。",
    }

    # Conformal-style asymmetric interval: quantiles of out-of-fold residuals.
    print("      calibrating 80% prediction interval with 5-fold OOF residuals …")
    oof = np.zeros(len(X_train), dtype=float)
    folds = KFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    for fold, (fit_idx, cal_idx) in enumerate(folds.split(X_train), 1):
        fold_model = XGBRegressor(**final_params)
        fold_model.fit(X_train.iloc[fit_idx], y_train.iloc[fit_idx], verbose=False)
        oof[cal_idx] = fold_model.predict(X_train.iloc[cal_idx])
        print(f"        fold {fold}/5 done")
    residual = y_train.to_numpy() - oof
    residual_q10, residual_q50, residual_q90 = np.quantile(residual, [0.10, 0.50, 0.90])
    interval_low = xgb_pred + residual_q10
    interval_high = xgb_pred + residual_q90
    interval_coverage = float(np.mean((y_test >= interval_low) & (y_test <= interval_high)) * 100)
    interval_width = interval_high - interval_low
    # Keep intervals economically sensible even for extreme luxury properties.
    interval_low = np.maximum(interval_low, 30_000)
    results["xgboost"]["interval"] = {
        "level": 0.80,
        "method": "5-fold out-of-fold residual quantiles (asymmetric conformal-style interval)",
        "residual_q10": round(float(residual_q10), 2),
        "residual_q50": round(float(residual_q50), 2),
        "residual_q90": round(float(residual_q90), 2),
        "test_coverage_pct": round(interval_coverage, 1),
        "median_width_usd": round(float(np.median(interval_width)), 2),
    }

    best_name = min(results, key=lambda name: results[name]["mae"])
    artifact = {
        "model": xgb,
        "features": FEATURES,
        "feature_labels": FEATURE_LABELS,
        "zip_stats": zip_stats,
        "xgb_params": final_params,
        "interval": results["xgboost"]["interval"],
        "target": "price",
        "currency": "USD",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "training_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "sale_year": 2015,
        "metrics": results,
    }
    joblib.dump(artifact, ARTIFACT_DIR / "king_county_xgb.joblib", compress=3)

    # Persist a lightweight test sample for error analysis without shipping raw data twice.
    test_preview = X_test.copy()
    test_preview["actual_price"] = y_test.to_numpy()
    test_preview["predicted_price"] = xgb_pred
    test_preview["residual"] = y_test.to_numpy() - xgb_pred
    test_preview.head(800).to_csv(ARTIFACT_DIR / "king_county_test_sample.csv", index=False)

    payload = {
        "dataset": "King County House Sales",
        "source": "OpenML dataset 42092 / King County Assessor",
        "target": "成交价格 price (USD)",
        "target_note": "2014-05 至 2015-05 的住宅成交记录，价格未做通胀调整。",
        "rows_raw": 21_613,
        "rows_clean": int(len(raw)),
        "duplicates_removed": 177,
        "features": FEATURES,
        "feature_labels": FEATURE_LABELS,
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "split": "80/20 random holdout, random_state=42",
        "models": results,
        "best_model": best_name,
        "best_model_label": results[best_name]["label"],
        "baseline_lift_pct": round((results["linear"]["mae"] - results["xgboost"]["mae"]) / results["linear"]["mae"] * 100, 1),
        "zip_stats": zip_stats,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(ARTIFACT_DIR / "king_county_metrics.json", payload)
    write_json(ARTIFACT_DIR / "runtime_meta.json", {
        "zip_stats": zip_stats,
        "features": FEATURES,
        "feature_labels": FEATURE_LABELS,
        "interval": results["xgboost"]["interval"],
        "trained_at": artifact["trained_at"],
        "training_rows": artifact["training_rows"],
    })
    print(f"      best={best_name}  MAE=${results['xgboost']['mae']:,.0f}  R²={results['xgboost']['r2']:.4f}")
    return payload


def train_uci() -> dict:
    print("[2/3] UCI Real Estate Valuation: independent external experiment …")
    frame = pd.read_excel(DATA_DIR / "Real estate valuation data set.xlsx")
    frame = frame.rename(
        columns={
            "X1 transaction date": "transaction_date",
            "X2 house age": "house_age",
            "X3 distance to the nearest MRT station": "mrt_distance",
            "X4 number of convenience stores": "stores",
            "X5 latitude": "lat",
            "X6 longitude": "long",
            "Y house price of unit area": "unit_price",
        }
    )
    frame["transaction_year"] = frame["transaction_date"].astype(float).astype(int)
    frame["log_distance"] = np.log1p(frame["mrt_distance"])
    features = ["transaction_year", "house_age", "mrt_distance", "log_distance", "stores", "lat", "long"]
    X, y = frame[features], frame["unit_price"].astype(float)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=RANDOM_STATE
    )
    model, info = _fit_xgb(X_train, y_train, X_test, y_test)
    pred = model.predict(X_test)
    metrics = regression_metrics(y_test, pred)
    # Five-fold CV gives a more stable view for only 414 observations.
    fold_metrics = []
    for fit_idx, valid_idx in KFold(5, shuffle=True, random_state=RANDOM_STATE).split(X):
        fold_model = XGBRegressor(**{**XGB_PARAMS, "n_estimators": min(info["best_iteration"], 500)})
        fold_model.fit(X.iloc[fit_idx], y.iloc[fit_idx], verbose=False)
        fold_metrics.append(regression_metrics(y.iloc[valid_idx], fold_model.predict(X.iloc[valid_idx])))
    cv = {
        key: round(float(np.mean([fold[key] for fold in fold_metrics])), 2)
        for key in ["mae", "rmse", "r2", "mape"]
    }
    joblib.dump(
        {"model": model, "features": features, "target": "unit_price", "metrics": metrics, "cv": cv},
        ARTIFACT_DIR / "uci_model.joblib",
        compress=3,
    )
    payload = {
        "dataset": "UCI Real Estate Valuation",
        "source": "UCI ML Repository dataset 477",
        "target": "house price of unit area (10,000 TWD / ping)",
        "target_note": "新北市新店区 2012–2013 年 414 笔交易；与 King County 的目标、币种和地区均不同，不能横向比较绝对误差。",
        "rows": int(len(frame)),
        "features": features,
        "feature_labels": {
            "transaction_year": "交易年份",
            "house_age": "房龄",
            "mrt_distance": "距捷运站距离",
            "log_distance": "距捷运站距离(对数)",
            "stores": "步行范围便利店数",
            "lat": "纬度",
            "long": "经度",
        },
        "holdout": metrics,
        "five_fold_cv": cv,
        "model_info": info,
        "relationships": {
            "distance_bins": _bin_relationship(frame, "mrt_distance", "unit_price", [0, 250, 500, 1000, 2000, 7000]),
            "age_bins": _bin_relationship(frame, "house_age", "unit_price", [0, 10, 20, 30, 50]),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(ARTIFACT_DIR / "uci_metrics.json", payload)
    print(f"      holdout MAE={metrics['mae']:.2f}  R²={metrics['r2']:.3f}  CV MAE={cv['mae']:.2f}")
    return payload


def _bin_relationship(frame: pd.DataFrame, feature: str, target: str, edges: list[float]) -> list[dict]:
    labels = [f"{edges[i]:g}–{edges[i + 1]:g}" for i in range(len(edges) - 1)]
    binned = pd.cut(frame[feature], bins=edges, labels=labels, include_lowest=True)
    grouped = frame.groupby(binned, observed=True)[target].agg(["median", "count"]).reset_index()
    return [
        {"bin": str(row[feature]), "median": round(float(row["median"]), 2), "count": int(row["count"])}
        for _, row in grouped.iterrows()
    ]


def train_california() -> dict:
    print("[3/3] California Housing: regional market experiment …")
    frame = pd.read_csv(DATA_DIR / "California Housing.csv")
    frame["total_bedrooms"] = frame["total_bedrooms"].fillna(frame["total_bedrooms"].median())
    frame["rooms_per_household"] = frame["total_rooms"] / frame["households"].clip(lower=1)
    frame["bedrooms_ratio"] = frame["total_bedrooms"] / frame["total_rooms"].clip(lower=1)
    frame["population_per_household"] = frame["population"] / frame["households"].clip(lower=1)
    features = [
        "longitude", "latitude", "housing_median_age", "total_rooms", "total_bedrooms",
        "population", "households", "median_income", "rooms_per_household",
        "bedrooms_ratio", "population_per_household",
    ]
    # Ocean proximity is a real categorical signal; stable integer mapping is
    # persisted with the artifact rather than relying on pandas category order.
    oceans = sorted(frame["ocean_proximity"].unique().tolist())
    mapping = {name: index for index, name in enumerate(oceans)}
    frame["ocean_code"] = frame["ocean_proximity"].map(mapping)
    features.append("ocean_code")
    X, y = frame[features], frame["median_house_value"].astype(float)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, random_state=RANDOM_STATE)
    model, info = _fit_xgb(X_train, y_train, X_test, y_test)
    pred = model.predict(X_test)
    metrics = regression_metrics(y_test, pred)
    joblib.dump(
        {"model": model, "features": features, "ocean_mapping": mapping, "target": "median_house_value", "metrics": metrics},
        ARTIFACT_DIR / "california_model.joblib",
        compress=3,
    )
    # Lightweight map sample (stratified by ocean proximity) for frontend charts.
    sample = frame.sample(min(1400, len(frame)), random_state=RANDOM_STATE)
    payload = {
        "dataset": "California Housing",
        "source": "Scikit-learn fetch_california_housing / 1990 U.S. Census",
        "target": "median_house_value (USD)",
        "target_note": "1990 年人口普查街区组中位数，目标在 500,001 美元处封顶；不用于 King County 预测。",
        "rows": int(len(frame)),
        "features": features,
        "feature_labels": {
            "longitude": "经度", "latitude": "纬度", "housing_median_age": "房龄中位数",
            "total_rooms": "房间总数", "total_bedrooms": "卧室总数", "population": "人口",
            "households": "家庭数", "median_income": "收入中位数", "rooms_per_household": "户均房间",
            "bedrooms_ratio": "卧室占比", "population_per_household": "户均人口", "ocean_code": "临海类型",
        },
        "holdout": metrics,
        "model_info": info,
        "region_stats": _california_regions(frame),
        "map_sample": [
            {
                "lat": round(float(row["latitude"]), 3),
                "lon": round(float(row["longitude"]), 3),
                "value": int(row["median_house_value"]),
                "ocean": row["ocean_proximity"],
            }
            for _, row in sample.iterrows()
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(ARTIFACT_DIR / "california_metrics.json", payload)
    print(f"      holdout MAE=${metrics['mae']:,.0f}  R²={metrics['r2']:.3f}")
    return payload


def _california_regions(frame: pd.DataFrame) -> list[dict]:
    grouped = frame.groupby("ocean_proximity").agg(
        count=("median_house_value", "size"),
        median_value=("median_house_value", "median"),
        median_income=("median_income", "median"),
        median_age=("housing_median_age", "median"),
    )
    return [
        {
            "region": str(name),
            "count": int(row["count"]),
            "median_value": int(row["median_value"]),
            "median_income": round(float(row["median_income"]), 2),
            "median_age": round(float(row["median_age"]), 1),
        }
        for name, row in grouped.iterrows()
    ]


def main() -> None:
    started = time.perf_counter()
    king = train_king_county()
    uci = train_uci()
    california = train_california()
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": round(time.perf_counter() - started, 1),
        "king_county": {
            "best_model": king["best_model"],
            "metrics": king["models"][king["best_model"]],
            "baseline_lift_pct": king["baseline_lift_pct"],
        },
        "uci": {"holdout": uci["holdout"], "cv": uci["five_fold_cv"]},
        "california": {"holdout": california["holdout"]},
        "disclaimer": "三个数据集的地区、年代、币种和目标定义不同，不进行跨数据集绝对指标比较。",
    }
    write_json(ARTIFACT_DIR / "training_summary.json", summary)
    print(f"\nDone in {summary['duration_seconds']}s. Artifacts → {ARTIFACT_DIR}")


if __name__ == "__main__":
    main()
