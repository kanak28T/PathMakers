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


# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]
QUESTIONS_FILE = BASE_DIR / "data" / "questions.json"


# ------------------------------------------------------------
# Question loading
# ------------------------------------------------------------

def load_questions() -> list[dict]:
    """Load diagnostic questions from questions.json."""

    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_question_count() -> int:
    """Return the number of diagnostic questions."""

    return len(load_questions())


# ------------------------------------------------------------
# Answer evaluation
# ------------------------------------------------------------

def evaluate_answer(
    question: dict,
    selected_option: str,
) -> bool:
    """
    Determine whether the selected option is correct.

    The correct answer is read directly from questions.json.
    """

    selected_option = selected_option.upper().strip()

    for option in question["options"]:

        if option["option_id"] == selected_option:
            return bool(option["is_correct"])

    raise ValueError(
        f"Invalid option '{selected_option}' "
        f"for question '{question['question_id']}'."
    )


# ------------------------------------------------------------
# Diagnostic response builder
# ------------------------------------------------------------

def build_response(
    question: dict,
    selected_option: str,
    time_spent_seconds: int,
) -> QuestionResponse:
    """
    Convert a learner's selected option into a validated
    QuestionResponse.

    is_correct is calculated automatically.
    """

    is_correct = evaluate_answer(
        question,
        selected_option,
    )

    return QuestionResponse(
        question_id=question["question_id"],
        selected_option=selected_option.upper().strip(),
        is_correct=is_correct,
        difficulty=DifficultyLevel(question["difficulty"]),
        skill_tag=question["skill_tag"],
        time_spent_seconds=time_spent_seconds,
    )


# ------------------------------------------------------------
# Diagnostic scoring
# ------------------------------------------------------------

def profile_learner(
    learner: LearnerProfile,
    responses: list[QuestionResponse],
) -> DiagnosticResult:
    """
    Generate a DiagnosticResult from learner responses.

    A skill is considered:

        confirmed -> correct response
        weak      -> incorrect response

    Overall score:

        correct responses / total responses

    Tier breakdown:

        beginner / intermediate / advanced
    """

    if not responses:
        raise ValueError(
            "At least one diagnostic response is required."
        )

    total_questions = len(responses)

    correct_count = sum(
        1
        for response in responses
        if response.is_correct
    )

    overall_score = correct_count / total_questions

    # --------------------------------------------------------
    # Confirmed and weak skills
    # --------------------------------------------------------

    confirmed_skills = sorted(
        {
            response.skill_tag
            for response in responses
            if response.is_correct
        }
    )

    weak_skills = sorted(
        {
            response.skill_tag
            for response in responses
            if not response.is_correct
        }
    )

    # --------------------------------------------------------
    # Difficulty tier breakdown
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

        difficulty = response.difficulty.value

        if difficulty not in tier_totals:
            continue

        tier_totals[difficulty] += 1

        if response.is_correct:
            tier_correct[difficulty] += 1

    tier_breakdown = {}

    for tier in tier_totals:

        if tier_totals[tier] == 0:
            tier_breakdown[tier] = 0.0

        else:
            tier_breakdown[tier] = (
                tier_correct[tier]
                / tier_totals[tier]
            )

    # --------------------------------------------------------
    # Build final contract
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