"""
Phase 1 - Learner Profiler

Responsible for:
1. Loading diagnostic questions
2. Evaluating learner answers
3. Calculating diagnostic score
4. Identifying confirmed and weak skills
5. Producing DiagnosticResult
"""

from pathlib import Path
import json

from contracts.schemas import (
    DiagnosticResult,
    LearnerProfile,
    QuestionResponse,
    DifficultyLevel,
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

QUESTIONS_FILE = (
    BASE_DIR
    / "data"
    / "questions.json"
)


# ============================================================
# QUESTION LOADING
# ============================================================

def load_questions() -> list[dict]:
    """
    Load diagnostic questions from questions.json.
    """

    with open(
        QUESTIONS_FILE,
        "r",
        encoding="utf-8",
    ) as f:

        return json.load(f)


def get_question_count() -> int:
    """
    Return the number of diagnostic questions.
    """

    return len(
        load_questions()
    )


# ============================================================
# ANSWER EVALUATION
# ============================================================

def evaluate_answer(
    question: dict,
    selected_option: str,
) -> bool:
    """
    Determine whether the selected option is correct.

    The correct answer is read directly from
    questions.json.
    """

    selected_option = (
        str(selected_option)
        .upper()
        .strip()
    )

    for option in question.get(
        "options",
        [],
    ):

        if (
            option.get("option_id")
            == selected_option
        ):

            return bool(
                option.get(
                    "is_correct",
                    False,
                )
            )

    raise ValueError(
        f"Invalid option "
        f"'{selected_option}' "
        f"for question "
        f"'{question.get('question_id', '')}'."
    )


# ============================================================
# DIAGNOSTIC RESPONSE BUILDER
# ============================================================

def build_response(
    question: dict,
    selected_option: str,
    time_spent_seconds: int,
) -> QuestionResponse:
    """
    Convert a learner's selected option into
    a validated QuestionResponse.

    is_correct is calculated automatically.
    """

    selected_option = (
        str(selected_option)
        .upper()
        .strip()
    )

    is_correct = evaluate_answer(
        question=question,
        selected_option=selected_option,
    )

    difficulty = DifficultyLevel(
        question["difficulty"]
    )

    return QuestionResponse(
        question_id=str(
            question["question_id"]
        ),
        selected_option=selected_option,
        is_correct=is_correct,
        difficulty=difficulty,
        skill_tag=str(
            question["skill_tag"]
        ).strip().lower(),
        time_spent_seconds=max(
            int(time_spent_seconds),
            0,
        ),
    )


# ============================================================
# SCORE DIAGNOSTIC
# ============================================================

def score_diagnostic(
    learner: LearnerProfile,
    responses: list[QuestionResponse],
) -> DiagnosticResult:
    """
    Calculate the learner's diagnostic result.

    Skill classification:

        confirmed_skills
            Skills answered correctly.

        weak_skills
            Skills answered incorrectly.

    Overall score:

        correct responses / total responses

    Tier breakdown:

        beginner
        intermediate
        advanced

    The returned object strictly follows the frozen
    DiagnosticResult contract.
    """

    if not responses:

        raise ValueError(
            "At least one diagnostic "
            "response is required."
        )

    # --------------------------------------------------------
    # Overall score
    # --------------------------------------------------------

    total_questions = len(
        responses
    )

    correct_count = sum(
        1
        for response in responses
        if response.is_correct
    )

    overall_score = (
        correct_count
        / total_questions
    )

    # --------------------------------------------------------
    # Confirmed skills
    # --------------------------------------------------------

    confirmed_skills = sorted(
        {
            str(response.skill_tag)
            .strip()
            .lower()
            for response in responses
            if response.is_correct
            and str(
                response.skill_tag
            ).strip()
        }
    )

    # --------------------------------------------------------
    # Weak skills
    # --------------------------------------------------------

    weak_skills = sorted(
        {
            str(response.skill_tag)
            .strip()
            .lower()
            for response in responses
            if not response.is_correct
            and str(
                response.skill_tag
            ).strip()
        }
    )

    # --------------------------------------------------------
    # Difficulty tier totals
    # --------------------------------------------------------

    tier_totals = {
        "beginner": 0,
        "intermediate": 0,
        "advanced": 0,
    }

    tier_correct = {
        "beginner": 0,
        "intermediate": 0,
        "advanced": 0,
    }

    for response in responses:

        difficulty = (
            response.difficulty.value
        )

        if difficulty not in tier_totals:
            continue

        tier_totals[
            difficulty
        ] += 1

        if response.is_correct:

            tier_correct[
                difficulty
            ] += 1

    # --------------------------------------------------------
    # Tier breakdown
    # --------------------------------------------------------

    tier_breakdown = {}

    for tier in tier_totals:

        total = tier_totals[
            tier
        ]

        if total == 0:

            tier_breakdown[
                tier
            ] = 0.0

        else:

            tier_breakdown[
                tier
            ] = (
                tier_correct[tier]
                / total
            )

    # --------------------------------------------------------
    # Final DiagnosticResult
    # --------------------------------------------------------

    return DiagnosticResult(
        learner_id=learner.learner_id,
        target_role=learner.target_role,
        confirmed_skills=confirmed_skills,
        weak_skills=weak_skills,
        overall_score=overall_score,
        tier_breakdown=tier_breakdown,
        responses=responses,
    )


# ============================================================
# BACKWARD-COMPATIBLE WRAPPER
# ============================================================

def profile_learner(
    learner: LearnerProfile,
    responses: list[QuestionResponse],
) -> DiagnosticResult:
    """
    Backward-compatible wrapper.

    Existing code using profile_learner()
    continues to work while the official
    Phase-1 function is score_diagnostic().
    """

    return score_diagnostic(
        learner=learner,
        responses=responses,
    )
