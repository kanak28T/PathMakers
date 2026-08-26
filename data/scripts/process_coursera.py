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


# ============================================================
# HELPERS
# ============================================================

def normalize_text(value):
    """Normalize whitespace without changing the meaning."""
    if pd.isna(value):
        return ""

    value = str(value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize_skill(skill):
    """Create a consistent skill representation."""
    skill = normalize_text(skill)

    if not skill:
        return ""

    return skill.lower().replace("-", " ").strip()


def make_course_id(row):
    """
    Generate a deterministic internal ID from the complete
    source record.

    The ID is NOT a fabricated Coursera URL or source ID.
    It is only our internal stable identifier.

    Including the source fields that distinguish records prevents
    collisions when the same course appears with different metadata.
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
    """Convert comma-separated skills into pipe-separated canonical tags."""

    if pd.isna(value):
        return ""

    skills = str(value).split(",")

    normalized = []

    for skill in skills:

        skill = normalize_skill(skill)

        if skill and skill not in normalized:
            normalized.append(skill)

    return "|".join(normalized)


# ============================================================
# LOAD DATA
# ============================================================

print("Loading Coursera dataset...")

df = pd.read_csv(INPUT_FILE)

print(f"Input rows: {len(df)}")


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
        f"Missing required columns: {missing_columns}"
    )


# ============================================================
# MISSING VALUE CHECK
# ============================================================

missing_counts = df[required_columns].isna().sum()

if missing_counts.sum() > 0:

    print("\nWARNING: Missing values detected:")

    print(
        missing_counts[
            missing_counts > 0
        ].to_string()
    )

else:

    print("Missing values: 0")


# ============================================================
# EXACT DUPLICATE CHECK
# ============================================================

exact_duplicates = df.duplicated().sum()

print(
    f"Exact duplicate rows: {exact_duplicates}"
)


# ============================================================
# NORMALIZE TEXT FIELDS
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
# CHECK VALID SOURCE VALUES
# ============================================================

unknown_levels = sorted(
    set(df["Level"]) - set(DIFFICULTY_MAP)
)

if unknown_levels:

    raise ValueError(
        f"Unknown Level values found: {unknown_levels}"
    )


unknown_durations = sorted(
    set(df["Duration"]) - set(DURATION_MAP)
)

if unknown_durations:

    raise ValueError(
        f"Unknown Duration values found: {unknown_durations}"
    )


# ============================================================
# BUILD OUTPUT DATAFRAME
# ============================================================

courses = pd.DataFrame()

courses["course_id"] = df.apply(
    make_course_id,
    axis=1,
)

courses["title"] = df["Title"]

courses["provider"] = df["Institution"]

courses["subject"] = df["Subject"]

courses["learning_product"] = df[
    "Learning Product"
]

courses["difficulty"] = df["Level"].map(
    DIFFICULTY_MAP
)

# Preserve the original source value
courses["duration_raw"] = df["Duration"]

# Derived numerical estimate for ranking.
# The original value is always preserved above.
courses["duration_hours"] = df[
    "Duration"
].map(DURATION_MAP)

courses["skill_tags"] = df[
    "Gained Skills"
].apply(normalize_skills)

courses["rating"] = pd.to_numeric(
    df["Rate"],
    errors="coerce",
)

courses["reviews"] = pd.to_numeric(
    df["Reviews"],
    errors="coerce",
)

# The provided Coursera dataset does not contain
# a course URL column.
# Therefore we intentionally do NOT fabricate URLs.
courses["url"] = ""

courses["source"] = "Coursera Courses & Skills 2025"


# ============================================================
# FINAL VALIDATION
# ============================================================

print("\nValidating processed dataset...")

if courses["course_id"].duplicated().any():

    duplicate_ids = courses[
        courses["course_id"].duplicated(
            keep=False
        )
    ]

    print(
        duplicate_ids[
            [
                "course_id",
                "title",
                "provider",
            ]
        ].to_string(index=False)
    )

    raise ValueError(
        "Duplicate internal course IDs detected."
    )


if courses["title"].eq("").any():

    raise ValueError(
        "Empty course titles detected."
    )


if courses["skill_tags"].eq("").any():

    empty_skill_count = courses[
        "skill_tags"
    ].eq("").sum()

    print(
        f"WARNING: {empty_skill_count} courses "
        "have no skill tags."
    )


# ============================================================
# SAVE
# ============================================================

courses.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8",
)

print("\n========================================")
print("Coursera processing completed")
print("========================================")

print(
    f"Input records  : {len(df)}"
)

print(
    f"Output records : {len(courses)}"
)

print(
    f"Output file    : {OUTPUT_FILE}"
)

print(
    f"Unique courses : {courses['course_id'].nunique()}"
)

print(
    f"Courses with skills : "
    f"{courses['skill_tags'].ne('').sum()}"
)

print(
    f"Courses without skills : "
    f"{courses['skill_tags'].eq('').sum()}"
)

print(
    f"Empty URLs : "
    f"{courses['url'].eq('').sum()}"
)