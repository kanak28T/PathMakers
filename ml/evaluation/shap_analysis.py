import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap

from sklearn.model_selection import train_test_split


ML_DIR = Path(__file__).resolve().parent.parent

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

    X["course_rating"] = X["course_rating"] / 5.0

    y = df["true_fit_score"]

    return X, y


def main():

    print("=" * 60)
    print("PathMakers SHAP Analysis")
    print("=" * 60)

    model = load_model()

    X, y = load_data()

    _, X_temp, _, y_temp = train_test_split(
        X,
        y,
        test_size=0.30,
        random_state=42,
    )

    _, X_test, _, _ = train_test_split(
        X_temp,
        y_temp,
        test_size=0.50,
        random_state=42,
    )

    print(f"Test samples: {len(X_test)}")

    print()
    print("Calculating SHAP values...")

    explainer = shap.TreeExplainer(model)

    shap_values = explainer.shap_values(X_test)

    shap_values = np.asarray(shap_values)

    print(f"SHAP matrix shape: {shap_values.shape}")

    # ---------------------------------------------------------
    # FEATURE CONTRIBUTION SUMMARY
    # ---------------------------------------------------------

    summary = {}

    for i, feature in enumerate(FEATURE_ORDER):

        values = shap_values[:, i]

        summary[feature] = {
            "mean_abs_shap": float(
                np.mean(np.abs(values))
            ),
            "mean_shap": float(
                np.mean(values)
            ),
            "positive_fraction": float(
                np.mean(values > 0)
            ),
            "negative_fraction": float(
                np.mean(values < 0)
            ),
            "min_shap": float(
                np.min(values)
            ),
            "max_shap": float(
                np.max(values)
            ),
        }

    output_path = (
        OUTPUT_DIR /
        "shap_feature_distribution.json"
    )

    with open(output_path, "w") as f:

        json.dump(
            summary,
            f,
            indent=2,
        )

    print()
    print("Feature Contribution Distribution")
    print("-" * 60)

    for feature in sorted(
        summary,
        key=lambda name:
            summary[name]["mean_abs_shap"],
        reverse=True,
    ):

        values = summary[feature]

        print(
            f"{feature:25s} "
            f"mean|SHAP|={values['mean_abs_shap']:.5f} "
            f"mean={values['mean_shap']:+.5f}"
        )

    print()
    print(
        f"Saved: {output_path}"
    )

    print()
    print("=" * 60)
    print("SHAP analysis completed")
    print("=" * 60)


if __name__ == "__main__":
    main()