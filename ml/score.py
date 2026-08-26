"""
ml/score.py
===========
PathMakers — ML Scoring Interface (Frozen Contract)

OWNER: S (Person C)
STATUS (Day 0): Stub — returns deterministic dummy values so all callers
                compile and run without a trained model.
STATUS (Day 2): S replaces the stub body with real HistGradientBoosting
                inference and SHAP value computation.

CONTRACT (DO NOT CHANGE THE SIGNATURE):
    Input  : ScoringFeatures  — Pydantic model defined in contracts/schemas.py
    Output : ScoringResult    — Pydantic model defined in contracts/schemas.py

CALLER PATTERN (Person A — phase2_matching/matcher.py):
    from ml.score import score
    from contracts.schemas import ScoringFeatures

    features = ScoringFeatures(
        course_id="c_001",
        learner_id="user_abc",
        gap_severity=0.87,
        tag_similarity=0.74,
        course_rating=4.6,
        difficulty_match=0.91,
        prereq_satisfaction=0.50,
    )
    result = score(features)
    # result.score         -> float [0, 1]
    # result.shap_values   -> dict[feature_name, shap_float]
    # result.explanation_text -> human-readable XAI sentence

SHAP CONTRACT (Day 2 requirement):
    shap_values must be instance-level (per-prediction), NOT global
    feature importances.  Use shap.TreeExplainer or shap.Explainer
    wrapping the trained HistGradientBoostingRegressor.
    Keys must exactly match the five feature field names in ScoringFeatures:
        gap_severity, tag_similarity, course_rating,
        difficulty_match, prereq_satisfaction
"""

from __future__ import annotations

import os
import logging
from pathlib import Path

from contracts.schemas import ScoringFeatures, ScoringResult

logger = logging.getLogger(__name__)

# Path where Person C will save the trained model artifact
_MODEL_PATH = Path(__file__).parent / "model.pkl"

# Module-level model cache — loaded once on first call
_model = None


def _load_model():
    """
    Lazy-load the trained model from model.pkl.
    Returns None if the model file does not exist yet (Day 0 / Day 1 behaviour).
    """
    global _model
    if _model is not None:
        return _model

    if not _MODEL_PATH.exists():
        logger.warning(
            "model.pkl not found at %s — score() will return stub values. "
            "Train the model by running: python ml/train.py",
            _MODEL_PATH,
        )
        return None

    import pickle  # noqa: PLC0415
    with open(_MODEL_PATH, "rb") as f:
        _model = pickle.load(f)
    logger.info("HistGradientBoosting model loaded from %s", _MODEL_PATH)
    return _model


# Ordered feature names — must stay in sync with train.py's feature column order
_FEATURE_NAMES: list[str] = [
    "gap_severity",
    "tag_similarity",
    "course_rating",
    "difficulty_match",
    "prereq_satisfaction",
]


def _features_to_array(features: ScoringFeatures) -> list[float]:
    """Extract feature values in the canonical column order."""
    return [
        features.gap_severity,
        features.tag_similarity,
        features.course_rating / 5.0,  # normalise rating to [0, 1]
        features.difficulty_match,
        features.prereq_satisfaction,
    ]


def _build_explanation(shap_vals: dict[str, float], score: float) -> str:
    """
    Generate a human-readable XAI sentence from the top SHAP contributors.
    Positive SHAP = pushed score up; Negative SHAP = pushed score down.
    """
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
    """
    Predict the fit score for a (learner, course) pair.

    Day 0–1 behaviour (stub):
        Returns a deterministic heuristic score based on a weighted average
        of the input features.  All SHAP values are 0.0 placeholders.

    Day 2+ behaviour (real model):
        Runs HistGradientBoostingRegressor inference and computes
        instance-level SHAP values via shap.TreeExplainer.

    Args:
        features: ScoringFeatures — all five feature fields required.

    Returns:
        ScoringResult with .score, .shap_values, and .explanation_text.
    """
    model = _load_model()
    feature_array = _features_to_array(features)

    if model is None:
        # ----------------------------------------------------------------
        # STUB IMPLEMENTATION (Day 0 / Day 1)
        # Weighted average heuristic — good enough for integration testing.
        # Replace entirely in Day 2 once model.pkl is trained.
        # ----------------------------------------------------------------
        weights = [0.30, 0.25, 0.15, 0.20, 0.10]
        stub_score = float(sum(w * v for w, v in zip(weights, feature_array)))
        stub_score = max(0.0, min(1.0, stub_score))

        stub_shap: dict[str, float] = {name: 0.0 for name in _FEATURE_NAMES}
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

    # --------------------------------------------------------------------
    # REAL IMPLEMENTATION (Day 2+) — S fills this section
    # --------------------------------------------------------------------
    import numpy as np  # noqa: PLC0415

    X = np.array(feature_array).reshape(1, -1)
    raw_score = float(model.predict(X)[0])
    real_score = max(0.0, min(1.0, raw_score))

    # Instance-level SHAP values
    # S: import shap and replace this block
    # Example:
    #   explainer = shap.TreeExplainer(model)
    #   shap_matrix = explainer.shap_values(X)   # shape (1, n_features)
    #   shap_vals = dict(zip(_FEATURE_NAMES, shap_matrix[0].tolist()))
    shap_vals: dict[str, float] = {name: 0.0 for name in _FEATURE_NAMES}
    # TODO (S, Day 2): replace the line above with real SHAP computation

    explanation = _build_explanation(shap_vals, real_score)

    return ScoringResult(
        course_id=features.course_id,
        learner_id=features.learner_id,
        score=real_score,
        shap_values=shap_vals,
        explanation_text=explanation,
    )
