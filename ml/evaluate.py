"""Evaluate saved experiments and generate report-ready charts.

    .venv/bin/python ml/evaluate.py
"""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd

from common import ARTIFACT_DIR, REPORT_DIR, region_for, write_json

INK = "#14251f"
GOLD = "#b3884c"
SAGE = "#6f8f7d"
SAND = "#e8dfd0"
font_manager.fontManager.addfont("/System/Library/Fonts/Hiragino Sans GB.ttc")
plt.rcParams.update({
    "figure.facecolor": "#fbf8f2",
    "axes.facecolor": "#fbf8f2",
    "axes.edgecolor": "#d9d1c3",
    "axes.labelcolor": INK,
    "text.color": INK,
    "xtick.color": "#5f6b64",
    "ytick.color": "#5f6b64",
    "font.family": "Hiragino Sans GB",
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def errors_by(frame: pd.DataFrame, column: str, bins=None) -> list[dict]:
    rows = []
    groups = frame.groupby(column, observed=True) if bins is None else frame.groupby(pd.cut(frame[column], bins), observed=True)
    for key, group in groups:
        absolute = (group["actual_price"] - group["predicted_price"]).abs()
        rows.append(
            {
                "group": str(key),
                "count": int(len(group)),
                "mae": round(float(absolute.mean()), 2),
                "mape": round(float((absolute / group["actual_price"].clip(lower=1)).mean() * 100), 2),
            }
        )
    return rows


def main() -> None:
    sample = pd.read_csv(ARTIFACT_DIR / "king_county_test_sample.csv")
    metrics = json.loads((ARTIFACT_DIR / "king_county_metrics.json").read_text())
    shap = json.loads((ARTIFACT_DIR / "global_shap.json").read_text())
    sample["region"] = [region_for(lat, lon) for lat, lon in zip(sample["lat"], sample["long"])]
    sample["price_band"] = pd.cut(
        sample["actual_price"],
        [0, 300_000, 500_000, 750_000, 1_000_000, 2_000_000, np.inf],
        labels=["<300k", "300-500k", "500-750k", "750k-1M", "1-2M", "2M+"],
    )

    # 1. Model comparison
    models = metrics["models"]
    names = [models[key]["label"] for key in ["linear", "random_forest", "xgboost"]]
    maes = [models[key]["mae"] for key in ["linear", "random_forest", "xgboost"]]
    fig, ax = plt.subplots(figsize=(8, 4.2), dpi=180)
    bars = ax.bar(names, maes, color=[SAND, SAGE, GOLD], width=0.55)
    for bar, value in zip(bars, maes):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 1800, f"${value:,.0f}", ha="center", fontsize=9)
    ax.set_ylabel("Holdout MAE (USD)")
    ax.set_title("King County model comparison — lower is better", loc="left", fontsize=12, pad=14)
    ax.set_ylim(0, max(maes) * 1.15)
    fig.tight_layout()
    fig.savefig(REPORT_DIR / "model_comparison.png")
    plt.close(fig)

    # 2. Actual vs predicted
    fig, ax = plt.subplots(figsize=(6, 6), dpi=180)
    ax.scatter(sample["actual_price"], sample["predicted_price"], s=9, alpha=0.35, color=SAGE, edgecolors="none")
    limit = max(sample["actual_price"].max(), sample["predicted_price"].max()) * 1.02
    ax.plot([0, limit], [0, limit], color=GOLD, lw=1.4, ls="--", label="Perfect prediction")
    ax.set_xlabel("Actual price (USD)")
    ax.set_ylabel("Predicted price (USD)")
    ax.set_title("Holdout predictions", loc="left", fontsize=12, pad=12)
    ax.legend(frameon=False, fontsize=8)
    ax.ticklabel_format(style="sci", axis="both", scilimits=(0, 0))
    fig.tight_layout()
    fig.savefig(REPORT_DIR / "actual_vs_predicted.png")
    plt.close(fig)

    # 3. Residual distribution
    residual = sample["actual_price"] - sample["predicted_price"]
    fig, ax = plt.subplots(figsize=(8, 4.2), dpi=180)
    ax.hist(residual, bins=45, color=SAGE, alpha=0.8)
    ax.axvline(0, color=GOLD, lw=1.4, ls="--")
    ax.set_xlabel("Residual (actual - predicted, USD)")
    ax.set_ylabel("Count")
    ax.set_title("Residual distribution — holdout", loc="left", fontsize=12, pad=12)
    ax.ticklabel_format(style="sci", axis="x", scilimits=(0, 0))
    fig.tight_layout()
    fig.savefig(REPORT_DIR / "residual_distribution.png")
    plt.close(fig)

    # 4. TreeSHAP global importance
    top = shap["ranking"][:10][::-1]
    fig, ax = plt.subplots(figsize=(8, 5), dpi=180)
    values = [row["mean_abs_shap"] for row in top]
    labels = [row["label"] for row in top]
    ax.barh(labels, values, color=GOLD, alpha=0.88)
    for index, value in enumerate(values):
        ax.text(value + 900, index, f"${value:,.0f}", va="center", fontsize=8)
    ax.set_xlabel("Mean |SHAP| (USD)")
    ax.set_title("What moves the valuation?", loc="left", fontsize=12, pad=12)
    ax.tick_params(axis="y", labelsize=9)
    fig.tight_layout()
    fig.savefig(REPORT_DIR / "shap_importance.png")
    plt.close(fig)

    report = {
        "errors_by_price_band": errors_by(sample, "price_band"),
        "errors_by_region": errors_by(sample, "region"),
        "residual": {
            "mean": round(float(residual.mean()), 2),
            "median": round(float(residual.median()), 2),
            "std": round(float(residual.std()), 2),
            "p10": round(float(residual.quantile(0.1)), 2),
            "p90": round(float(residual.quantile(0.9)), 2),
        },
        "interval": metrics["models"]["xgboost"]["interval"],
        "figures": [
            "model_comparison.png",
            "actual_vs_predicted.png",
            "residual_distribution.png",
            "shap_importance.png",
        ],
    }
    write_json(ARTIFACT_DIR / "evaluation.json", report)

    markdown = f"""# HouseMind AI 实验结果摘要

> 以下数字均由 `ml/train.py` 在本地真实数据上运行生成，可通过重新运行脚本复现。

## 主实验：King County

- 数据：21,613 条原始记录 → {metrics['rows_clean']:,} 条清洗后记录
- 划分：{metrics['split']}
- 最终模型：{metrics['best_model_label']}，{metrics['models']['xgboost']['best_iteration']} 轮提升树
- 测试集 MAE：**${metrics['models']['xgboost']['mae']:,.0f}**
- 测试集 RMSE：**${metrics['models']['xgboost']['rmse']:,.0f}**
- 测试集 R²：**{metrics['models']['xgboost']['r2']:.4f}**
- 相对 Ridge 基线 MAE 降低：**{metrics['baseline_lift_pct']}%**
- 80% 区间：${metrics['models']['xgboost']['interval']['residual_q10']:,.0f} ~ +${metrics['models']['xgboost']['interval']['residual_q90']:,.0f}；测试集覆盖率 {metrics['models']['xgboost']['interval']['test_coverage_pct']}%

## 外部实验

| 数据集 | 目标 | 留出集 MAE | R² | 说明 |
|---|---|---:|---:|---|
| UCI Real Estate | 单位面积房价（万元新台币/坪） | {json.loads((ARTIFACT_DIR / 'uci_metrics.json').read_text())['holdout']['mae']} | {json.loads((ARTIFACT_DIR / 'uci_metrics.json').read_text())['holdout']['r2']} | 414 条，独立市场，不可与 King County 直接比较 |
| California Housing | 街区组房价中位数（USD） | ${json.loads((ARTIFACT_DIR / 'california_metrics.json').read_text())['holdout']['mae']:,.0f} | {json.loads((ARTIFACT_DIR / 'california_metrics.json').read_text())['holdout']['r2']} | 1990 年普查，目标在 500,001 美元封顶 |

## 误差切片

> 下表使用测试集前 800 套固定预览样本，用于可复现的图表与报告；总体指标仍基于全部 4,284 套。

| 价格带 | 样本数 | MAE | MAPE |
|---|---:|---:|---:|
""" + "\n".join(
        f"| {row['group']} | {row['count']} | ${row['mae']:,.0f} | {row['mape']}% |"
        for row in report["errors_by_price_band"]
    ) + """

![Model comparison](model_comparison.png)

![SHAP importance](shap_importance.png)
"""
    (REPORT_DIR / "evaluation.md").write_text(markdown, encoding="utf-8")
    print("Evaluation written:", ARTIFACT_DIR / "evaluation.json")
    for row in report["errors_by_price_band"]:
        print(row)


if __name__ == "__main__":
    main()
