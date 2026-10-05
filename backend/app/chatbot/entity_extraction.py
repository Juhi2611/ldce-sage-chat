"""Rule-based entity extraction: departments and topics.

Canonical department list verified against https://ldce.ac.in (October 2025).
"""
import re
from typing import Optional

# ---------------------------------------------------------------------------
# Canonical department names (exactly 17 UG departments from ldce.ac.in)
# ---------------------------------------------------------------------------
CANONICAL_DEPARTMENTS = [
    "Artificial Intelligence and Machine Learning",
    "Automobile Engineering",
    "Biomedical Engineering",
    "Chemical Engineering",
    "Civil Engineering",
    "Computer Engineering",
    "Electrical Engineering",
    "Electronics and Communication Engineering",
    "Environmental Engineering",
    "Information Technology",
    "Instrumentation and Control Engineering",
    "Mechanical Engineering",
    "Plastic Technology",
    "Robotics and Automation",
    "Rubber Technology",
    "Science and Humanities",
    "Textile Technology",
]

# Alias → canonical department
_DEPT_ALIASES: dict[str, str] = {
    # Computer Engineering
    "computer engineering": "Computer Engineering",
    "computer": "Computer Engineering",
    "cse": "Computer Engineering",
    "ce": "Computer Engineering",
    "comp": "Computer Engineering",
    "cs": "Computer Engineering",
    # Information Technology
    "information technology": "Information Technology",
    "it": "Information Technology",
    "info tech": "Information Technology",
    # AI/ML
    "artificial intelligence machine learning": "Artificial Intelligence and Machine Learning",
    "artificial intelligence and machine learning": "Artificial Intelligence and Machine Learning",
    "ai ml": "Artificial Intelligence and Machine Learning",
    "aiml": "Artificial Intelligence and Machine Learning",
    "ai": "Artificial Intelligence and Machine Learning",
    "machine learning": "Artificial Intelligence and Machine Learning",
    # Mechanical
    "mechanical engineering": "Mechanical Engineering",
    "mechanical": "Mechanical Engineering",
    "mech": "Mechanical Engineering",
    # Civil
    "civil engineering": "Civil Engineering",
    "civil": "Civil Engineering",
    # Electrical
    "electrical engineering": "Electrical Engineering",
    "electrical": "Electrical Engineering",
    "ee": "Electrical Engineering",
    "electric": "Electrical Engineering",
    # Electronics & Communication
    "electronics and communication engineering": "Electronics and Communication Engineering",
    "electronics": "Electronics and Communication Engineering",
    "ec": "Electronics and Communication Engineering",
    "ece": "Electronics and Communication Engineering",
    "electronics communication": "Electronics and Communication Engineering",
    # Instrumentation & Control
    "instrumentation and control engineering": "Instrumentation and Control Engineering",
    "instrumentation": "Instrumentation and Control Engineering",
    "instrumentation control": "Instrumentation and Control Engineering",
    "ic": "Instrumentation and Control Engineering",
    # Chemical
    "chemical engineering": "Chemical Engineering",
    "chemical": "Chemical Engineering",
    "chem": "Chemical Engineering",
    # Automobile
    "automobile engineering": "Automobile Engineering",
    "automobile": "Automobile Engineering",
    "auto": "Automobile Engineering",
    "automotive": "Automobile Engineering",
    # Biomedical
    "biomedical engineering": "Biomedical Engineering",
    "biomedical": "Biomedical Engineering",
    "bme": "Biomedical Engineering",
    "bio": "Biomedical Engineering",
    # Environmental
    "environmental engineering": "Environmental Engineering",
    "environmental": "Environmental Engineering",
    "environment": "Environmental Engineering",
    # Plastic Technology
    "plastic technology": "Plastic Technology",
    "plastic": "Plastic Technology",
    # Robotics
    "robotics and automation": "Robotics and Automation",
    "robotics": "Robotics and Automation",
    "robot": "Robotics and Automation",
    # Rubber Technology
    "rubber technology": "Rubber Technology",
    "rubber": "Rubber Technology",
    # Science & Humanities
    "science and humanities": "Science and Humanities",
    "science humanities": "Science and Humanities",
    "humanities": "Science and Humanities",
    # Textile Technology
    "textile technology": "Textile Technology",
    "textile": "Textile Technology",
}

# Topic keyword groups
_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "eligibility": ["eligib", "criteria", "qualify", "pcm", "minimum marks", "10+2", "hsc"],
    "fees": ["fees", "fee", "tuition", "charges", "cost", "amount", "pay", "payment", "how much"],
    "scholarship": ["scholarship", "financial aid", "waiver", "free ship", "sc st scholarship"],
    "hostel": ["hostel", "accommodation", "stay", "residence", "dorm", "boarding"],
    "admission": ["admission", "apply", "acpc", "ddcet", "d2d", "lateral", "process", "how to get"],
    "cutoff": ["cutoff", "cut off", "closing rank", "last rank", "merit rank"],
    "placement": ["placement", "placed", "campus recruit", "job", "hiring", "company visit"],
    "package": ["package", "ctc", "salary", "lpa", "highest salary", "average salary"],
    "internship": ["internship", "intern", "industrial training", "summer project"],
    "transport": ["transport", "bus", "commute", "travel", "route", "shuttle"],
    "library": ["library", "books", "reading room", "journals", "e-library"],
    "canteen": ["canteen", "cafeteria", "food", "lunch", "dining", "mess"],
    "sports": ["sports", "ground", "cricket", "football", "gym", "court"],
    "syllabus": ["syllabus", "curriculum", "subjects", "courses", "program structure"],
    "results": ["results", "marks", "grades", "gpa", "cpi", "sgpa"],
    "contact": ["contact", "address", "phone", "email", "office", "location", "reach"],
}


def extract_department(text: str) -> Optional[str]:
    """Return the canonical department name found in *text*, or None."""
    t = text.lower()
    # Sort by length descending so longer matches win
    for alias in sorted(_DEPT_ALIASES, key=len, reverse=True):
        if re.search(r"\b" + re.escape(alias) + r"\b", t):
            return _DEPT_ALIASES[alias]
    return None


def extract_topic(text: str) -> Optional[str]:
    """Return the first matching topic keyword group found in *text*, or None."""
    t = text.lower()
    for topic, keywords in _TOPIC_KEYWORDS.items():
        for kw in keywords:
            if kw in t:
                return topic
    return None
