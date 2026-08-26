"""
End-to-end Phase 2 Matching Test

Checks:

DiagnosticResult
    ↓
Career matching
    ↓
Skill gaps
    ↓
Coursera skill mapping
    ↓
Course recommendation
    ↓
RankedCandidateList
"""

from contracts.schemas import (
    DiagnosticResult,
    QuestionResponse,
)

from backend.phase2_matching.matcher import (
    load_courses,
    load_skill_aliases,
    build_ranked_candidates,
)


# ============================================================
# TEST DATA
# ============================================================

diagnostic = DiagnosticResult(
    learner_id="phase2-e2e-001",
    target_role="web_developer",
    confirmed_skills=[
        "active learning",
        "complex problem solving",
        "management of financial resources",
    ],
    weak_skills=[
        "active listening",
        "repairing",
    ],
    overall_score=0.60,
    tier_breakdown={
        "beginner": 0.6666666667,
        "intermediate": 1.0,
        "advanced": 0.0,
    },
    responses=[
        QuestionResponse(
            question_id="q_001",
            selected_option="A",
            is_correct=True,
            difficulty="beginner",
            skill_tag="active learning",
            time_spent_seconds=10,
        ),
        QuestionResponse(
            question_id="q_002",
            selected_option="B",
            is_correct=False,
            difficulty="beginner",
            skill_tag="active listening",
            time_spent_seconds=12,
        ),
        QuestionResponse(
            question_id="q_003",
            selected_option="C",
            is_correct=True,
            difficulty="beginner",
            skill_tag="complex problem solving",
            time_spent_seconds=15,
        ),
        QuestionResponse(
            question_id="q_013",
            selected_option="A",
            is_correct=True,
            difficulty="intermediate",
            skill_tag="management of financial resources",
            time_spent_seconds=20,
        ),
        QuestionResponse(
            question_id="q_025",
            selected_option="B",
            is_correct=False,
            difficulty="advanced",
            skill_tag="repairing",
            time_spent_seconds=18,
        ),
    ],
)


# ============================================================
# TEST 1 - DATA LOADING
# ============================================================

courses = load_courses()
aliases = load_skill_aliases()

print("========================================")
print("PHASE 2 MATCHER TEST")
print("========================================")

print(
    f"Courses loaded: {len(courses)}"
)

print(
    f"Skill mappings loaded: {len(aliases)}"
)

assert len(courses) == 3404
assert len(aliases) >= 8

print("Data loading: PASS")


# ============================================================
# TEST 2 - BUILD CANDIDATES
# ============================================================

result = build_ranked_candidates(
    diagnostic=diagnostic,
    top_n_careers=5,
    top_n_courses=10,
)


print(
    f"Candidates generated: "
    f"{len(result.candidates)}"
)

assert len(result.candidates) > 0

print("Candidate generation: PASS")


# ============================================================
# TEST 3 - CONTRACT VALIDATION
# ============================================================

assert (
    result.learner_id
    == diagnostic.learner_id
)

assert (
    result.target_role
    == diagnostic.target_role
)

assert (
    result.diagnostic_score
    == diagnostic.overall_score
)

print("RankedCandidateList contract: PASS")


# ============================================================
# TEST 4 - COURSE VALIDATION
# ============================================================

course_ids = set()

for candidate in result.candidates:

    assert candidate.course_id
    assert candidate.title

    assert (
        0.0
        <= candidate.score
        <= 1.0
    )

    assert (
        candidate.duration_hours
        >= 0.0
    )

    assert len(
        candidate.skill_tags
    ) > 0

    course_ids.add(
        candidate.course_id
    )


assert len(course_ids) == len(
    result.candidates
)

print("Course validation: PASS")


# ============================================================
# TEST 5 - SCORE ORDER
# ============================================================

scores = [
    candidate.score
    for candidate in result.candidates
]

assert scores == sorted(
    scores,
    reverse=True,
)

print("Course ranking order: PASS")


# ============================================================
# DISPLAY RESULTS
# ============================================================

print()
print("========================================")
print("RECOMMENDED COURSES")
print("========================================")

for index, candidate in enumerate(
    result.candidates,
    start=1,
):

    print(
        f"{index}. "
        f"{candidate.title} | "
        f"Score: {candidate.score:.2%} | "
        f"Level: {candidate.difficulty.value}"
    )

    print(
        f"   Skills: "
        f"{', '.join(candidate.skill_tags[:5])}"
    )

    print(
        f"   Reason: "
        f"{candidate.explanation_text}"
    )


# ============================================================
# FINAL
# ============================================================

print()
print("========================================")
print("PHASE 2 MATCHER TEST: PASS")
print("========================================")