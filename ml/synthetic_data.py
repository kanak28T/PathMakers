"""
PathMakers — Synthetic Training Data Generator

DISTRIBUTION_NOTES:
- gap_severity follows a Beta(2, 3) distribution.
- prereq_satisfaction is correlated negatively with gap_severity
  and includes Gaussian noise, then is clipped to [0, 1].
- tag_similarity follows a Beta(2, 2) distribution.
- course_rating follows a Normal(4.2, 0.5) distribution and is
  clipped to the range [1, 5].
- difficulty_match follows a Beta(3, 2) distribution.
- true_fit_score is generated from a weighted combination of the
  features with an additional prerequisite-readiness penalty and
  Gaussian noise.

The distributions are designed to represent correlated
learner-course suitability features for the PathMak ers ML pipeline.
"""

from pathlib import Path

import numpy as np
import pandas as pd

ML_DIR = Path(__file__).resolve().parent

# feature names/ranges here match contracts.schemas.ScoringFeatures exactly -
# if that file changes, this has to change with it

RNG = np.random.default_rng(42)
N_SAMPLES = 2000


def generate_features(n):
    # gap_severity and prereq_satisfaction are negatively correlated by construction -
    # a learner with a big skill gap on a course's required skills has usually also
    # not satisfied its prerequisites. modeling that dependency (not sampling them
    # independently) is what "correlated persona distributions" means in practice.
    gap_severity = RNG.beta(a=2, b=3, size=n)
    prereq_noise = RNG.normal(0, 0.15, size=n)
    prereq_satisfaction = np.clip(1 - gap_severity + prereq_noise, 0, 1)

    tag_similarity = RNG.beta(a=2, b=2, size=n)
    course_rating = np.clip(RNG.normal(4.2, 0.5, size=n), 1.0, 5.0)
    difficulty_match = RNG.beta(a=3, b=2, size=n)

    return gap_severity, tag_similarity, course_rating, difficulty_match, prereq_satisfaction


def build_target(gap_severity, tag_similarity, course_rating, difficulty_match, prereq_satisfaction):
    # base linear combination, roughly mirrors the Day-0 stub's heuristic weights
    # so the trained model doesn't contradict the fallback it's replacing
    rating_norm = course_rating / 5.0
    base = (
        0.30 * (1 - gap_severity) +
        0.25 * tag_similarity +
        0.15 * rating_norm +
        0.20 * difficulty_match +
        0.10 * prereq_satisfaction
    )

    # non-linear penalty: recommending a course the learner isn't prerequisite-ready
    # for is much worse than the linear formula implies, especially if it's also a
    # difficulty mismatch. this interaction term is exactly the kind of pattern a
    # tree model picks up on that a plain weighted sum can't - it's the reason to
    # train a model here instead of just shipping the stub's linear heuristic
    readiness_penalty = np.where(
        (prereq_satisfaction < 0.3) & (difficulty_match < 0.5),
        0.25,
        0.0
    )

    target = np.clip(base - readiness_penalty + RNG.normal(0, 0.04, size=len(base)), 0, 1)
    return target


def main():
    gap_severity, tag_similarity, course_rating, difficulty_match, prereq_satisfaction = generate_features(N_SAMPLES)
    target = build_target(gap_severity, tag_similarity, course_rating, difficulty_match, prereq_satisfaction)

    df = pd.DataFrame({
        "gap_severity": gap_severity,
        "tag_similarity": tag_similarity,
        "course_rating": course_rating,
        "difficulty_match": difficulty_match,
        "prereq_satisfaction": prereq_satisfaction,
        "true_fit_score": target,
    })

    output_path = ML_DIR / "synthetic_training_data.csv"
    df.to_csv(output_path, index=False)
    print(f"generated {len(df)} rows -> {output_path}")
    print(df.describe().to_string())


if __name__ == "__main__":
    main()