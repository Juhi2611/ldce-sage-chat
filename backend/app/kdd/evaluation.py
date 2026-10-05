"""KDD Step 5 — Pattern Evaluation.

Applies post-filtering and quality labelling to mined rules:
  - Keep rules with support >= MIN_SUPPORT, confidence >= MIN_CONFIDENCE, lift > MIN_LIFT
  - Remove redundant reciprocal rules (A→B and B→A, keep higher confidence)
  - Drop trivial intra-category rules (antecedent and consequent in same category)
  - Label each rule as "Useful" or "Weak"
"""
from typing import Any
from ..config import settings

# Category classification for trivial rule detection
ITEM_CATEGORY_MAP: dict[str, str] = {
    "Tuition": "Fees",
    "Exam Fee": "Fees",
    "Scholarship": "Aid",
    "Hostel Fee": "Hostel_Fin",
    "Hostel": "Hostel",
    "Transport": "Facilities",
    "Library": "Facilities",
    "Canteen": "Facilities",
    "Wifi": "Facilities",
    "Sports": "Facilities",
    "Placement": "Placements",
    "Package": "Placements",
    "Companies": "Placements",
    "Internship": "Placements",
    "Admission": "Admissions",
    "Eligibility": "Eligibility",
    "Documents": "Admissions",
    "Dates": "Admissions",
    "Cutoff": "Admissions",
    "Overview": "Departments",
    "Curriculum": "Academics",
    "Syllabus": "Academics",
    "Calendar": "Academics",
    "Exams": "Academics",
    "Timetable": "Academics",
    "Address": "Contact",
    "Phone": "Contact",
    "Email": "Contact",
    "Website": "Contact",
    "CSE": "Dept_CSE",
    "IT": "Dept_IT",
    "AIML": "Dept_AIML",
    "Mech": "Dept_Mech",
    "Civil": "Dept_Civil",
    "Electrical": "Dept_EE",
    "EC": "Dept_EC",
    "Chemical": "Dept_Chem",
    "Automobile": "Dept_Auto",
}


def evaluate_rules(raw_rules: list[dict]) -> list[dict]:
    """Filter, de-duplicate, and label association rules."""
    if not raw_rules:
        return []

    # 1. Apply numerical thresholds
    filtered = [
        r for r in raw_rules
        if r["support"] >= settings.min_support
        and r["confidence"] >= settings.min_confidence
        and r["lift"] > settings.min_lift
    ]

    # 2. Drop trivial rules where antecedent and consequent are in same category
    non_trivial = []
    for r in filtered:
        ant = r["antecedent"].strip()
        con = r["consequent"].strip()
        if ant == con:
            continue
        cat_ant = ITEM_CATEGORY_MAP.get(ant)
        cat_con = ITEM_CATEGORY_MAP.get(con)
        # Drop only if both belong to the exact same non-empty category
        if cat_ant and cat_con and cat_ant == cat_con:
            continue
        non_trivial.append(r)

    # 3. Remove redundant reciprocal rules (A→B and B→A), preferring higher confidence (then higher lift)
    seen: dict[frozenset, dict] = {}
    for rule in non_trivial:
        key = frozenset([rule["antecedent"], rule["consequent"]])
        if key not in seen:
            seen[key] = rule
        else:
            prev = seen[key]
            # Prefer higher confidence
            if rule["confidence"] > prev["confidence"] or (
                rule["confidence"] == prev["confidence"] and rule["lift"] > prev["lift"]
            ):
                seen[key] = rule

    deduped = list(seen.values())

    # 4. Label useful vs weak
    evaluated = []
    for rule in deduped:
        status = "Useful" if rule["lift"] > settings.min_lift and rule["confidence"] >= settings.min_confidence else "Weak"
        evaluated.append({**rule, "status": status})

    # Sort by lift × confidence descending
    evaluated.sort(key=lambda r: r["lift"] * r["confidence"], reverse=True)
    return evaluated
