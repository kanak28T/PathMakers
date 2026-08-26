"""
ml/score.py
===========
PathMakers — ML Scoring Interface (Frozen Contract)

OWNER: S (Person C)
STATUS: Day 2 real implementation. Loads model.pkl trained by train.py and
        computes instance-level SHAP values via shap.TreeExplainer.
        Falls back to the Day-0 heuristic stub only if model.pkl is missing,
        so nothing breaks for teammates who haven't pulled the trained model yet.

CONTRACT (DO NOT CHANGE THE SIGNATURE):
    Input  : ScoringFeatures  — Pydantic model defined in contracts/schemas.py
    Output : ScoringResult    — Pydantic model defined in contracts/schemas.py
"""

from __future__ import annotations

import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap

from contracts.schemas import ScoringFeatures, ScoringResult

logger = logging.getLogger(__name__)

_MODEL_PATH = Path(__file__).parent / "model.pkl"

_model = None
_explainer = None
_feature_order: list[str] | None = None

_FEATURE_NAMES: list[str] = [
    "gap_severity",
    "tag_similarity",
    "course_rating",
    "difficulty_match",
    "prereq_satisfaction",
]


def _load_model():
    """Lazy-load model + SHAP explainer. Returns (None, None) if not trained yet."""
    global _model, _explainer, _feature_order
    if _model is not None:
        return _model, _explainer

    if not _MODEL_PATH.exists():
        logger.warning(
            "model.pkl not found at %s — score() will return stub values. "
            "Train the model by running: python ml/train.py",
            _MODEL_PATH,
        )
        return None, None

    bundle = joblib.load(_MODEL_PATH)
    _model = bundle["model"]
    _feature_order = bundle["feature_order"]
    _explainer = shap.TreeExplainer(_model)
    logger.info("HistGradientBoosting model + SHAP explainer loaded from %s", _MODEL_PATH)
    return _model, _explainer


def _features_to_row(features: ScoringFeatures) -> pd.DataFrame:
    """Build a single-row DataFrame in the exact column order the model was trained on."""
    order = _feature_order or _FEATURE_NAMES
    values = {
        "gap_severity": features.gap_severity,
        "tag_similarity": features.tag_similarity,
        "course_rating": features.course_rating / 5.0,  # normalise, matches train.py
        "difficulty_match": features.difficulty_match,
        "prereq_satisfaction": features.prereq_satisfaction,
    }
    return pd.DataFrame([{name: values[name] for name in order}])


def _build_explanation(shap_vals: dict[str, float], score: float) -> str:
    sorted_feats = sorted(shap_vals.items(), key=lambda kv: abs(kv[1]), reverse=True)
    top_name, top_val = sorted_feats[0]
    direction = "boosted" if top_val > 0 else "penalised"
    readable = {
        "gap_severity": "skill gap severity",
        "tag_similarity": "topic alignment with your target role",
        "course_rating": "course rating",
        "difficulty_match": "difficulty alignment",
        "prereq_satisfaction": "prerequisite coverage",
    }
    feature_label = readable.get(top_name, top_name)
    return (
        f"Score {score:.2f}: primarily {direction} by {feature_label} "
        f"(SHAP {top_val:+.3f})."
    )


def score(features: ScoringFeatures) -> ScoringResult:
    model, explainer = _load_model()

    if model is None:
        # Day-0/1 stub fallback - unchanged from the original scaffold
        weights = [0.30, 0.25, 0.15, 0.20, 0.10]
        feature_array = [
            features.gap_severity,
            features.tag_similarity,
            features.course_rating / 5.0,
            features.difficulty_match,
            features.prereq_satisfaction,
        ]
        stub_score = float(max(0.0, min(1.0, sum(w * v for w, v in zip(weights, feature_array)))))
        stub_shap = {name: 0.0 for name in _FEATURE_NAMES}
        explanation = (
            f"[STUB] Heuristic score {stub_score:.2f} — "
            "train the model (python ml/train.py) for real SHAP explanations."
        )
        return ScoringResult(
            course_id=features.course_id,
            learner_id=features.learner_id,
            score=stub_score,
            shap_values=stub_shap,
            explanation_text=explanation,
        )

    row = _features_to_row(features)
    raw_score = float(model.predict(row)[0])
    real_score = max(0.0, min(1.0, raw_score))

    shap_row = explainer.shap_values(row)[0]
    shap_vals = dict(zip(row.columns, [float(v) for v in shap_row]))

    explanation = _build_explanation(shap_vals, real_score)

    return ScoringResult(
        course_id=features.course_id,
        learner_id=features.learner_id,
        score=real_score,
        shap_values=shap_vals,
        explanation_text=explanation,
    )


if __name__ == "__main__":
    sample = ScoringFeatures(
        course_id="c_001",
        learner_id="user_abc",
        gap_severity=0.87,
        tag_similarity=0.74,
        course_rating=4.6,
        difficulty_match=0.91,
        prereq_satisfaction=0.50,
    )
    result = score(sample)
    print(result.model_dump_json(indent=2))