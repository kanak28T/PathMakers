import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

TAXONOMY_FILE = BASE_DIR / "career_taxonomy.json"
OUTPUT_FILE = BASE_DIR / "questions.json"


QUESTION_TEMPLATES = {
    "beginner": {
        "question": "Which statement best describes {skill}?",
        "options": [
            "It is a fundamental skill used to perform tasks related to this area.",
            "It is only useful for financial accounting.",
            "It is unrelated to professional work.",
            "It is exclusively used for hardware repair.",
        ],
        "correct": 0,
    },
    "intermediate": {
        "question": "Which situation best demonstrates the practical use of {skill}?",
        "options": [
            "Applying the skill appropriately to solve a work-related problem.",
            "Ignoring the requirements of the task.",
            "Avoiding the use of the skill completely.",
            "Performing an unrelated activity.",
        ],
        "correct": 0,
    },
    "advanced": {
        "question": "Which approach demonstrates advanced ability in {skill}?",
        "options": [
            "Applying the skill strategically to evaluate complex situations and improve outcomes.",
            "Avoiding difficult situations involving the skill.",
            "Using the skill without considering the problem context.",
            "Using an unrelated technique instead.",
        ],
        "correct": 0,
    },
}


def load_skills():
    with open(
        TAXONOMY_FILE,
        "r",
        encoding="utf-8",
    ) as f:

        taxonomy = json.load(f)

    skills = sorted(
        set(
            skill["skill_name"]
            for career in taxonomy.values()
            for skill in career["required_skills"]
        )
    )

    return skills


def build_question(
    skill,
    index,
    difficulty,
):
    template = QUESTION_TEMPLATES[
        difficulty
    ]

    options = []

    for option_index, text in enumerate(
        template["options"]
    ):

        options.append(
            {
                "option_id": chr(
                    65 + option_index
                ),
                "text": text.format(
                    skill=skill
                ),
                "is_correct": (
                    option_index
                    == template["correct"]
                ),
            }
        )

    return {
        "question_id": f"q_{index:03d}",
        "question": template[
            "question"
        ].format(skill=skill),
        "skill_tag": skill.lower(),
        "difficulty": difficulty,
        "options": options,
    }


def main():

    print(
        "Loading O*NET career taxonomy..."
    )

    skills = load_skills()

    print(
        f"O*NET unique skills: {len(skills)}"
    )

    if len(skills) == 0:
        raise ValueError(
            "No skills found in career taxonomy."
        )

    # --------------------------------------------------------
    # Generate exactly 45 questions
    # --------------------------------------------------------

    target_questions = 45

    difficulties = [
        "beginner",
        "intermediate",
        "advanced",
    ]

    questions = []

    for index in range(
        target_questions
    ):

        skill = skills[
            index % len(skills)
        ]

        difficulty = difficulties[
            index % 3
        ]

        questions.append(
            build_question(
                skill=skill,
                index=index + 1,
                difficulty=difficulty,
            )
        )

    # --------------------------------------------------------
    # Validate generated dataset
    # --------------------------------------------------------

    if len(questions) != 45:

        raise ValueError(
            "Question generation failed: "
            f"expected 45, got {len(questions)}"
        )

    tier_counts = {
        "beginner": 0,
        "intermediate": 0,
        "advanced": 0,
    }

    for question in questions:

        tier = question[
            "difficulty"
        ]

        if tier not in tier_counts:

            raise ValueError(
                f"Invalid difficulty tier: {tier}"
            )

        tier_counts[tier] += 1

    for tier, count in tier_counts.items():

        if count != 15:

            raise ValueError(
                f"{tier} must contain "
                f"15 questions, got {count}"
            )

    # --------------------------------------------------------
    # Write questions.json
    # --------------------------------------------------------

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            questions,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print(
        "========================================"
    )
    print(
        "QUESTION DATASET GENERATED"
    )
    print(
        "========================================"
    )
    print(
        f"Questions written : {len(questions)}"
    )
    print(
        f"Beginner          : {tier_counts['beginner']}"
    )
    print(
        f"Intermediate      : {tier_counts['intermediate']}"
    )
    print(
        f"Advanced          : {tier_counts['advanced']}"
    )
    print(
        f"Output file       : {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()