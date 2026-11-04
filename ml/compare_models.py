"""Additional validation: geographic holdout and model comparison artifacts."""
from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupShuffleSplit
from xgboost import XGBRegressor

from common import ARTIFACT_DIR, RANDOM_STATE, build_zip_stats, engineer_features, load_king_county, write_json

PARAMS = dict(
    n_estimators=900,
    max_depth=6,
    learning_rate=0.03,
    subsample=0.8,
    colsample_bytree=0.8,
    min_child_weight=3,
    reg_lambda=1.0,
    objective="reg:squarederror",
    tree_method="hist",
    n_jobs=-1,
    random_state=RANDOM_STATE,
)


def metrics(y_true, y_pred) -> dict:
    return {
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 2),
        "rmse": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 2),
        "r2": round(float(r2_score(y_true, y_pred)), 4),
    }


def main() -> None:
    frame = load_king_county()
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=RANDOM_STATE)
    train_idx, test_idx = next(splitter.split(frame, groups=frame["zipcode"]))
    train, test = frame.iloc[train_idx].copy(), frame.iloc[test_idx].copy()
    zip_stats = build_zip_stats(train)
    X_train = engineer_features(train, zip_stats)
    X_test = engineer_features(test, zip_stats)
    y_train, y_test = train["price"], test["price"]
    model = XGBRegressor(**PARAMS)
    model.fit(X_train, y_train, verbose=False)
    pred = model.predict(X_test)
    unseen = sorted(set(test["zipcode"].astype(str)) - set(train["zipcode"].astype(str)))
    payload = {
        "experiment": "unseen-zipcode geographic holdout",
        "purpose": "检验模型在训练集中未出现过的邮编子市场上的泛化能力，比随机切分更严格。",
        "split": "GroupShuffleSplit by zipcode, 80/20",
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "unseen_zipcodes": unseen,
        "metrics": metrics(y_test, pred),
        "random_split_reference": None,
        "caveat": "未见邮编会回退到全局邮编基准价，因此该结果代表冷启动场景的下界水平，而非正式估值精度。",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        import json
        king = json.loads((ARTIFACT_DIR / "king_county_metrics.json").read_text())
        payload["random_split_reference"] = {
            "mae": king["models"]["xgboost"]["mae"],
            "r2": king["models"]["xgboost"]["r2"],
        }
    except Exception:
        pass
    write_json(ARTIFACT_DIR / "generalization.json", payload)
    print("Geographic holdout:", payload["metrics"], f"unseen zips={len(unseen)}")


if __name__ == "__main__":
    main()
