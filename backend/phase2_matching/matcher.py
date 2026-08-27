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

The scoring model considers:
    - O*NET career skill-gap coverage
    - O*NET skill importance
    - technical skill relevance
    - career-domain relevance
    - difficulty alignment
    - course rating
"""

from pathlib import Path
import json
import re

import pandas as pd

from contracts.schemas import (
    DiagnosticResult,
    DifficultyLevel,
    RankedCandidateList,
    RankedCourse,
    ScoringFeatures,
)

from ml.score import score as ml_score

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

COURSES_FILE = (
    BASE_DIR / "data" / "courses.csv"
)

SKILL_ALIASES_FILE = (
    BASE_DIR / "data" / "skill_aliases.csv"
)

CAREER_TAXONOMY_FILE = (
    BASE_DIR / "data" / "career_taxonomy.json"
)


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_skill(
    skill: str,
) -> str:
    """Normalize a skill for comparison."""

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

    courses = pd.read_csv(
        COURSES_FILE
    )

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

    aliases[
        "canonical_skill"
    ] = aliases[
        "canonical_skill"
    ].apply(normalize_skill)

    aliases[
        "source_skill"
    ] = aliases[
        "source_skill"
    ].apply(normalize_skill)

    aliases[
        "confidence_score"
    ] = pd.to_numeric(
        aliases[
            "confidence_score"
        ],
        errors="coerce",
    ).fillna(0.0)

    return aliases


# ============================================================
# LOAD CAREER TAXONOMY
# ============================================================

def load_career_taxonomy() -> dict:
    """
    Load O*NET career taxonomy.
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
        for skill in str(
            skill_tags
        ).split("|")
        if normalize_skill(skill)
    }


# ============================================================
# TOKENIZATION
# ============================================================

STOP_WORDS = {
    "and",
    "the",
    "of",
    "to",
    "a",
    "an",
    "in",
    "for",
    "with",
    "on",
    "or",
    "by",
    "may",
    "be",
    "is",
    "are",
    "this",
    "that",
    "from",
    "as",
    "other",
    "their",
    "they",
    "will",
    "can",
    "used",
    "use",
    "into",
    "existing",
    "available",
    "large",
    "new",
    "current",
}


def tokenize_text(
    text: str,
) -> set[str]:
    """
    Convert text into normalized meaningful tokens.
    """

    if not text:
        return set()

    text = str(text).lower()

    tokens = re.findall(
        r"[a-z0-9]+",
        text,
    )

    return {
        token
        for token in tokens
        if token not in STOP_WORDS
        and len(token) > 2
    }


# ============================================================
# DOMAIN PHRASES
# ============================================================

DOMAIN_PHRASES = {
    "computer_systems_analyst": {
        "computer systems",
        "systems management",
        "systems integration",
        "system administration",
        "computer systems capabilities",
        "network concerns",
        "software",
        "data processing",
        "system integration",
        "computer applications",
    },

    "database_architect": {
        "enterprise databases",
        "data warehouse",
        "data warehouses",
        "database operations",
        "database security",
        "relational databases",
        "data models",
        "database design",
        "database infrastructure",
        "database performance",
        "query processes",
    },

    "web_developer": {
        "web development",
        "web applications",
        "web application",
        "web interfaces",
        "web interface",
        "website development",
        "websites",
        "website infrastructure",
        "front end",
        "front end web development",
        "back end web development",
        "full stack web development",
        "server side",
        "web design",
        "html and css",
        "javascript",
        "browser compatibility",
        "web performance",
    },

    "business_intelligence_analyst": {
        "business intelligence",
        "market intelligence",
        "financial intelligence",
        "data repositories",
        "data patterns",
        "data trends",
        "business analytics",
        "data analytics",
        "data reporting",
        "market analysis",
    },

    "clinical_data_manager": {
        "clinical data",
        "clinical data management",
        "health care",
        "healthcare",
        "database management",
        "clinical analysis",
        "clinical databases",
        "health data",
        "data trends",
    },
}


# ============================================================
# CAREER DOMAIN TOKENS
# ============================================================

def build_career_domain_tokens(
    career: dict,
) -> set[str]:
    """
    Build career-domain vocabulary from:
        - career name
        - career description
        - required O*NET skill names
    """

    career_name = career.get(
        "career_name",
        "",
    )

    description = career.get(
        "description",
        "",
    )

    tokens = set()

    tokens.update(
        tokenize_text(
            career_name
        )
    )

    tokens.update(
        tokenize_text(
            description
        )
    )

    for skill in career.get(
        "required_skills",
        [],
    ):

        tokens.update(
            tokenize_text(
                skill.get(
                    "skill_name",
                    "",
                )
            )
        )

    return tokens


# ============================================================
# CAREER DOMAIN PHRASES
# ============================================================

def build_career_domain_phrases(
    career: dict,
) -> set[str]:
    """
    Return explicitly defined deterministic domain phrases
    for the selected career.
    """

    career_id = career.get(
        "career_id",
        "",
    )

    phrases = DOMAIN_PHRASES.get(
        career_id,
        set(),
    )

    return {
        normalize_skill(
            phrase
        )
        for phrase in phrases
    }


# ============================================================
# COURSE TEXT
# ============================================================

def build_course_text(
    course: pd.Series,
) -> str:
    """
    Combine course title and skill tags.
    """

    title = str(
        course.get(
            "title",
            "",
        )
    )

    tags = str(
        course.get(
            "skill_tags",
            "",
        )
    ).replace(
        "|",
        " ",
    )

    return normalize_skill(
        f"{title} {tags}"
    )


# ============================================================
# CAREER DOMAIN SCORE
# ============================================================

def calculate_career_domain_score(
    course: pd.Series,
    career: dict,
) -> float:
    """
    Calculate deterministic career-domain relevance.

    Scoring:
        Explicit domain phrase match = strong signal
        Title token overlap             = medium signal
        Skill-tag token overlap         = weak signal

    This prevents generic words such as
    programming, data, systems, mathematics,
    and computer from dominating the domain score.
    """

    course_title = normalize_skill(
        course.get(
            "title",
            "",
        )
    )

    course_text = build_course_text(
        course
    )

    course_tokens = tokenize_text(
        course_text
    )

    career_tokens = (
        build_career_domain_tokens(
            career
        )
    )

    domain_phrases = (
        build_career_domain_phrases(
            career
        )
    )

    # --------------------------------------------------------
    # Explicit phrase matching
    # --------------------------------------------------------

    matched_phrases = []

    for phrase in domain_phrases:

        if phrase in course_text:

            matched_phrases.append(
                phrase
            )

    if matched_phrases:

        phrase_score = min(
            len(matched_phrases) / 3.0,
            1.0,
        )

    else:

        phrase_score = 0.0

    # --------------------------------------------------------
    # Title token overlap
    # --------------------------------------------------------

    title_tokens = tokenize_text(
        course_title
    )

    title_overlap = (
        title_tokens
        & career_tokens
    )

    title_score = min(
        len(title_overlap) / 4.0,
        1.0,
    )

    # --------------------------------------------------------
    # Course skill-tag overlap
    # --------------------------------------------------------

    tag_tokens = set()

    for skill in course_skill_set(
        course.get(
            "skill_tags",
            "",
        )
    ):

        tag_tokens.update(
            tokenize_text(
                skill
            )
        )

    tag_overlap = (
        tag_tokens
        & career_tokens
    )

    tag_score = min(
        len(tag_overlap) / 8.0,
        1.0,
    )

    # --------------------------------------------------------
    # Final domain score
    # --------------------------------------------------------

    score = (
        0.60 * phrase_score
        + 0.25 * title_score
        + 0.15 * tag_score
    )

    return min(
        max(score, 0.0),
        1.0,
    )


# ============================================================
# TECHNICAL O*NET SKILLS
# ============================================================

TECHNICAL_SKILLS = {
    "programming",
    "technology design",
    "systems analysis",
    "systems evaluation",
    "troubleshooting",
    "operations analysis",
    "operations monitoring",
    "installation",
    "equipment selection",
    "equipment maintenance",
    "repairing",
    "quality control analysis",
    "mathematics",
    "science",
    "monitoring",
    "operation and control",
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

    Highest-performing tier becomes target tier.
    Ties favour the easier tier.
    """

    breakdown = diagnostic.tier_breakdown

    beginner = float(
        breakdown.get(
            "beginner",
            0.0,
        )
    )

    intermediate = float(
        breakdown.get(
            "intermediate",
            0.0,
        )
    )

    advanced = float(
        breakdown.get(
            "advanced",
            0.0,
        )
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

    target_level = (
        target_difficulty.value
    )

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
# COURSE CANDIDATE SCORING
# ============================================================

def calculate_course_score(
    course: pd.Series,
    relevant_skills: list[dict],
    target_difficulty: DifficultyLevel,
    career: dict | None = None,
    learner_id: str = "",
    alpha: float = 0.70,
) -> dict:
    """
    Calculate hybrid course fit score.

    Final score:

        hybrid_score =
            alpha * ML model score
            + (1 - alpha) * deterministic/user-weight score

    Current deterministic/user-weight components:

        skill coverage          30%
        importance coverage     25%
        technical relevance     10%
        career-domain relevance 20%
        difficulty match        10%
        rating                   5%

    ML component:

        ScoringFeatures
        -> ml.score()
        -> trained model prediction
        -> instance-level SHAP values

    Args:
        course: Course row from courses.csv.
        relevant_skills: Prioritized O*NET skill mappings.
        target_difficulty: Learner's target difficulty level.
        career: Selected career taxonomy entry.
        learner_id: Learner identifier for ML scoring.
        alpha: Weight given to ML model score.

    Returns:
        Dictionary containing hybrid score, deterministic
        features, ML score, SHAP values and explanation.
    """

    # --------------------------------------------------------
    # Validate alpha
    # --------------------------------------------------------

    alpha = max(
        0.0,
        min(
            float(alpha),
            1.0,
        ),
    )

    # --------------------------------------------------------
    # Course skills
    # --------------------------------------------------------

    course_skills = course_skill_set(
        course["skill_tags"]
    )

    if not course_skills:

        return {
            "score": 0.0,
            "user_weight_score": 0.0,
            "model_score": 0.0,
            "alpha": alpha,
            "skill_coverage": 0.0,
            "importance_coverage": 0.0,
            "technical_relevance": 0.0,
            "career_domain_relevance": 0.0,
            "difficulty_match": 0.0,
            "rating_score": 0.0,
            "gap_severity": 1.0,
            "tag_similarity": 0.0,
            "prereq_satisfaction": 0.0,
            "matched_skills": [],
            "shap_values": {},
            "explanation_text": "",
        }

    matched_skills = []

    total_importance = 0.0
    matched_importance = 0.0

    technical_total = 0.0
    technical_matched = 0.0

    # --------------------------------------------------------
    # Evaluate O*NET career gaps
    # --------------------------------------------------------

    for skill in relevant_skills:

        canonical_skill = normalize_skill(
            skill["canonical_skill"]
        )

        source_skill = normalize_skill(
            skill["source_skill"]
        )

        importance = float(
            skill.get(
                "importance",
                0.0,
            )
        )

        confidence = float(
            skill.get(
                "confidence_score",
                0.0,
            )
        )

        total_importance += importance

        is_technical = (
            canonical_skill
            in TECHNICAL_SKILLS
        )

        if is_technical:

            technical_total += importance

        if source_skill in course_skills:

            matched_importance += (
                importance
                * confidence
            )

            matched_skills.append(
                canonical_skill
            )

            if is_technical:

                technical_matched += (
                    importance
                    * confidence
                )

    matched_skills = sorted(
        set(matched_skills)
    )

    # --------------------------------------------------------
    # Skill coverage
    # --------------------------------------------------------

    relevant_count = len(
        relevant_skills
    )

    if relevant_count == 0:

        skill_coverage = 0.0

    else:

        skill_coverage = min(
            len(matched_skills)
            / relevant_count,
            1.0,
        )

    # --------------------------------------------------------
    # Importance coverage
    # --------------------------------------------------------

    if total_importance == 0:

        importance_coverage = 0.0

    else:

        importance_coverage = min(
            matched_importance
            / total_importance,
            1.0,
        )

    # --------------------------------------------------------
    # Technical relevance
    # --------------------------------------------------------

    if technical_total == 0:

        technical_relevance = 0.0

    else:

        technical_relevance = min(
            technical_matched
            / technical_total,
            1.0,
        )

    # --------------------------------------------------------
    # Career-domain relevance
    # --------------------------------------------------------

    if career is None:

        career_domain_relevance = 0.0

    else:

        career_domain_relevance = (
            calculate_career_domain_score(
                course=course,
                career=career,
            )
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
    # Deterministic / user-weight score
    # --------------------------------------------------------

    user_weight_score = (
        0.30 * skill_coverage
        + 0.25 * importance_coverage
        + 0.10 * technical_relevance
        + 0.20 * career_domain_relevance
        + 0.10 * difficulty_score
        + 0.05 * rating_score
    )

    user_weight_score = max(
        0.0,
        min(
            user_weight_score,
            1.0,
        ),
    )

    # --------------------------------------------------------
    # Gap severity
    # --------------------------------------------------------

    gap_severity = max(
        0.0,
        min(
            1.0 - skill_coverage,
            1.0,
        ),
    )

    # --------------------------------------------------------
    # Tag similarity
    # --------------------------------------------------------

    if career is None:

        tag_similarity = 0.0

    else:

        career_required_skills = {
            normalize_skill(
                skill.get(
                    "skill_name",
                    "",
                )
            )
            for skill in career.get(
                "required_skills",
                [],
            )
        }

        career_required_skills.discard("")

        if not career_required_skills:

            tag_similarity = 0.0

        else:

            tag_similarity = (
                len(
                    course_skills
                    & career_required_skills
                )
                / len(
                    course_skills
                    | career_required_skills
                )
                if (
                    course_skills
                    | career_required_skills
                )
                else 0.0
            )

    tag_similarity = max(
        0.0,
        min(
            float(tag_similarity),
            1.0,
        ),
    )

    # --------------------------------------------------------
    # Prerequisite satisfaction
    # --------------------------------------------------------

    prereq_value = course.get(
        "prereq_ids",
        "",
    )

    if (
        pd.isna(prereq_value)
        or not str(
            prereq_value
        ).strip()
    ):

        prereq_satisfaction = 1.0

    else:

        # Current DiagnosticResult does not contain
        # completed course IDs. Therefore use matched
        # skill coverage as a conservative proxy.
        prereq_satisfaction = skill_coverage

    prereq_satisfaction = max(
        0.0,
        min(
            float(prereq_satisfaction),
            1.0,
        ),
    )

    # --------------------------------------------------------
    # Build frozen ML scoring contract
    # --------------------------------------------------------

    scoring_features = ScoringFeatures(
        course_id=str(
            course["course_id"]
        ),
        learner_id=learner_id,
        gap_severity=gap_severity,
        tag_similarity=tag_similarity,
        course_rating=rating,
        difficulty_match=difficulty_score,
        prereq_satisfaction=prereq_satisfaction,
    )

    # --------------------------------------------------------
    # Run trained ML scorer
    # --------------------------------------------------------

    ml_result = ml_score(
        scoring_features
    )

    model_score = max(
        0.0,
        min(
            float(ml_result.score),
            1.0,
        ),
    )

    # --------------------------------------------------------
    # HYBRID FINAL SCORE
    # --------------------------------------------------------

    hybrid_score = (
        alpha * model_score
        + (1.0 - alpha)
        * user_weight_score
    )

    hybrid_score = max(
        0.0,
        min(
            hybrid_score,
            1.0,
        ),
    )

    # --------------------------------------------------------
    # Final result
    # --------------------------------------------------------

    return {
        "score": hybrid_score,

        "user_weight_score": (
            user_weight_score
        ),

        "model_score": model_score,

        "alpha": alpha,

        "skill_coverage": skill_coverage,

        "importance_coverage": (
            importance_coverage
        ),

        "technical_relevance": (
            technical_relevance
        ),

        "career_domain_relevance": (
            career_domain_relevance
        ),

        "difficulty_match": (
            difficulty_score
        ),

        "rating_score": rating_score,

        "gap_severity": gap_severity,

        "tag_similarity": tag_similarity,

        "prereq_satisfaction": (
            prereq_satisfaction
        ),

        "matched_skills": matched_skills,

        "shap_values": dict(
            ml_result.shap_values
        ),

        "explanation_text": (
            ml_result.explanation_text
        ),
    }


# ============================================================
# BUILD RELEVANT COURSE SKILLS
# ============================================================

def build_relevant_skill_mappings(
    prioritized_gaps: list[dict],
    aliases: pd.DataFrame,
) -> list[dict]:
    """
    Combine prioritized career gaps with Coursera
    skill aliases.
    """

    gap_importance = {
        normalize_skill(
            gap["skill_name"]
        ): float(
            gap["importance"]
        )
        for gap in prioritized_gaps
    }

    relevant = []

    for _, row in aliases.iterrows():

        canonical = normalize_skill(
            row["canonical_skill"]
        )

        if canonical not in gap_importance:
            continue

        relevant.append(
            {
                "canonical_skill": canonical,
                "source_skill": normalize_skill(
                    row["source_skill"]
                ),
                "confidence_score": float(
                    row["confidence_score"]
                ),
                "importance": gap_importance[
                    canonical
                ],
                "mapping_method": row[
                    "mapping_method"
                ],
            }
        )

    return relevant


# ============================================================
# FIND COURSE CANDIDATES
# ============================================================

def find_course_candidates(
    prioritized_gaps: list[dict],
    courses: pd.DataFrame,
    aliases: pd.DataFrame,
    target_difficulty: DifficultyLevel,
    career: dict | None = None,
    top_n: int = 20,
    learner_id: str = "",
) -> list[dict]:
    """
    Find and rank courses relevant to the learner's
    prioritized career skill gaps.

    Each candidate is scored using the deterministic
    Phase 2 matching features and the trained ML scorer.
    """

    relevant_mappings = (
        build_relevant_skill_mappings(
            prioritized_gaps=prioritized_gaps,
            aliases=aliases,
        )
    )

    if not relevant_mappings:
        return []

    candidates = []

    for _, course in courses.iterrows():

        result = calculate_course_score(
            course=course,
            relevant_skills=relevant_mappings,
            target_difficulty=target_difficulty,
            career=career,
            learner_id=learner_id,
        )

        if result["matched_skills"]:

            candidates.append(
                {
                    "course": course,
                    "result": result,
                }
            )

    # --------------------------------------------------------
    # Remove duplicate course IDs
    # --------------------------------------------------------

    unique_candidates = {}

    for candidate in candidates:

        course = candidate["course"]

        course_id = str(
            course["course_id"]
        )

        existing = unique_candidates.get(
            course_id
        )

        if existing is None:

            unique_candidates[
                course_id
            ] = candidate

        elif (
            candidate["result"]["score"]
            > existing["result"]["score"]
        ):

            unique_candidates[
                course_id
            ] = candidate

    candidates = list(
        unique_candidates.values()
    )

    # --------------------------------------------------------
    # Ranking
    # --------------------------------------------------------

    candidates.sort(
        key=lambda item: (
            item["result"]["score"],
            item["result"][
                "career_domain_relevance"
            ],
            item["result"][
                "technical_relevance"
            ],
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
    Convert an internal candidate into the
    frozen RankedCourse contract.

    ML-generated SHAP values and explanation are
    preserved for the frontend XAI drawer.
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
        skill.strip()
        for skill in str(
            course["skill_tags"]
        ).split("|")
        if skill.strip()
    ]

    # --------------------------------------------------------
    # Preserve ML XAI output
    # --------------------------------------------------------

    shap_values = dict(
        result.get(
            "shap_values",
            {},
        )
    )

    explanation = result.get(
        "explanation_text",
        "",
    )

    # Fallback explanation if ML explanation is unavailable
    if not explanation:

        matched = result.get(
            "matched_skills",
            [],
        )

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
                "skill-gap alignment."
            )

    # --------------------------------------------------------
    # Preserve prerequisite relationships
    # --------------------------------------------------------

    prereq_value = course.get(
        "prereq_ids",
        "",
    )

    if pd.isna(prereq_value):

        prereq_ids = []

    else:

        prereq_ids = [
            prereq.strip()
            for prereq in str(
                prereq_value
            ).split("|")
            if prereq.strip()
        ]

    # --------------------------------------------------------
    # Final frozen contract
    # --------------------------------------------------------

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
        shap_values=shap_values,
        explanation_text=explanation,
        prereq_ids=prereq_ids,
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
    # Load data
    # --------------------------------------------------------

    courses = load_courses()

    aliases = load_skill_aliases()

    career_taxonomy = (
        load_career_taxonomy()
    )

    selected_career_details = dict(
        career_taxonomy.get(
            career_id,
            {},
        )
    )

    selected_career_details.setdefault(
        "career_id",
        career_id,
    )

    # --------------------------------------------------------
    # Target difficulty
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
        courses=courses,
        aliases=aliases,
        target_difficulty=target_difficulty,
        career=selected_career_details,
        top_n=top_n_courses,
        learner_id=diagnostic.learner_id,
    )

    if not candidates:

        raise ValueError(
            "No Coursera courses matched "
            "the learner's career skill gaps."
        )

    # --------------------------------------------------------
    # Convert candidates
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