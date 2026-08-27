import json
from pathlib import Path

import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import shap

ML_DIR = Path(__file__).resolve().parent

DATA_PATH = ML_DIR / "synthetic_training_data.csv"
MODEL_PATH = ML_DIR / "model.pkl"
METRICS_PATH = ML_DIR / "model_metrics.json"
TARGET_COL = "true_fit_score"

# must match contracts.schemas.ScoringFeatures field order and ml/score.py's
# _FEATURE_NAMES exactly - this is the actual frozen part of this file
FEATURE_ORDER = ["gap_severity", "tag_similarity", "course_rating", "difficulty_match", "prereq_satisfaction"]


def main():
    df = pd.read_csv(DATA_PATH)

    # normalise course_rating to [0,1] here, matching what score.py's
    # _features_to_array does at inference time - the model must be trained
    # on the same scale it'll see in production, or predictions will be off
    X = df[FEATURE_ORDER].copy()
    X["course_rating"] = X["course_rating"] / 5.0
    y = df[TARGET_COL]

    X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.3, random_state=42)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42)

    model = HistGradientBoostingRegressor(random_state=42, max_iter=200, max_depth=6, learning_rate=0.08)
    model.fit(X_train, y_train)

    val_preds = model.predict(X_val)
    test_preds = model.predict(X_test)

    val_rmse = float(np.sqrt(mean_squared_error(y_val, val_preds)))
    test_rmse = float(np.sqrt(mean_squared_error(y_test, test_preds)))
    test_mae = float(mean_absolute_error(y_test, test_preds))
    test_r2 = float(r2_score(y_test, test_preds))

    print(f"Val RMSE  : {val_rmse:.4f}")
    print(f"Test RMSE : {test_rmse:.4f}")
    print(f"Test MAE  : {test_mae:.4f}")
    print(f"Test R2   : {test_r2:.4f}")

    # sanity check that SHAP actually works on this trained model before shipping it -
    # if this explodes, better to find out now than in score.py at demo time
    explainer = shap.TreeExplainer(model)
    sample_shap = explainer.shap_values(X_test.iloc[:5])
    print(f"SHAP sanity check ok, shape: {sample_shap.shape}")

    metrics = {
        "val_rmse": val_rmse,
        "test_rmse": test_rmse,
        "test_mae": test_mae,
        "test_r2": test_r2,
        "n_train": len(X_train),
        "n_val": len(X_val),
        "n_test": len(X_test),
        "feature_order": FEATURE_ORDER,
    }
    with open(METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=2)

    joblib.dump({"model": model, "feature_order": FEATURE_ORDER}, MODEL_PATH)
    print(f"\nsaved {MODEL_PATH} and {METRICS_PATH}")

    if val_rmse >= 0.15:
        print(f"WARNING: val RMSE {val_rmse:.4f} did not hit the < 0.15 target")


if __name__ == "__main__":
    main()