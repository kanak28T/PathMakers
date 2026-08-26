import json
from pathlib import Path

import pandas as pd


# --------------------------------------------------
# Paths
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "raw"
OUTPUT_FILE = BASE_DIR / "career_taxonomy.json"


# --------------------------------------------------
# Target careers
# These are verified from O*NET 29.0
# --------------------------------------------------

TARGET_CAREERS = {
    "computer_systems_analyst": {
        "title": "Computer Systems Analysts",
        "soc_codes": ["15-1211.00"],
    },
    "database_architect": {
        "title": "Database Architects",
        "soc_codes": ["15-1243.00"],
    },
    "web_developer": {
        "title": "Web Developers",
        "soc_codes": ["15-1254.00"],
    },
    "business_intelligence_analyst": {
        "title": "Business Intelligence Analysts",
        "soc_codes": ["15-2051.01"],
    },
    "clinical_data_manager": {
        "title": "Clinical Data Managers",
        "soc_codes": ["15-2051.02"],
    },
}


# --------------------------------------------------
# Read O*NET occupation data
# --------------------------------------------------

occupation_file = RAW_DIR / "Occupation Data.txt"

occupations = pd.read_csv(
    occupation_file,
    sep="\t",
)

occupations["O*NET-SOC Code"] = (
    occupations["O*NET-SOC Code"]
    .astype(str)
    .str.strip()
)


# --------------------------------------------------
# Read O*NET skills
# --------------------------------------------------

skills_file = RAW_DIR / "Skills.txt"

skill_columns = [
    "soc",
    "element_id",
    "element_name",
    "scale_id",
    "data_value",
    "n",
    "std_error",
    "lower_ci",
    "upper_ci",
    "suppress",
    "not_relevant",
    "date",
    "domain_source",
]

skills = pd.read_csv(
    skills_file,
    sep="\t",
    names=skill_columns,
    skiprows=1,
)

skills["soc"] = skills["soc"].astype(str).str.strip()
skills["scale_id"] = skills["scale_id"].astype(str).str.strip()
skills["element_name"] = skills["element_name"].astype(str).str.strip()

skills["data_value"] = pd.to_numeric(
    skills["data_value"],
    errors="coerce",
)


# --------------------------------------------------
# Keep only Importance (IM)
# --------------------------------------------------

importance = skills[
    skills["scale_id"] == "IM"
].copy()


# --------------------------------------------------
# Build career taxonomy
# --------------------------------------------------

taxonomy = {}

for career_id, career_info in TARGET_CAREERS.items():

    soc_codes = career_info["soc_codes"]

    occupation_rows = occupations[
        occupations["O*NET-SOC Code"].isin(soc_codes)
    ]

    if occupation_rows.empty:
        print(
            f"WARNING: No occupation found for {career_id}"
        )
        continue

    career_title = career_info["title"]

    descriptions = (
        occupation_rows["Description"]
        .dropna()
        .astype(str)
        .tolist()
    )

    career_skills = importance[
        importance["soc"].isin(soc_codes)
    ].copy()

    career_skills = career_skills[
        ["soc", "element_id", "element_name", "data_value"]
    ]

    career_skills = career_skills.rename(
        columns={
            "soc": "soc_code",
            "element_id": "element_id",
            "element_name": "skill_name",
            "data_value": "importance",
        }
    )

    career_skills["importance"] = career_skills[
        "importance"
    ].round(2)

    # Remove duplicate skill rows if present
    career_skills = career_skills.drop_duplicates(
        subset=["soc_code", "element_id", "skill_name"]
    )

    taxonomy[career_id] = {
        "career_id": career_id,
        "career_name": career_title,
        "onet_soc_codes": soc_codes,
        "description": descriptions[0] if descriptions else "",
        "required_skills": career_skills.to_dict(
            orient="records"
        ),
        "source": "O*NET 29.0",
    }


# --------------------------------------------------
# Save JSON
# --------------------------------------------------

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        taxonomy,
        f,
        indent=2,
        ensure_ascii=False,
    )


# --------------------------------------------------
# Summary
# --------------------------------------------------

print("\nCareer taxonomy generated successfully.")
print(f"Output: {OUTPUT_FILE}")
print(f"Careers: {len(taxonomy)}")

for career_id, career in taxonomy.items():
    print(
        f"- {career['career_name']}: "
        f"{len(career['required_skills'])} skills"
    )