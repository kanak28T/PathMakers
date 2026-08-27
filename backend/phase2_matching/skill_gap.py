"""
Phase 2 - Skill Gap Analyzer

Responsible for:
1. Loading O*NET career requirements
2. Comparing learner skills with career requirements
3. Identifying weak skills
4. Identifying unassessed skills
5. Prioritizing skill gaps using O*NET importance
6. Producing a clean internal skill-gap report
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
# NORMALIZATION
# ============================================================

def normalize_skill(skill: str) -> str:
    """
    Normalize a skill name for reliable comparison.
    """

    return str(skill).strip().lower()


# ============================================================
# LOAD TAXONOMY
# ============================================================

def load_career_taxonomy() -> dict:
    """
    Load the O*NET-based career taxonomy.
    """

    with open(
        CAREER_TAXONOMY_FILE,
        "r",
        encoding="utf-8",
    ) as f:

        return json.load(f)


# ============================================================
# FIND CAREER
# ============================================================

def get_career(
    career_id: str,
) -> dict:
    """
    Return a single career from the taxonomy.

    Raises:
        ValueError if the career does not exist.
    """

    taxonomy = load_career_taxonomy()

    if career_id not in taxonomy:

        raise ValueError(
            f"Unknown career_id: {career_id}"
        )

    career = dict(taxonomy[career_id])

    career.setdefault(
        "career_id",
        career_id,
    )

    return career


# ============================================================
# ANALYZE SKILL GAPS
# ============================================================

def analyze_skill_gaps(
    confirmed_skills: list[str],
    weak_skills: list[str],
    career: dict,
) -> dict:
    """
    Analyze the learner's skill gaps for one career.

    Categories:

        matched
            Learner has confirmed the skill.

        weak
            Learner was assessed but performed poorly.

        not_assessed
            Skill is required by the career but was
            neither confirmed nor marked weak.

    Skill gaps are sorted by O*NET importance,
    highest importance first.
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

    matched_skills = []
    weak_gaps = []
    unassessed_gaps = []

    total_importance = 0.0
    matched_importance = 0.0
    weak_importance = 0.0
    unassessed_importance = 0.0

    for skill in required_skills:

        skill_name = skill.get(
            "skill_name",
            "",
        )

        normalized_name = normalize_skill(
            skill_name
        )

        importance = float(
            skill.get("importance", 0.0)
        )

        total_importance += importance

        # ----------------------------------------------------
        # MATCHED
        # ----------------------------------------------------

        if normalized_name in confirmed:

            matched_importance += importance

            matched_skills.append(
                {
                    "skill_name": skill_name,
                    "importance": importance,
                    "status": "matched",
                }
            )

        # ----------------------------------------------------
        # WEAK
        # ----------------------------------------------------

        elif normalized_name in weak:

            weak_importance += importance

            weak_gaps.append(
                {
                    "skill_name": skill_name,
                    "importance": importance,
                    "status": "weak",
                }
            )

        # ----------------------------------------------------
        # NOT ASSESSED
        # ----------------------------------------------------

        else:

            unassessed_importance += importance

            unassessed_gaps.append(
                {
                    "skill_name": skill_name,
                    "importance": importance,
                    "status": "not_assessed",
                }
            )

    # --------------------------------------------------------
    # Sort by importance
    # --------------------------------------------------------

    matched_skills.sort(
        key=lambda item: item["importance"],
        reverse=True,
    )

    weak_gaps.sort(
        key=lambda item: item["importance"],
        reverse=True,
    )

    unassessed_gaps.sort(
        key=lambda item: item["importance"],
        reverse=True,
    )

    # --------------------------------------------------------
    # Combined prioritized gaps
    # --------------------------------------------------------

    prioritized_gaps = (
        weak_gaps
        + unassessed_gaps
    )

    prioritized_gaps.sort(
        key=lambda item: item["importance"],
        reverse=True,
    )

    # --------------------------------------------------------
    # Score
    # --------------------------------------------------------

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
        "total_importance": total_importance,
        "matched_importance": matched_importance,
        "weak_importance": weak_importance,
        "unassessed_importance": unassessed_importance,
        "matched_skills": matched_skills,
        "weak_gaps": weak_gaps,
        "unassessed_gaps": unassessed_gaps,
        "prioritized_gaps": prioritized_gaps,
    }


# ============================================================
# ANALYZE CAREER BY ID
# ============================================================

def analyze_skill_gaps_for_career(
    confirmed_skills: list[str],
    weak_skills: list[str],
    career_id: str,
) -> dict:
    """
    Analyze skill gaps using a career_id.
    """

    career = get_career(
        career_id
    )

    return analyze_skill_gaps(
        confirmed_skills=confirmed_skills,
        weak_skills=weak_skills,
        career=career,
    )


# ============================================================
# TOP SKILL GAPS
# ============================================================

def get_top_skill_gaps(
    confirmed_skills: list[str],
    weak_skills: list[str],
    career_id: str,
    top_n: int = 10,
) -> list[dict]:
    """
    Return the highest-priority skill gaps.

    Weak and unassessed skills are combined and
    sorted by O*NET importance.
    """

    if top_n < 1:

        raise ValueError(
            "top_n must be at least 1."
        )

    result = analyze_skill_gaps_for_career(
        confirmed_skills=confirmed_skills,
        weak_skills=weak_skills,
        career_id=career_id,
    )

    return result["prioritized_gaps"][:top_n]
