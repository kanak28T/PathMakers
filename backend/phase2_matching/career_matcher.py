"""
Phase 2 - Career Matcher

Responsible for:
1. Loading O*NET career taxonomy
2. Reading learner diagnostic results
3. Calculating weighted career match scores
4. Identifying matched skills
5. Identifying skill gaps
6. Ranking careers
"""

from pathlib import Path
import json


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

CAREER_TAXONOMY_FILE = (
    BASE_DIR / "data" / "career_taxonomy.json"
)


# ============================================================
# LOAD CAREER TAXONOMY
# ============================================================

def load_career_taxonomy() -> dict:
    """
    Load O*NET-based career taxonomy.
    """

    with open(
        CAREER_TAXONOMY_FILE,
        "r",
        encoding="utf-8",
    ) as f:

        return json.load(f)


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_skill(skill: str) -> str:
    """
    Normalize skill names for comparison.
    """

    return skill.strip().lower()


# ============================================================
# CAREER MATCHING
# ============================================================

def calculate_career_match(
    confirmed_skills: list[str],
    weak_skills: list[str],
    career: dict,
) -> dict:
    """
    Calculate weighted career match score.

    Score is based on O*NET skill importance.

    Confirmed skills contribute positively.
    Weak skills are treated as skill gaps.

    Returns:
        career name
        match score
        matched skills
        skill gaps
        total importance
        matched importance
    """

    confirmed = {
        normalize_skill(skill)
        for skill in confirmed_skills
    }

    weak = {
        normalize_skill(skill)
        for skill in weak_skills
    }

    required_skills = career.get(
        "required_skills",
        [],
    )

    total_importance = 0.0
    matched_importance = 0.0

    matched_skills = []
    skill_gaps = []

    for skill in required_skills:

        skill_name = normalize_skill(
            skill["skill_name"]
        )

        importance = float(
            skill.get("importance", 0.0)
        )

        total_importance += importance

        if skill_name in confirmed:

            matched_importance += importance

            matched_skills.append(
                {
                    "skill_name": skill["skill_name"],
                    "importance": importance,
                }
            )

        elif skill_name in weak:

            skill_gaps.append(
                {
                    "skill_name": skill["skill_name"],
                    "importance": importance,
                    "reason": "weak",
                }
            )

        else:

            skill_gaps.append(
                {
                    "skill_name": skill["skill_name"],
                    "importance": importance,
                    "reason": "not_assessed",
                }
            )

    if total_importance == 0:

        match_score = 0.0

    else:

        match_score = (
            matched_importance
            / total_importance
        )

    return {
        "career_id": career.get(
            "career_id"
        ),
        "career_name": career.get(
            "career_name"
        ),
        "match_score": match_score,
        "matched_importance": matched_importance,
        "total_importance": total_importance,
        "matched_skills": matched_skills,
        "skill_gaps": skill_gaps,
    }


# ============================================================
# RANK CAREERS
# ============================================================

def rank_careers(
    confirmed_skills: list[str],
    weak_skills: list[str],
    top_n: int | None = None,
) -> list[dict]:
    """
    Calculate and rank all careers.

    Highest match score appears first.
    """

    taxonomy = load_career_taxonomy()

    results = []

    for career_id, career in taxonomy.items():

        career_data = dict(career)

        career_data.setdefault(
            "career_id",
            career_id,
        )

        result = calculate_career_match(
            confirmed_skills=confirmed_skills,
            weak_skills=weak_skills,
            career=career_data,
        )

        results.append(result)

    results.sort(
        key=lambda item: item["match_score"],
        reverse=True,
    )

    if top_n is not None:

        return results[:top_n]

    return results


# ============================================================
# SIMPLE DIAGNOSTIC RESULT ADAPTER
# ============================================================

def rank_from_diagnostic_result(
    diagnostic_result,
    top_n: int | None = None,
) -> list[dict]:
    """
    Rank careers directly from a DiagnosticResult object.
    """

    return rank_careers(
        confirmed_skills=diagnostic_result.confirmed_skills,
        weak_skills=diagnostic_result.weak_skills,
        top_n=top_n,
    )
