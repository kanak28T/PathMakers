"""
Phase 2 - Matching Orchestrator

Responsible for:
1. Receiving DiagnosticResult
2. Ranking careers
3. Selecting the target career
4. Analyzing skill gaps
5. Mapping O*NET skills to Coursera skills
6. Finding relevant courses
7. Producing RankedCandidateList

This module uses deterministic rule-based scoring.

Course scoring considers:
    - Career relevance
    - Skill-gap importance
    - Skill coverage
    - Difficulty alignment
    - Course rating

The ML scoring layer can be plugged in later through
ScoringFeatures / ScoringResult.
"""

from pathlib import Path
import json

import pandas as pd

from contracts.schemas import (
    DiagnosticResult,
    DifficultyLevel,
    RankedCandidateList,
    RankedCourse,
)

from backend.phase2_matching.career_matcher import (
    rank_from_diagnostic_result,
)

from backend.phase2_matching.skill_gap import (
    analyze_skill_gaps_for_career,
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

COURSES_FILE = BASE_DIR / "data" / "courses.csv"

SKILL_ALIASES_FILE = BASE_DIR / "data" / "skill_aliases.csv"

CAREER_TAXONOMY_FILE = (
    BASE_DIR / "data" / "career_taxonomy.json"
)


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_skill(skill: str) -> str:
    """
    Normalize a skill for comparison.

    Example:
        "Critical   Thinking"
        ->
        "critical thinking"
    """

    return " ".join(
        str(skill)
        .lower()
        .strip()
        .split()
    )


# ============================================================
# LOAD COURSES
# ============================================================

def load_courses() -> pd.DataFrame:
    """
    Load processed Coursera courses.
    """

    courses = pd.read_csv(COURSES_FILE)

    required_columns = {
        "course_id",
        "title",
        "provider",
        "difficulty",
        "duration_hours",
        "skill_tags",
        "rating",
        "reviews",
        "url",
    }

    missing = (
        required_columns
        - set(courses.columns)
    )

    if missing:
        raise ValueError(
            "Missing course columns: "
            f"{sorted(missing)}"
        )

    return courses


# ============================================================
# LOAD SKILL ALIASES
# ============================================================

def load_skill_aliases() -> pd.DataFrame:
    """
    Load controlled O*NET -> Coursera skill mappings.
    """

    aliases = pd.read_csv(
        SKILL_ALIASES_FILE
    )

    required_columns = {
        "canonical_skill",
        "source_skill",
        "mapping_method",
        "confidence_score",
    }

    missing = (
        required_columns
        - set(aliases.columns)
    )

    if missing:
        raise ValueError(
            "Missing skill alias columns: "
            f"{sorted(missing)}"
        )

    aliases["canonical_skill"] = (
        aliases["canonical_skill"]
        .apply(normalize_skill)
    )

    aliases["source_skill"] = (
        aliases["source_skill"]
        .apply(normalize_skill)
    )

    aliases["confidence_score"] = pd.to_numeric(
        aliases["confidence_score"],
        errors="coerce",
    ).fillna(0.0)

    return aliases


# ============================================================
# LOAD CAREER TAXONOMY
# ============================================================

def load_career_taxonomy() -> dict:
    """
    Load the O*NET career taxonomy.
    """

    with open(
        CAREER_TAXONOMY_FILE,
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


# ============================================================
# COURSE SKILL SET
# ============================================================

def course_skill_set(
    skill_tags: str,
) -> set[str]:
    """
    Convert a course's pipe-separated skill tags
    into a normalized set.
    """

    if pd.isna(skill_tags):
        return set()

    return {
        normalize_skill(skill)
        for skill in str(skill_tags).split("|")
        if normalize_skill(skill)
    }


# ============================================================
# TARGET DIFFICULTY
# ============================================================

def get_target_difficulty(
    diagnostic: DiagnosticResult,
) -> DifficultyLevel:
    """
    Estimate learner's current course difficulty
    from diagnostic tier performance.

    Highest-performing tier becomes the target tier.

    Ties favour the easier tier.
    """

    breakdown = diagnostic.tier_breakdown

    beginner = float(
        breakdown.get("beginner", 0.0)
    )

    intermediate = float(
        breakdown.get("intermediate", 0.0)
    )

    advanced = float(
        breakdown.get("advanced", 0.0)
    )

    if (
        advanced >= intermediate
        and advanced >= beginner
    ):
        return DifficultyLevel.ADVANCED

    if intermediate >= beginner:
        return DifficultyLevel.INTERMEDIATE

    return DifficultyLevel.BEGINNER


# ============================================================
# DIFFICULTY SCORE
# ============================================================

def difficulty_match_score(
    course_difficulty: str,
    target_difficulty: DifficultyLevel,
) -> float:
    """
    Calculate deterministic difficulty alignment.

    Same level      = 1.0
    One level away  = 0.7
    Two levels away = 0.4
    """

    order = {
        "beginner": 0,
        "intermediate": 1,
        "advanced": 2,
        "mixed": 1,
    }

    course_level = normalize_skill(
        course_difficulty
    )

    target_level = target_difficulty.value

    if (
        course_level not in order
        or target_level not in order
    ):
        return 0.5

    distance = abs(
        order[course_level]
        - order[target_level]
    )

    if distance == 0:
        return 1.0

    if distance == 1:
        return 0.7

    return 0.4


# ============================================================
# CAREER PROFILE SKILLS
# ============================================================

def build_career_skill_profile(
    career: dict,
) -> list[dict]:
    """
    Build normalized O*NET career skill profile.

    Each item contains:
        canonical_skill
        importance
    """

    profile = []

    for skill in career.get(
        "required_skills",
        [],
    ):
        skill_name = normalize_skill(
            skill.get(
                "skill_name",
                "",
            )
        )

        if not skill_name:
            continue

        profile.append(
            {
                "canonical_skill": skill_name,
                "importance": float(
                    skill.get(
                        "importance",
                        0.0,
                    )
                ),
            }
        )

    return profile


# ============================================================
# CAREER SKILL -> COURSERA SKILL MAPPINGS
# ============================================================

def build_course_skill_lookup(
    career_profile: list[dict],
    aliases: pd.DataFrame,
) -> dict[str, list[dict]]:
    """
    Build:

        canonical O*NET skill
            ->
        Coursera source skill mappings

    Only controlled mappings from skill_aliases.csv
    are used.

    No fuzzy matching is performed.
    """

    career_skills = {
        item["canonical_skill"]
        for item in career_profile
    }

    lookup = {}

    for _, row in aliases.iterrows():

        canonical = normalize_skill(
            row["canonical_skill"]
        )

        source = normalize_skill(
            row["source_skill"]
        )

        if (
            canonical not in career_skills
            or not source
        ):
            continue

        lookup.setdefault(
            canonical,
            [],
        ).append(
            {
                "source_skill": source,
                "confidence_score": float(
                    row["confidence_score"]
                ),
                "mapping_method": row[
                    "mapping_method"
                ],
            }
        )

    return lookup


# ============================================================
# COURSE CAREER RELEVANCE
# ============================================================

def calculate_career_relevance(
    course: pd.Series,
    career_profile: list[dict],
    aliases: pd.DataFrame,
) -> dict:
    """
    Calculate how strongly a course aligns with the
    selected career's complete O*NET skill profile.

    This is different from gap coverage.

    Example:

        Web Developer
        Programming importance = 4.12

    A course containing Python Programming receives
    career relevance through the controlled mapping:

        programming
            ->
        python programming

    Returns:
        relevance score
        matched career skills
        matched importance
        total importance
    """

    course_skills = course_skill_set(
        course["skill_tags"]
    )

    if not course_skills or not career_profile:
        return {
            "score": 0.0,
            "matched_skills": [],
            "matched_importance": 0.0,
            "total_importance": 0.0,
        }

    lookup = build_course_skill_lookup(
        career_profile=career_profile,
        aliases=aliases,
    )

    total_importance = sum(
        item["importance"]
        for item in career_profile
    )

    matched_importance = 0.0
    matched_skills = []

    for item in career_profile:

        canonical = item["canonical_skill"]
        importance = item["importance"]

        possible_mappings = lookup.get(
            canonical,
            [],
        )

        for mapping in possible_mappings:

            source_skill = mapping[
                "source_skill"
            ]

            confidence = float(
                mapping[
                    "confidence_score"
                ]
            )

            if source_skill in course_skills:

                matched_importance += (
                    importance
                    * confidence
                )

                matched_skills.append(
                    canonical
                )

                # One course skill should count
                # only once for one career skill.
                break

    matched_skills = sorted(
        set(matched_skills)
    )

    if total_importance == 0:
        relevance_score = 0.0
    else:
        relevance_score = min(
            matched_importance
            / total_importance,
            1.0,
        )

    return {
        "score": relevance_score,
        "matched_skills": matched_skills,
        "matched_importance": matched_importance,
        "total_importance": total_importance,
    }


# ============================================================
# COURSE GAP SCORE
# ============================================================

def calculate_gap_score(
    course: pd.Series,
    prioritized_gaps: list[dict],
    aliases: pd.DataFrame,
) -> dict:
    """
    Calculate how strongly a course addresses the learner's
    actual skill gaps.

    Weak and not-assessed career skills are represented by
    prioritized_gaps.

    Importance determines the weight of each gap.
    """

    course_skills = course_skill_set(
        course["skill_tags"]
    )

    if not course_skills or not prioritized_gaps:
        return {
            "score": 0.0,
            "matched_skills": [],
            "matched_importance": 0.0,
            "total_importance": 0.0,
        }

    gap_importance = {
        normalize_skill(
            gap["skill_name"]
        ): float(
            gap["importance"]
        )
        for gap in prioritized_gaps
    }

    total_importance = sum(
        gap_importance.values()
    )

    relevant_aliases = []

    for _, row in aliases.iterrows():

        canonical = normalize_skill(
            row["canonical_skill"]
        )

        if canonical not in gap_importance:
            continue

        relevant_aliases.append(
            {
                "canonical_skill": canonical,
                "source_skill": normalize_skill(
                    row["source_skill"]
                ),
                "confidence_score": float(
                    row["confidence_score"]
                ),
            }
        )

    matched_skills = []
    matched_importance = 0.0

    for mapping in relevant_aliases:

        source_skill = mapping[
            "source_skill"
        ]

        canonical = mapping[
            "canonical_skill"
        ]

        confidence = mapping[
            "confidence_score"
        ]

        if source_skill not in course_skills:
            continue

        if canonical in matched_skills:
            continue

        matched_importance += (
            gap_importance[canonical]
            * confidence
        )

        matched_skills.append(
            canonical
        )

    matched_skills = sorted(
        set(matched_skills)
    )

    if total_importance == 0:
        gap_score = 0.0
    else:
        gap_score = min(
            matched_importance
            / total_importance,
            1.0,
        )

    return {
        "score": gap_score,
        "matched_skills": matched_skills,
        "matched_importance": matched_importance,
        "total_importance": total_importance,
    }


# ============================================================
# COURSE CANDIDATE SCORING
# ============================================================

def calculate_course_score(
    course: pd.Series,
    prioritized_gaps: list[dict],
    career_profile: list[dict],
    aliases: pd.DataFrame,
    target_difficulty: DifficultyLevel,
) -> dict:
    """
    Calculate deterministic course fit score.

    Components:

        career relevance       30%
        skill-gap importance   30%
        skill coverage         25%
        difficulty match       10%
        rating                  5%

    The score is normalized to [0, 1].

    Career relevance ensures that courses are useful for
    the selected career even when some career skills were
    not assessed by the diagnostic.

    Skill-gap importance ensures that learner weaknesses
    remain the primary learning signal.
    """

    course_skills = course_skill_set(
        course["skill_tags"]
    )

    if not course_skills:
        return {
            "score": 0.0,
            "career_relevance": 0.0,
            "gap_score": 0.0,
            "skill_coverage": 0.0,
            "difficulty_match": 0.0,
            "rating_score": 0.0,
            "matched_skills": [],
        }

    career_result = calculate_career_relevance(
        course=course,
        career_profile=career_profile,
        aliases=aliases,
    )

    gap_result = calculate_gap_score(
        course=course,
        prioritized_gaps=prioritized_gaps,
        aliases=aliases,
    )

    # --------------------------------------------------------
    # Skill coverage
    #
    # Coverage is based on the number of distinct career
    # skills addressed by the course.
    # --------------------------------------------------------

    total_career_skills = len(
        career_profile
    )

    career_matched_skills = set(
        career_result["matched_skills"]
    )

    gap_matched_skills = set(
        gap_result["matched_skills"]
    )

    all_matched_skills = (
        career_matched_skills
        | gap_matched_skills
    )

    if total_career_skills == 0:
        skill_coverage = 0.0
    else:
        skill_coverage = min(
            len(all_matched_skills)
            / total_career_skills,
            1.0,
        )

    # --------------------------------------------------------
    # Difficulty
    # --------------------------------------------------------

    difficulty_score = (
        difficulty_match_score(
            course_difficulty=course[
                "difficulty"
            ],
            target_difficulty=target_difficulty,
        )
    )

    # --------------------------------------------------------
    # Rating
    # --------------------------------------------------------

    rating = float(
        course["rating"]
    )

    rating_score = max(
        0.0,
        min(
            rating / 5.0,
            1.0,
        ),
    )

    # --------------------------------------------------------
    # Final score
    # --------------------------------------------------------

    score = (
        0.30 * career_result["score"]
        + 0.30 * gap_result["score"]
        + 0.25 * skill_coverage
        + 0.10 * difficulty_score
        + 0.05 * rating_score
    )

    matched_skills = sorted(
        all_matched_skills
    )

    return {
        "score": min(
            max(score, 0.0),
            1.0,
        ),
        "career_relevance": career_result[
            "score"
        ],
        "gap_score": gap_result[
            "score"
        ],
        "skill_coverage": skill_coverage,
        "difficulty_match": difficulty_score,
        "rating_score": rating_score,
        "matched_skills": matched_skills,
    }


# ============================================================
# FIND COURSE CANDIDATES
# ============================================================

def find_course_candidates(
    prioritized_gaps: list[dict],
    career_profile: list[dict],
    courses: pd.DataFrame,
    aliases: pd.DataFrame,
    target_difficulty: DifficultyLevel,
    top_n: int = 20,
) -> list[dict]:
    """
    Find and rank courses relevant to the selected career
    and learner's prioritized skill gaps.

    A course is considered a candidate when it maps to at
    least one O*NET skill in the selected career profile.

    This prevents unrelated courses from entering the
    recommendation list merely because they match a weak
    skill in isolation.
    """

    if not career_profile:
        return []

    candidates = []

    for _, course in courses.iterrows():

        result = calculate_course_score(
            course=course,
            prioritized_gaps=prioritized_gaps,
            career_profile=career_profile,
            aliases=aliases,
            target_difficulty=target_difficulty,
        )

        if not result["matched_skills"]:
            continue

        candidates.append(
            {
                "course": course,
                "result": result,
            }
        )

    candidates.sort(
        key=lambda item: (
            item["result"]["score"],
            item["result"]["career_relevance"],
            item["result"]["gap_score"],
            item["course"]["rating"],
            item["course"]["reviews"],
        ),
        reverse=True,
    )

    return candidates[:top_n]


# ============================================================
# CONVERT TO RANKED COURSE
# ============================================================

def build_ranked_course(
    candidate: dict,
    learner_id: str,
) -> RankedCourse:
    """
    Convert an internal candidate into the frozen
    RankedCourse contract.
    """

    course = candidate["course"]
    result = candidate["result"]

    difficulty_value = normalize_skill(
        course["difficulty"]
    )

    if difficulty_value == "mixed":
        difficulty_value = "intermediate"

    difficulty = DifficultyLevel(
        difficulty_value
    )

    skill_tags = [
        skill
        for skill in str(
            course["skill_tags"]
        ).split("|")
        if skill
    ]

    # --------------------------------------------------------
    # Explanation
    # --------------------------------------------------------

    matched = result[
        "matched_skills"
    ]

    if matched:

        explanation = (
            "Recommended because it aligns "
            "with career skills: "
            + ", ".join(
                matched[:5]
            )
            + "."
        )

    else:

        explanation = (
            "Recommended based on career "
            "skill alignment."
        )

    return RankedCourse(
        course_id=str(
            course["course_id"]
        ),
        title=str(
            course["title"]
        ),
        platform="Coursera",
        difficulty=difficulty,
        duration_hours=float(
            course["duration_hours"]
        ),
        score=float(
            result["score"]
        ),
        shap_values={},
        explanation_text=explanation,
        prereq_ids=[],
        skill_tags=skill_tags,
        url=(
            ""
            if pd.isna(course["url"])
            else str(course["url"])
        ),
    )


# ============================================================
# MAIN MATCHING FUNCTION
# ============================================================

def build_ranked_candidates(
    diagnostic: DiagnosticResult,
    top_n_careers: int = 5,
    top_n_courses: int = 20,
) -> RankedCandidateList:
    """
    Main Phase 2 orchestration function.

    Produces the frozen RankedCandidateList contract.
    """

    # --------------------------------------------------------
    # Career ranking
    # --------------------------------------------------------

    career_results = rank_from_diagnostic_result(
        diagnostic,
        top_n=top_n_careers,
    )

    if not career_results:
        raise ValueError(
            "No careers were produced."
        )

    # --------------------------------------------------------
    # Select target career
    #
    # Prefer learner's requested target_role if it exists.
    # Otherwise use highest-ranked career.
    # --------------------------------------------------------

    selected_career = None

    for career in career_results:

        if (
            career["career_id"]
            == diagnostic.target_role
        ):
            selected_career = career
            break

    if selected_career is None:
        selected_career = career_results[0]

    career_id = selected_career[
        "career_id"
    ]

    # --------------------------------------------------------
    # Load career taxonomy
    # --------------------------------------------------------

    taxonomy = load_career_taxonomy()

    if career_id not in taxonomy:
        raise ValueError(
            f"Career '{career_id}' not found "
            "in career taxonomy."
        )

    career = taxonomy[career_id]

    career_profile = build_career_skill_profile(
        career
    )

    # --------------------------------------------------------
    # Skill gap analysis
    # --------------------------------------------------------

    gap_result = (
        analyze_skill_gaps_for_career(
            confirmed_skills=diagnostic.confirmed_skills,
            weak_skills=diagnostic.weak_skills,
            career_id=career_id,
        )
    )

    # --------------------------------------------------------
    # Load course data
    # --------------------------------------------------------

    courses = load_courses()
    aliases = load_skill_aliases()

    # --------------------------------------------------------
    # Target learning difficulty
    # --------------------------------------------------------

    target_difficulty = (
        get_target_difficulty(
            diagnostic
        )
    )

    # --------------------------------------------------------
    # Course candidates
    # --------------------------------------------------------

    candidates = find_course_candidates(
        prioritized_gaps=gap_result[
            "prioritized_gaps"
        ],
        career_profile=career_profile,
        courses=courses,
        aliases=aliases,
        target_difficulty=target_difficulty,
        top_n=top_n_courses,
    )

    if not candidates:
        raise ValueError(
            "No Coursera courses matched "
            "the selected career's skill profile."
        )

    # --------------------------------------------------------
    # Convert candidates to contract objects
    # --------------------------------------------------------

    ranked_courses = []

    for candidate in candidates:

        ranked_courses.append(
            build_ranked_course(
                candidate=candidate,
                learner_id=diagnostic.learner_id,
            )
        )

    # --------------------------------------------------------
    # Final contract
    # --------------------------------------------------------

    return RankedCandidateList(
        learner_id=diagnostic.learner_id,
        target_role=career_id,
        diagnostic_score=float(
            diagnostic.overall_score
        ),
        candidates=ranked_courses,
    )