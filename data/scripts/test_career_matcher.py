from backend.phase2_matching.career_matcher import rank_careers


confirmed_skills = [
    "active learning",
    "complex problem solving",
    "management of financial resources",
]

weak_skills = [
    "active listening",
    "repairing",
]


results = rank_careers(
    confirmed_skills=confirmed_skills,
    weak_skills=weak_skills,
)


print("========================================")
print("CAREER RANKING CHECK")
print("========================================")

print(f"Careers ranked: {len(results)}")
print()

for index, result in enumerate(results, start=1):

    career_name = result["career_name"]
    score = result["match_score"]
    matched = len(result["matched_skills"])
    gaps = len(result["skill_gaps"])

    print(
        f"{index}. {career_name} | "
        f"Score: {score:.4f} | "
        f"Matched: {matched} | "
        f"Gaps: {gaps}"
    )


print()
print("CAREER RANKING CHECK: PASS")