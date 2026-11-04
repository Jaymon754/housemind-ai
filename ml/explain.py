"""Compute global SHAP explanations for the production XGBoost model.

Run after training:
    .venv/bin/python ml/explain.py
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb

from common import ARTIFACT_DIR, FEATURE_LABELS, RANDOM_STATE, build_zip_stats, engineer_features, load_king_county, write_json


def main() -> None:
    print("Loading production model and holdout rows …")
    artifact = joblib.load(ARTIFACT_DIR / "king_county_xgb.joblib")
    model = artifact["model"]
    frame = load_king_county()
    # Use the persisted test sample for global explanations.  It is a genuine
    # held-out set, so it does not inflate the importance ranking.
    sample = pd.read_csv(ARTIFACT_DIR / "king_county_test_sample.csv")
    X = sample[artifact["features"]]
    print(f"Computing TreeSHAP over {len(X):,} held-out rows …")
    # XGBoost's built-in pred_contribs is the exact same TreeSHAP algorithm
    # exposed by the shap package, without version-fragile model conversion.
    booster = model.get_booster()
    contributions = booster.predict(xgb.DMatrix(X, feature_names=artifact["features"]), pred_contribs=True)
    values = contributions[:, :-1]
    base_value = float(contributions[0, -1])

    mean_abs = np.abs(values).mean(axis=0)
    direction = []
    for index, feature in enumerate(artifact["features"]):
        corr = float(np.corrcoef(X[feature].astype(float), values[:, index])[0, 1])
        direction.append(round(corr, 3) if np.isfinite(corr) else 0.0)
    ranking = sorted(
        [
            {
                "feature": feature,
                "label": FEATURE_LABELS.get(feature, feature),
                "mean_abs_shap": round(float(mean_abs[index]), 2),
                "direction_corr": direction[index],
            }
            for index, feature in enumerate(artifact["features"])
            if feature != "zip_market_value" or True
        ],
        key=lambda row: row["mean_abs_shap"],
        reverse=True,
    )
    total = sum(row["mean_abs_shap"] for row in ranking) or 1
    for row in ranking:
        row["share_pct"] = round(row["mean_abs_shap"] / total * 100, 2)
        row["direction"] = "正向" if row["direction_corr"] >= 0 else "负向"

    # Compact beeswarm sample for the frontend (top 8 features × 180 rows).
    top = [row["feature"] for row in ranking[:8]]
    rng = np.random.default_rng(RANDOM_STATE)
    indices = rng.choice(len(X), size=min(180, len(X)), replace=False)
    beeswarm = []
    for feature in top:
        column = artifact["features"].index(feature)
        values_feature = X[feature].astype(float).to_numpy()
        low, high = np.nanpercentile(values_feature, [5, 95])
        for row in indices:
            raw = float(values_feature[row])
            normalized = 0.0 if high == low else (raw - low) / (high - low)
            beeswarm.append(
                {
                    "feature": feature,
                    "label": FEATURE_LABELS.get(feature, feature),
                    "value": round(float(values[row, column]), 1),
                    "raw": round(raw, 3),
                    "normalized": round(float(np.clip(normalized, 0, 1)), 3),
                }
            )

    payload = {
        "method": "TreeSHAP (exact additive Shapley values for tree ensembles)",
        "model": "XGBoost",
        "sample_rows": int(len(X)),
        "base_value_usd": round(base_value, 2),
        "ranking": ranking,
        "beeswarm": beeswarm,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "interpretation_note": "SHAP 反映模型在本次样本中的条件关联，不等同于因果效应，也不能替代专业评估。",
    }
    write_json(ARTIFACT_DIR / "global_shap.json", payload)
    card = {
        "intended_use": "大西雅图地区住宅成交价的辅助估值与研究演示",
        "not_intended_for": [
            "正式抵押贷款评估或法律用途",
            "美国境外房产定价",
            "对个人或社区进行歧视性决策",
            "替代现场勘察与结构安全鉴定",
        ],
        "training_period": "2014-05 至 2015-05",
        "currency": "USD",
        "performance": artifact["metrics"]["xgboost"],
        "interval": artifact["interval"],
        "known_limitations": [
            "历史成交数据，不能自动反映 2020 年后的市场变化。",
            "邮编市场基准在训练集内学习；未见过的邮编会回退到全局基准。",
            "目标为成交价，未针对翻新、景观或室内装修做现场核验。",
            "模型误差在低价房中相对更大，使用 MAPE 与区间而非只看 R²。",
        ],
        "sensitive_attributes": "模型未使用种族、性别、宗教等受保护属性；但地理位置可能与历史性隔离相关，需进行公平性审查。",
        "explainability": "逐套房源提供 TreeSHAP 加性分解，所有贡献值之和等于预测值减基准值。",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(ARTIFACT_DIR / "model_card.json", card)
    print("Top drivers:")
    for row in ranking[:8]:
        print(f"  {row['label']:<12} ${row['mean_abs_shap']:,.0f}  {row['share_pct']:5.1f}%  {row['direction']}")


if __name__ == "__main__":
    main()
