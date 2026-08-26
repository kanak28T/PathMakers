import re
import hashlib
from pathlib import Path

import pandas as pd


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = BASE_DIR / "Coursera.csv"
OUTPUT_FILE = BASE_DIR / "courses.csv"


# ============================================================
# DURATION NORMALIZATION
# ============================================================

DURATION_MAP = {
    "Less Than 2 Hours": 1.0,
    "1 - 4 Weeks": 60.0,
    "1 - 3 Months": 240.0,
    "3 - 6 Months": 540.0,
}


# ============================================================
# DIFFICULTY NORMALIZATION
# ============================================================

DIFFICULTY_MAP = {
    "Beginner": "beginner",
    "Intermediate": "intermediate",
    "Advanced": "advanced",
    "Mixed": "mixed",
}


DIFFICULTY_ORDER = {
    "beginner": 0,
    "intermediate": 1,
    "advanced": 2,
    "mixed": 1,
}


# ============================================================
# HELPERS
# ============================================================

def normalize_text(value):
    """Normalize whitespace."""

    if pd.isna(value):
        return ""

    value = str(value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def normalize_skill(skill):
    """Normalize a skill name."""

    skill = normalize_text(skill)

    if not skill:
        return ""

    return (
        skill
        .lower()
        .replace("-", " ")
        .strip()
    )


def make_course_id(row):
    """
    Generate deterministic internal course ID.
    """

    raw = "|".join(
        [
            normalize_text(row["Subject"]),
            normalize_text(row["Title"]),
            normalize_text(row["Institution"]),
            normalize_text(row["Learning Product"]),
            normalize_text(row["Level"]),
            normalize_text(row["Duration"]),
            normalize_text(row["Gained Skills"]),
            normalize_text(row["Rate"]),
            normalize_text(row["Reviews"]),
        ]
    )

    digest = hashlib.sha1(
        raw.encode("utf-8")
    ).hexdigest()[:12]

    return f"coursera_{digest}"


def normalize_skills(value):
    """
    Convert comma-separated skills
    into pipe-separated normalized tags.
    """

    if pd.isna(value):
        return ""

    skills = str(value).split(",")

    normalized = []

    for skill in skills:

        skill = normalize_skill(skill)

        if skill and skill not in normalized:
            normalized.append(skill)

    return "|".join(normalized)


def skill_set(value):
    """
    Convert pipe-separated skill tags
    into a set.
    """

    return {
        normalize_skill(skill)
        for skill in str(value).split("|")
        if normalize_skill(skill)
    }


# ============================================================
# FAST PREREQUISITE GENERATION
# ============================================================

def build_prerequisite_ids(courses):
    """
    Generate deterministic prerequisite IDs.

    Fast strategy:

    - Build indexes by skill.
    - Only inspect courses sharing a skill.
    - Never compare every course with every other course.
    - Only easier courses can become prerequisites.
    - Maximum 2 prerequisites.
    - Only previous courses are considered.

    This guarantees an acyclic ordering because
    prerequisite candidates always occur earlier.
    """

    print("Preparing skill index...")

    # --------------------------------------------------------
    # Precompute skill sets
    # --------------------------------------------------------

    course_skills = {}

    for index, course in courses.iterrows():

        course_skills[index] = skill_set(
            course["skill_tags"]
        )

    # --------------------------------------------------------
    # Build skill -> course index
    # --------------------------------------------------------

    skill_index = {}

    for index, skills in course_skills.items():

        for skill in skills:

            skill_index.setdefault(
                skill,
                []
            ).append(index)

    print(
        f"Indexed skills: {len(skill_index)}"
    )

    # --------------------------------------------------------
    # Build prerequisites
    # --------------------------------------------------------

    prerequisite_map = {}

    total = len(courses)

    for index, course in courses.iterrows():

        course_id = str(
            course["course_id"]
        )

        current_level = (
            DIFFICULTY_ORDER.get(
                course["difficulty"],
                1,
            )
        )

        current_skills = course_skills[
            index
        ]

        # Beginner courses need no prerequisite.
        if current_level == 0:

            prerequisite_map[
                course_id
            ] = ""

            continue

        # ----------------------------------------------------
        # Only inspect courses sharing skills
        # ----------------------------------------------------

        candidate_indexes = set()

        for skill in current_skills:

            for candidate_index in skill_index.get(
                skill,
                [],
            ):

                if candidate_index < index:

                    candidate_indexes.add(
                        candidate_index
                    )

        ranked_candidates = []

        for candidate_index in candidate_indexes:

            previous = courses.iloc[
                candidate_index
            ]

            previous_level = (
                DIFFICULTY_ORDER.get(
                    previous["difficulty"],
                    1,
                )
            )

            # Must be easier.
            if previous_level >= current_level:
                continue

            previous_skills = course_skills[
                candidate_index
            ]

            shared_count = len(
                current_skills
                & previous_skills
            )

            if shared_count == 0:
                continue

            ranked_candidates.append(
                (
                    shared_count,
                    previous_level,
                    candidate_index,
                )
            )

        # ----------------------------------------------------
        # Select strongest prerequisites
        # ----------------------------------------------------

        ranked_candidates.sort(
            key=lambda item: (
                item[0],
                item[1],
            ),
            reverse=True,
        )

        selected = []

        for (
            shared_count,
            previous_level,
            candidate_index,
        ) in ranked_candidates[:2]:

            selected.append(
                str(
                    courses.iloc[
                        candidate_index
                    ]["course_id"]
                )
            )

        prerequisite_map[
            course_id
        ] = "|".join(selected)

        # Progress indicator
        if (
            (index + 1) % 500 == 0
            or index == total - 1
        ):

            print(
                f"Prerequisites processed: "
                f"{index + 1}/{total}"
            )

    return prerequisite_map


# ============================================================
# LOAD DATA
# ============================================================

print(
    "Loading Coursera dataset..."
)

df = pd.read_csv(
    INPUT_FILE
)

print(
    f"Input rows: {len(df)}"
)


# ============================================================
# VALIDATE SOURCE COLUMNS
# ============================================================

required_columns = [
    "Subject",
    "Title",
    "Institution",
    "Learning Product",
    "Level",
    "Duration",
    "Gained Skills",
    "Rate",
    "Reviews",
]

missing_columns = [
    column
    for column in required_columns
    if column not in df.columns
]

if missing_columns:

    raise ValueError(
        f"Missing required columns: "
        f"{missing_columns}"
    )


# ============================================================
# MISSING VALUE CHECK
# ============================================================

missing_counts = (
    df[
        required_columns
    ].isna().sum()
)

if missing_counts.sum() > 0:

    print(
        "\nWARNING: Missing values detected:"
    )

    print(
        missing_counts[
            missing_counts > 0
        ].to_string()
    )

else:

    print(
        "Missing values: 0"
    )


# ============================================================
# DUPLICATE CHECK
# ============================================================

exact_duplicates = (
    df.duplicated().sum()
)

print(
    f"Exact duplicate rows: "
    f"{exact_duplicates}"
)


# ============================================================
# NORMALIZE TEXT
# ============================================================

text_columns = [
    "Subject",
    "Title",
    "Institution",
    "Learning Product",
    "Level",
    "Duration",
]

for column in text_columns:

    df[column] = df[column].apply(
        normalize_text
    )


# ============================================================
# VALIDATE LEVELS
# ============================================================

unknown_levels = sorted(
    set(df["Level"])
    - set(DIFFICULTY_MAP)
)

if unknown_levels:

    raise ValueError(
        f"Unknown Level values found: "
        f"{unknown_levels}"
    )


# ============================================================
# VALIDATE DURATIONS
# ============================================================

unknown_durations = sorted(
    set(df["Duration"])
    - set(DURATION_MAP)
)

if unknown_durations:

    raise ValueError(
        f"Unknown Duration values found: "
        f"{unknown_durations}"
    )


# ============================================================
# BUILD COURSES DATAFRAME
# ============================================================

courses = pd.DataFrame()

courses["course_id"] = df.apply(
    make_course_id,
    axis=1,
)

courses["title"] = df[
    "Title"
]

courses["provider"] = df[
    "Institution"
]

courses["subject"] = df[
    "Subject"
]

courses["learning_product"] = df[
    "Learning Product"
]

courses["difficulty"] = df[
    "Level"
].map(
    DIFFICULTY_MAP
)

courses["duration_raw"] = df[
    "Duration"
]

courses["duration_hours"] = df[
    "Duration"
].map(
    DURATION_MAP
)

courses["skill_tags"] = df[
    "Gained Skills"
].apply(
    normalize_skills
)

courses["rating"] = pd.to_numeric(
    df["Rate"],
    errors="coerce",
)

courses["reviews"] = pd.to_numeric(
    df["Reviews"],
    errors="coerce",
)

courses["url"] = ""

courses["source"] = (
    "Coursera Courses & Skills 2025"
)


# ============================================================
# PREREQUISITES
# ============================================================

print(
    "\nBuilding prerequisite relationships..."
)

prerequisite_map = (
    build_prerequisite_ids(
        courses
    )
)

courses["prereq_ids"] = (
    courses[
        "course_id"
    ].map(
        prerequisite_map
    ).fillna("")
)


# ============================================================
# VALIDATION
# ============================================================

print(
    "\nValidating processed dataset..."
)


# ------------------------------------------------------------
# Duplicate course IDs
# ------------------------------------------------------------

if courses[
    "course_id"
].duplicated().any():

    raise ValueError(
        "Duplicate internal course IDs detected."
    )


# ------------------------------------------------------------
# Empty titles
# ------------------------------------------------------------

if courses[
    "title"
].eq("").any():

    raise ValueError(
        "Empty course titles detected."
    )


# ------------------------------------------------------------
# Empty skill tags
# ------------------------------------------------------------

empty_skill_count = (
    courses[
        "skill_tags"
    ].eq("").sum()
)

if empty_skill_count > 0:

    print(
        f"WARNING: "
        f"{empty_skill_count} courses "
        "have no skill tags."
    )


# ------------------------------------------------------------
# Validate prerequisites
# ------------------------------------------------------------

course_ids = set(
    courses[
        "course_id"
    ].astype(str)
)

for index, course in courses.iterrows():

    course_id = str(
        course["course_id"]
    )

    prereq_value = str(
        course["prereq_ids"]
    ).strip()

    if not prereq_value:
        continue

    prereq_ids = [
        item.strip()
        for item in prereq_value.split("|")
        if item.strip()
    ]

    for prereq_id in prereq_ids:

        if prereq_id not in course_ids:

            raise ValueError(
                f"Invalid prerequisite "
                f"{prereq_id} for "
                f"{course_id}"
            )

        if prereq_id == course_id:

            raise ValueError(
                f"Self prerequisite detected "
                f"for {course_id}"
            )


# ============================================================
# SAVE
# ============================================================

courses.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8",
)


# ============================================================
# SUMMARY
# ============================================================

courses_with_prereqs = (
    courses[
        "prereq_ids"
    ]
    .astype(str)
    .str.strip()
    .ne("")
    .sum()
)

courses_without_prereqs = (
    len(courses)
    - courses_with_prereqs
)


print(
    "\n========================================"
)

print(
    "Coursera processing completed"
)

print(
    "========================================"
)

print(
    f"Input records          : {len(df)}"
)

print(
    f"Output records         : {len(courses)}"
)

print(
    f"Unique courses         : "
    f"{courses['course_id'].nunique()}"
)

print(
    f"Courses with skills    : "
    f"{courses['skill_tags'].ne('').sum()}"
)

print(
    f"Courses without skills : "
    f"{empty_skill_count}"
)

print(
    f"Courses with prereqs   : "
    f"{courses_with_prereqs}"
)

print(
    f"Courses without prereqs: "
    f"{courses_without_prereqs}"
)

print(
    f"Output file            : "
    f"{OUTPUT_FILE}"
)

print(
    f"Empty URLs             : "
    f"{courses['url'].eq('').sum()}"
)