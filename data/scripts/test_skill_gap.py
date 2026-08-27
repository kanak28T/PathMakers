"""
Test Phase 2 Skill Gap Analyzer

Checks:
1. Career loading
2. Skill classification
3. Weak skill detection
4. Unassessed skill detection
5. Importance-based prioritization
6. Match score
7. Top gap extraction
"""

from backend.phase2_matching.skill_gap import (
    load_career_taxonomy,
    analyze_skill_gaps,
    analyze_skill_gaps_for_career,
    get_top_skill_gaps,
)


# ============================================================
# TEST 1 - TAXONOMY
# ============================================================

taxonomy = load_career_taxonomy()

print("========================================")
print("SKILL GAP ANALYZER TEST")
print("========================================")

print(
    f"Careers loaded: {len(taxonomy)}"
)

assert len(taxonomy) == 5

print("Taxonomy loading: PASS")


# ============================================================
# TEST 2 - SAMPLE LEARNER
# ============================================================

confirmed_skills = [
    "active learning",
    "complex problem solving",
    "management of financial resources",
]

weak_skills = [
    "active listening",
    "repairing",
]


# ============================================================
# TEST 3 - GET CAREER
# ============================================================

career_id = "web_developer"

result = analyze_skill_gaps_for_career(
    confirmed_skills=confirmed_skills,
    weak_skills=weak_skills,
    career_id=career_id,
)

print(
    f"Career analyzed: {result['career_name']}"
)

assert result["career_id"] == career_id

print("Career loading: PASS")


# ============================================================
# TEST 4 - RESULT STRUCTURE
# ============================================================

required_fields = {
    "career_id",
    "career_name",
    "match_score",
    "total_importance",
    "matched_importance",
    "weak_importance",
    "unassessed_importance",
    "matched_skills",
    "weak_gaps",
    "unassessed_gaps",
    "prioritized_gaps",
}


missing_fields = (
    required_fields
    - set(result.keys())
)

assert not missing_fields, (
    f"Missing fields: {missing_fields}"
)

print("Result structure: PASS")


# ============================================================
# TEST 5 - MATCHED SKILLS
# ============================================================

matched_names = {
    skill["skill_name"].lower()
    for skill in result["matched_skills"]
}

assert "active learning" in matched_names
assert "complex problem solving" in matched_names

print("Matched skill detection: PASS")


# ============================================================
# TEST 6 - WEAK SKILLS
# ============================================================

weak_names = {
    skill["skill_name"].lower()
    for skill in result["weak_gaps"]
}

assert "active listening" in weak_names
assert "repairing" in weak_names

print("Weak skill detection: PASS")


# ============================================================
# TEST 7 - UNASSESSED SKILLS
# ============================================================

unassessed_names = {
    skill["skill_name"].lower()
    for skill in result["unassessed_gaps"]
}

assert "programming" in unassessed_names

print("Unassessed skill detection: PASS")


# ============================================================
# TEST 8 - SCORE RANGE
# ============================================================

assert 0.0 <= result["match_score"] <= 1.0

print("Match score validation: PASS")


# ============================================================
# TEST 9 - PRIORITIZED GAPS
# ============================================================

prioritized = result["prioritized_gaps"]

assert len(prioritized) > 0

importance_values = [
    skill["importance"]
    for skill in prioritized
]

assert importance_values == sorted(
    importance_values,
    reverse=True,
)

print("Gap prioritization: PASS")


# ============================================================
# TEST 10 - TOP GAPS
# ============================================================

top_gaps = get_top_skill_gaps(
    confirmed_skills=confirmed_skills,
    weak_skills=weak_skills,
    career_id=career_id,
    top_n=5,
)

assert len(top_gaps) <= 5
assert len(top_gaps) > 0

print("Top gap extraction: PASS")


# ============================================================
# DISPLAY RESULTS
# ============================================================

print()
print("========================================")
print("TOP SKILL GAPS")
print("========================================")

for index, gap in enumerate(
    top_gaps,
    start=1,
):

    print(
        f"{index}. "
        f"{gap['skill_name']} | "
        f"Importance: {gap['importance']:.2f} | "
        f"Status: {gap['status']}"
    )


print()
print("========================================")
print("SKILL GAP ANALYZER TEST: PASS")
print("========================================")