"""
ml/synthetic_data.py
====================
PathMakers — Synthetic Training Data Generator

Generates 2,000 correlated (learner, course) feature-target pairs using
Beta/Normal distributions with a non-linear prerequisite penalty.
This is the weak-supervision approach: a richer heuristic generates labels,
then the model learns to recover the non-linear pattern.

OWNER: S (Person C)
OUTPUT: ml/synthetic_training_data.csv
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

RANDOM_SEED = 42
N_SAMPLES   = 2000
OUT_PATH    = Path(__file__).parent / "synthetic_training_data.csv"


def generate(n: int = N_SAMPLES, seed: int = RANDOM_SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    # ---- Correlated Beta distributions ----
    gap_severity       = rng.beta(2.0, 5.0, n)           # skewed low (most learners have small gaps)
    tag_similarity     = rng.beta(3.0, 2.0, n)           # skewed high
    course_rating_raw  = rng.beta(8.0, 2.0, n) * 5.0     # [0,5], skewed toward 4-5
    difficulty_match   = rng.beta(4.0, 4.0, n)           # roughly normal around 0.5
    prereq_satisfaction = rng.beta(5.0, 2.0, n)          # skewed high — most prereqs met

    # ---- Weak-supervision label with non-linear threshold effect ----
    base = (
        0.40 * gap_severity
        + 0.30 * tag_similarity
        + 0.15 * (course_rating_raw / 5.0)
        + 0.15 * difficulty_match
    )

    # Hard penalty: poor difficulty match tanks the score much harder than linear
    penalty_mask = difficulty_match < 0.3
    base[penalty_mask] *= 0.4

    # Prereq boost: high prereq satisfaction lifts scores for mid-range base
    prereq_boost = np.where(prereq_satisfaction > 0.7, 0.05 * prereq_satisfaction, 0.0)
    base = base + prereq_boost

    # Clip + noise
    true_fit_score = np.clip(
        base + rng.normal(0, 0.05, n), 0.0, 1.0
    )

    df = pd.DataFrame({
        "gap_severity":        gap_severity,
        "tag_similarity":      tag_similarity,
        "course_rating":       course_rating_raw,
        "difficulty_match":    difficulty_match,
        "prereq_satisfaction": prereq_satisfaction,
        "true_fit_score":      true_fit_score,
    })

    return df


if __name__ == "__main__":
    df = generate()
    df.to_csv(OUT_PATH, index=False)
    print(f"Saved {len(df)} samples to {OUT_PATH}")
    print(df.describe().round(3))
