import json
from pathlib import Path

import pandas as pd


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

CAREER_FILE = BASE_DIR / "career_taxonomy.json"
COURSE_FILE = BASE_DIR / "courses.csv"
OUTPUT_FILE = BASE_DIR / "skill_aliases.csv"


# ============================================================
# HELPERS
# ============================================================

def normalize_skill(value):
    """Normalize skill names for comparison."""

    if pd.isna(value):
        return ""

    return " ".join(
        str(value)
        .lower()
        .strip()
        .split()
    )


# ============================================================
# EXPLICIT CONTROLLED ALIASES
# ============================================================
#
# IMPORTANT:
# These mappings are manually defined.
#
# No fuzzy matching.
# No automatic semantic matching.
#
# canonical O*NET skill -> Coursera source skill
#
# Confidence:
#   exact             = 1.00
#   controlled_alias  = 0.90
#
# Only aliases that are reasonably defensible are included.
# ============================================================

CONTROLLED_ALIASES = {

    # --------------------------------------------------------
    # Learning
    # --------------------------------------------------------

    "active learning": [
        "interactive learning",
    ],

    # --------------------------------------------------------
    # Coordination
    # --------------------------------------------------------

    "coordination": [
        "project coordination",
    ],

    # --------------------------------------------------------
    # Installation
    # --------------------------------------------------------

    "installation": [
        "software installation",
    ],

    # --------------------------------------------------------
    # Instructing
    # --------------------------------------------------------

    "instructing": [
        "instructional design",
    ],

    # --------------------------------------------------------
    # Judgment and Decision Making
    # --------------------------------------------------------

    "judgment and decision making": [
        "decision making",
    ],

    # --------------------------------------------------------
    # Financial Resources
    # --------------------------------------------------------

    "management of financial resources": [
        "financial management",
    ],

    # --------------------------------------------------------
    # Material Resources
    # --------------------------------------------------------

    "management of material resources": [
        "materials management",
        "resource management",
    ],

    # --------------------------------------------------------
    # Personnel Resources
    # --------------------------------------------------------

    "management of personnel resources": [
        "people management",
    ],

    # --------------------------------------------------------
    # Mathematics
    # --------------------------------------------------------

    "mathematics": [
        "advanced mathematics",
        "applied mathematics",
        "business mathematics",
        "mathematics and mathematical modeling",
    ],

    # --------------------------------------------------------
    # Monitoring
    # --------------------------------------------------------

    "monitoring": [
        "continuous monitoring",
        "event monitoring",
        "network monitoring",
        "quality monitoring",
        "system monitoring",
    ],

    # --------------------------------------------------------
    # Operation and Control
    # --------------------------------------------------------

    "operation and control": [
        "operations management",
        "process control",
    ],

    # --------------------------------------------------------
    # Operations Analysis
    # --------------------------------------------------------

    "operations analysis": [
        "business analysis",
        "operations research",
    ],

    # --------------------------------------------------------
    # Operations Monitoring
    # --------------------------------------------------------

    "operations monitoring": [
        "system monitoring",
    ],

    # --------------------------------------------------------
    # Persuasion
    # --------------------------------------------------------

    "persuasion": [
        "persuasive communication",
    ],

    # --------------------------------------------------------
    # Programming
    # --------------------------------------------------------

    "programming": [
        "computer programming",
        "computer programming tools",
        "java programming",
        "object oriented programming (oop)",
        "python programming",

        # Explicit programming-language aliases
        "c programming language",
        "c++ programming language",
        "javascript",
        "r programming",
    ],

    # --------------------------------------------------------
    # Quality Control Analysis
    # --------------------------------------------------------

    "quality control analysis": [
        "quality control",
    ],

    # --------------------------------------------------------
    # Science
    # --------------------------------------------------------

    "science": [
        "general science and research",
        "science and research",
    ],

    # --------------------------------------------------------
    # Service Orientation
    # --------------------------------------------------------

    "service orientation": [
        "customer service",
    ],

    # --------------------------------------------------------
    # Social Perceptiveness
    # --------------------------------------------------------

    "social perceptiveness": [
        "emotional intelligence",
    ],

    # --------------------------------------------------------
    # Speaking
    # --------------------------------------------------------

    "speaking": [
        "public speaking",
    ],

    # --------------------------------------------------------
    # Technology Design
    # --------------------------------------------------------

    "technology design": [
        "software architecture",
        "systems design",
        "software design",
    ],

    # --------------------------------------------------------
    # Troubleshooting
    # --------------------------------------------------------

    "troubleshooting": [
        "hardware troubleshooting",
        "network troubleshooting",
        "debugging",
    ],
}


# ============================================================
# LOAD O*NET CAREER DATA
# ============================================================

print("Loading O*NET career taxonomy...")

with open(
    CAREER_FILE,
    "r",
    encoding="utf-8",
) as f:
    career_data = json.load(f)


onet_skills = set()

for career in career_data.values():

    for skill in career.get(
        "required_skills",
        [],
    ):

        skill_name = normalize_skill(
            skill.get(
                "skill_name",
                "",
            )
        )

        if skill_name:
            onet_skills.add(
                skill_name
            )


print(
    f"O*NET unique skills: {len(onet_skills)}"
)


# ============================================================
# LOAD COURSERA DATA
# ============================================================

print("Loading Coursera courses...")

courses = pd.read_csv(
    COURSE_FILE
)

coursera_skills = set()

for value in courses[
    "skill_tags"
].dropna():

    for skill in str(
        value
    ).split("|"):

        skill = normalize_skill(
            skill
        )

        if skill:
            coursera_skills.add(
                skill
            )


print(
    f"Coursera unique skills: {len(coursera_skills)}"
)


# ============================================================
# EXACT MATCHING
# ============================================================

exact_matches = sorted(
    onet_skills
    & coursera_skills
)


# ============================================================
# CONTROLLED MATCHING
# ============================================================

controlled_matches = []

for canonical_skill, aliases in (
    CONTROLLED_ALIASES.items()
):

    canonical_skill = normalize_skill(
        canonical_skill
    )

    # Only create mappings for actual O*NET
    # skills present in the taxonomy.
    if canonical_skill not in onet_skills:
        continue

    for source_skill in aliases:

        source_skill = normalize_skill(
            source_skill
        )

        # Only map to skills that actually
        # exist in the Coursera dataset.
        if source_skill not in coursera_skills:
            continue

        # If source and canonical are already
        # exact matches, don't duplicate them.
        if source_skill == canonical_skill:
            continue

        controlled_matches.append(
            (
                canonical_skill,
                source_skill,
            )
        )


# Remove duplicates while preserving order.
controlled_matches = sorted(
    set(controlled_matches)
)


# ============================================================
# BUILD MAPPING DATA
# ============================================================

mapping_rows = []


# ------------------------------------------------------------
# Exact mappings
# ------------------------------------------------------------

for skill in exact_matches:

    mapping_rows.append(
        {
            "canonical_skill": skill,
            "source_skill": skill,
            "source": "O*NET/Coursera",
            "mapping_method": "exact",
            "confidence_score": 1.0,
        }
    )


# ------------------------------------------------------------
# Controlled mappings
# ------------------------------------------------------------

for canonical_skill, source_skill in (
    controlled_matches
):

    mapping_rows.append(
        {
            "canonical_skill": canonical_skill,
            "source_skill": source_skill,
            "source": "O*NET/Coursera",
            "mapping_method": "controlled_alias",
            "confidence_score": 0.90,
        }
    )


# ============================================================
# DATAFRAME
# ============================================================

mapping_df = pd.DataFrame(
    mapping_rows,
    columns=[
        "canonical_skill",
        "source_skill",
        "source",
        "mapping_method",
        "confidence_score",
    ],
)


# ============================================================
# REMOVE DUPLICATES
# ============================================================

mapping_df = mapping_df.drop_duplicates(
    subset=[
        "canonical_skill",
        "source_skill",
    ]
).reset_index(
    drop=True
)


# ============================================================
# MAPPING STATISTICS
# ============================================================

mapped_onet_skills = set(
    mapping_df[
        "canonical_skill"
    ]
)

unmatched_onet = sorted(
    onet_skills
    - mapped_onet_skills
)


exact_count = len(
    mapping_df[
        mapping_df[
            "mapping_method"
        ]
        == "exact"
    ]
)

controlled_count = len(
    mapping_df[
        mapping_df[
            "mapping_method"
        ]
        == "controlled_alias"
    ]
)


# ============================================================
# REPORT
# ============================================================

print("\n========================================")
print("SKILL MAPPING RESULTS")
print("========================================")

print(
    f"O*NET skills          : {len(onet_skills)}"
)

print(
    f"Coursera skills       : {len(coursera_skills)}"
)

print(
    f"Exact mappings        : {exact_count}"
)

print(
    f"Controlled mappings   : {controlled_count}"
)

print(
    f"Total mapping rows    : {len(mapping_df)}"
)

print(
    f"O*NET skills mapped   : {len(mapped_onet_skills)}"
)

print(
    f"O*NET skills unmatched: {len(unmatched_onet)}"
)


# ============================================================
# PRINT MAPPINGS
# ============================================================

print("\nMappings:")

for _, row in mapping_df.iterrows():

    print(
        f"- {row['canonical_skill']} "
        f"<- {row['source_skill']} "
        f"[{row['mapping_method']}] "
        f"confidence={row['confidence_score']:.2f}"
    )


# ============================================================
# PRINT UNMATCHED
# ============================================================

print("\nUnmatched O*NET skills:")

for skill in unmatched_onet:

    print(
        f"- {skill}"
    )


# ============================================================
# SAVE
# ============================================================

mapping_df.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8",
)


# ============================================================
# FINAL REPORT
# ============================================================

print("\n========================================")
print("Skill mapping completed")
print("========================================")

print(
    f"Output file: {OUTPUT_FILE}"
)

print(
    f"Mappings written: {len(mapping_df)}"
)

print(
    "\nIMPORTANT:"
)

print(
    "Only exact and explicitly defined "
    "controlled aliases were used."
)

print(
    "No automatic fuzzy or semantic mappings "
    "were created."
)