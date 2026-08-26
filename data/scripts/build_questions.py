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
    with open(TAXONOMY_FILE, "r", encoding="utf-8") as f:
        taxonomy = json.load(f)

    skills = sorted(
        set(
            skill["skill_name"]
            for career in taxonomy.values()
            for skill in career["required_skills"]
        )
    )

    return skills


def build_question(skill, index, difficulty):
    template = QUESTION_TEMPLATES[difficulty]

    options = []

    for option_index, text in enumerate(template["options"]):
        options.append(
            {
                "option_id": chr(65 + option_index),
                "text": text.format(skill=skill),
                "is_correct": option_index == template["correct"],
            }
        )

    return {
        "question_id": f"q_{index:03d}",
        "question": template["question"].format(skill=skill),
        "skill_tag": skill.lower(),
        "difficulty": difficulty,
        "options": options,
    }


def main():
    print("Loading O*NET career taxonomy...")

    skills = load_skills()

    print(f"O*NET unique skills: {len(skills)}")

    questions = []

    for index, skill in enumerate(skills, start=1):

        # Distribute questions across three difficulty levels.
        position = (index - 1) % 3

        if position == 0:
            difficulty = "beginner"
        elif position == 1:
            difficulty = "intermediate"
        else:
            difficulty = "advanced"

        questions.append(
            build_question(
                skill=skill,
                index=index,
                difficulty=difficulty,
            )
        )

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(
            questions,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print("========================================")
    print("QUESTION DATASET GENERATED")
    print("========================================")
    print(f"Questions written : {len(questions)}")
    print(f"Output file       : {OUTPUT_FILE}")


if __name__ == "__main__":
    main()