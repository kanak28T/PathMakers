import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.inspection import permutation_importance
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import train_test_split


ML_DIR = Path(__file__).resolve().parent

DATA_PATH = ML_DIR / "synthetic_training_data.csv"
MODEL_PATH = ML_DIR / "model.pkl"
OUTPUT_DIR = ML_DIR / "evaluation"

OUTPUT_DIR.mkdir(exist_ok=True)


FEATURE_ORDER = [
    "gap_severity",
    "tag_similarity",
    "course_rating",
    "difficulty_match",
    "prereq_satisfaction",
]


def load_model():

    bundle = joblib.load(MODEL_PATH)

    return bundle["model"]


def load_data():

    df = pd.read_csv(DATA_PATH)

    X = df[FEATURE_ORDER].copy()

    # Must match train.py
    X["course_rating"] = X["course_rating"] / 5.0

    y = df["true_fit_score"]

    return X, y


def main():

    print("=" * 60)
    print("PathMakers ML Evaluation")
    print("=" * 60)

    model = load_model()

    X, y = load_data()

    # Same 70 / 15 / 15 split as train.py
    X_train, X_temp, y_train, y_temp = train_test_split(
        X,
        y,
        test_size=0.30,
        random_state=42,
    )

    X_val, X_test, y_val, y_test = train_test_split(
        X_temp,
        y_temp,
        test_size=0.50,
        random_state=42,
    )

    print()
    print("Dataset Split")
    print("-" * 60)

    print(f"Training : {len(X_train)}")
    print(f"Validation : {len(X_val)}")
    print(f"Test : {len(X_test)}")

    # ---------------------------------------------------------
    # TEST PREDICTIONS
    # ---------------------------------------------------------

    predictions = model.predict(X_test)

    rmse = np.sqrt(
        mean_squared_error(
            y_test,
            predictions,
        )
    )

    mae = mean_absolute_error(
        y_test,
        predictions,
    )

    r2 = r2_score(
        y_test,
        predictions,
    )

    print()
    print("Evaluation Metrics")
    print("-" * 60)

    print(f"RMSE : {rmse:.4f}")
    print(f"MAE  : {mae:.4f}")
    print(f"R²   : {r2:.4f}")

    # ---------------------------------------------------------
    # CALIBRATION PLOT
    # ---------------------------------------------------------

    plt.figure(figsize=(7, 6))

    plt.scatter(
        y_test,
        predictions,
        alpha=0.4,
    )

    minimum = min(
        y_test.min(),
        predictions.min(),
    )

    maximum = max(
        y_test.max(),
        predictions.max(),
    )

    plt.plot(
        [minimum, maximum],
        [minimum, maximum],
        linestyle="--",
    )

    plt.xlabel("Actual Fit Score")
    plt.ylabel("Predicted Fit Score")
    plt.title("PathMakers ML Calibration")

    plt.tight_layout()

    calibration_path = (
        OUTPUT_DIR / "calibration.png"
    )

    plt.savefig(
        calibration_path,
        dpi=150,
    )

    plt.close()

    print()
    print(f"Calibration plot saved: {calibration_path}")

    # ---------------------------------------------------------
    # FEATURE IMPORTANCE
    # ---------------------------------------------------------

    importance = permutation_importance(
        model,
        X_test,
        y_test,
        n_repeats=5,
        random_state=42,
        scoring="neg_mean_squared_error",
    )

    feature_importance = {}

    for feature, value in zip(
        FEATURE_ORDER,
        importance.importances_mean,
    ):
        feature_importance[feature] = float(value)

    importance_path = (
        OUTPUT_DIR / "feature_importance.json"
    )

    with open(
        importance_path,
        "w",
    ) as f:

        json.dump(
            feature_importance,
            f,
            indent=2,
        )

    print()
    print("Feature Importance")
    print("-" * 60)

    for feature, value in sorted(
        feature_importance.items(),
        key=lambda x: x[1],
        reverse=True,
    ):

        print(
            f"{feature:25s} : {value:.6f}"
        )

    print()
    print(
        f"Feature importance saved: {importance_path}"
    )

    # ---------------------------------------------------------
    # SAVE EVALUATION METRICS
    # ---------------------------------------------------------

    metrics = {
        "rmse": float(rmse),
        "mae": float(mae),
        "r2": float(r2),
        "n_train": len(X_train),
        "n_validation": len(X_val),
        "n_test": len(X_test),
    }

    metrics_path = (
        OUTPUT_DIR / "evaluation_metrics.json"
    )

    with open(
        metrics_path,
        "w",
    ) as f:

        json.dump(
            metrics,
            f,
            indent=2,
        )

    print()
    print(
        f"Evaluation metrics saved: {metrics_path}"
    )

    print()
    print("=" * 60)
    print("Evaluation completed successfully")
    print("=" * 60)


if __name__ == "__main__":
    main()