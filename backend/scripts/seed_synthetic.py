"""Synthetic enquiry data generator.

Creates realistic enquiry rows across sessions with realistic noise and co-occurrences:
  - Hostel -> Transport
  - Fees -> Scholarship
  - CSE -> Placement
  - Admission -> Eligibility
  - 8-12% unresolved / low-confidence enquiries
  - Session lengths: 1 to 5 enquiries
  - Non-null predicted_topic on all valid enquiries
"""
import os
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Prevent joblib physical-cores warning on Windows
os.environ.setdefault("LOKY_MAX_CPU_COUNT", "4")

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Allow direct execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, init_db
from app.models import Enquiry, Session as SessionModel

# ─── Configuration ──────────────────────────────────────────────────────────
N_SESSIONS = 1200
MIN_ENQUIRIES_PER_SESSION = 1
MAX_ENQUIRIES_PER_SESSION = 5
START_DATE = datetime(2025, 1, 1)
END_DATE = datetime(2025, 9, 30)

CATEGORIES = [
    "Admissions", "Departments", "Fees", "Hostel",
    "Placements", "Academics", "Campus Facilities", "Contact",
]
DEPTS = [
    "Computer Engineering", "Information Technology",
    "Artificial Intelligence and Machine Learning",
    "Mechanical Engineering", "Civil Engineering",
    "Electrical Engineering", "Electronics and Communication Engineering",
    "Chemical Engineering", "Automobile Engineering",
    None,  # General
]

TOPIC_TEMPLATES: dict[str, list[tuple[str, str]]] = {
    "Admissions": [
        ("what is the admission process", "Admission"),
        ("how do i apply to ldce", "Admission"),
        ("acpc process for ldce", "Admission"),
        ("d2d lateral entry process", "Admission"),
        ("eligibility criteria for btech", "Eligibility"),
        ("what is the eligibility for admission", "Eligibility"),
        ("minimum marks required for admission", "Eligibility"),
        ("documents required for admission", "Documents"),
        ("cutoff rank for {dept}", "Cutoff"),
        ("seat allotment rounds", "Admission"),
        ("when is admission starting", "Dates"),
        ("acpc counselling dates", "Dates"),
        ("ddcet score required for d2d", "Eligibility"),
    ],
    "Fees": [
        ("fee for {dept}", "Tuition"),
        ("fees for {dept}", "Tuition"),
        ("what is {dept} fee", "Tuition"),
        ("{dept} fees per year", "Tuition"),
        ("annual tuition fee at ldce", "Tuition"),
        ("fee structure ldce", "Tuition"),
        ("total cost for btech", "Tuition"),
        ("how much is semester fee", "Tuition"),
        ("scholarships available for fee waiver", "Scholarship"),
        ("mysy scholarship process", "Scholarship"),
        ("exam fee payment process", "Exam Fee"),
    ],
    "Hostel": [
        ("hostel available at ldce", "Hostel"),
        ("hostel fee per year", "Hostel Fee"),
        ("hostel for first year", "Hostel"),
        ("boys hostel facility", "Hostel"),
        ("girls hostel accommodation", "Hostel"),
        ("hostel application process", "Hostel"),
        ("is there hostel on campus", "Hostel"),
        ("hostel mess charges", "Hostel Fee"),
    ],
    "Placements": [
        ("placement record at ldce", "Placement"),
        ("placement package for {dept}", "Package"),
        ("average salary package after {dept}", "Package"),
        ("highest package at ldce", "Package"),
        ("companies visiting ldce for placement", "Companies"),
        ("campus recruitment drives", "Companies"),
        ("internship opportunities through college", "Internship"),
        ("does ldce provide internship", "Internship"),
        ("placement statistics for {dept}", "Placement"),
    ],
    "Departments": [
        ("tell me about {dept} department", "Overview"),
        ("about {dept} branch at ldce", "Overview"),
        ("{dept} department overview", "Overview"),
        ("career scope after {dept}", "Overview"),
        ("subjects and labs in {dept}", "Curriculum"),
        ("is {dept} good branch at ldce", "Overview"),
    ],
    "Academics": [
        ("syllabus for {dept}", "Syllabus"),
        ("academic calendar ldce", "Calendar"),
        ("when are mid sem exams", "Exams"),
        ("how many semesters in be", "Curriculum"),
        ("gtu exam schedule", "Exams"),
        ("timetable for {dept}", "Timetable"),
        ("semester exam dates", "Exams"),
    ],
    "Campus Facilities": [
        ("transport facility near ldce", "Transport"),
        ("campus bus timings and routes", "Transport"),
        ("how to reach ldce by bus", "Transport"),
        ("library facilities and books at ldce", "Library"),
        ("canteen and food options at ldce", "Canteen"),
        ("sports ground and gym at ldce", "Sports"),
        ("wifi facility on campus", "Wifi"),
    ],
    "Contact": [
        ("address of ldce campus", "Address"),
        ("contact phone number ldce", "Phone"),
        ("admission office phone number", "Phone"),
        ("how to reach ldce location", "Address"),
        ("official website ldce", "Website"),
        ("email address of ldce admin", "Email"),
    ],
}

UNRESOLVED_TEMPLATES = [
    "what is the meaning of life",
    "can you order pizza for me",
    "who is the prime minister of india",
    "how to cook biryani",
    "play some music please",
    "tell me a funny joke",
    "what is the weather today",
    "crypto trading tips",
    "xyz college fee structure",
    "recommend a good movie",
    "asdfghjkl random test",
    "where can i buy shoes",
]

DEPT_SHORT: dict[str, str] = {
    "Computer Engineering": "CSE",
    "Information Technology": "IT",
    "Artificial Intelligence and Machine Learning": "AIML",
    "Mechanical Engineering": "Mech",
    "Civil Engineering": "Civil",
    "Electrical Engineering": "Electrical",
    "Electronics and Communication Engineering": "EC",
    "Chemical Engineering": "Chemical",
    "Automobile Engineering": "Automobile",
}


def _random_timestamp(spike_month: int | None = None) -> datetime:
    """Generate a timestamp with evening bias and optional month spike."""
    weights = [1, 1, 1, 1, 3, 3, 3, 1.5, 1, 1, 1, 1]
    month = spike_month if spike_month else random.choices(range(1, 13), weights=weights)[0]
    day = random.randint(1, 28)
    year = 2025

    dt = datetime(year, month, day)
    weekday = dt.weekday()

    hour_weights = [0.5, 0.3, 0.2, 0.2, 0.2, 0.5,
                    1.0, 1.5, 2.0, 2.0, 2.0, 2.5,
                    2.5, 2.0, 2.0, 2.5, 3.0, 3.5,
                    4.0, 4.0, 3.5, 2.5, 1.5, 0.8]
    if weekday >= 5:
        hour_weights = [w * 0.7 for w in hour_weights]

    hour = random.choices(range(24), weights=hour_weights)[0]
    minute = random.randint(0, 59)
    return datetime(year, month, day, hour, minute)


def _add_noise(text: str) -> str:
    """Randomly add typos, duplicate chars, trailing punctuation."""
    if random.random() < 0.15:
        pos = random.randint(0, len(text) - 1)
        text = text[:pos] + text[pos] + text[pos:]
    if random.random() < 0.25:
        text += random.choice(["?", "??", "!", "...", " plz", " pls", ""])
    return text


def generate(db) -> int:
    """Insert synthetic sessions and enquiries. Returns total rows inserted."""
    init_db()
    total = 0
    from app.chatbot.normalizer import normalize

    for s_idx in range(N_SESSIONS):
        session_id = f"synthetic-{s_idx:05d}"

        sess = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not sess:
            sess = SessionModel(id=session_id, user_type="Prospective Student")
            db.add(sess)

        # ~18% single-enquiry sessions, remaining 2-5 enquiries
        if random.random() < 0.18:
            n_enq = 1
        else:
            n_enq = random.randint(2, MAX_ENQUIRIES_PER_SESSION)

        dept_canonical = random.choice(DEPTS)
        dept_short = DEPT_SHORT.get(dept_canonical, "Engg") if dept_canonical else "General"

        # Determine if this session follows a planted pattern
        pattern_roll = random.random()
        session_items: list[tuple[str, str, str, str | None]] = []  # (category, topic, raw_q, dept)

        if n_enq >= 2 and pattern_roll < 0.22:
            # Planted: Hostel -> Transport
            session_items.append(("Hostel", "Hostel", "hostel facilities and accommodation at ldce", None))
            session_items.append(("Campus Facilities", "Transport", "campus bus timings and transport facility", None))
        elif n_enq >= 2 and pattern_roll < 0.44:
            # Planted: Fees -> Scholarship
            dept_used = dept_canonical or "Computer Engineering"
            session_items.append(("Fees", "Tuition", f"fee structure for {DEPT_SHORT.get(dept_used, 'cse')}", dept_used))
            session_items.append(("Fees", "Scholarship", "scholarships available for fee waiver at ldce", dept_used))
        elif n_enq >= 2 and pattern_roll < 0.66:
            # Planted: CSE -> Placement
            session_items.append(("Departments", "Overview", "tell me about cse department at ldce", "Computer Engineering"))
            session_items.append(("Placements", "Placement", "placement record and companies for cse", "Computer Engineering"))
        elif n_enq >= 2 and pattern_roll < 0.85:
            # Planted: Admission -> Eligibility
            session_items.append(("Admissions", "Admission", "what is the admission process for ldce", dept_canonical))
            session_items.append(("Admissions", "Eligibility", "eligibility criteria and minimum marks for btech", dept_canonical))
        else:
            first_cat = random.choice(CATEGORIES)
            items = TOPIC_TEMPLATES.get(first_cat, [("tell me about ldce", "General")])
            tpl, top = random.choice(items)
            q = tpl.replace("{dept}", dept_short)
            session_items.append((first_cat, top, q, dept_canonical))

        # Fill remaining enquiries in the session
        while len(session_items) < n_enq:
            cat = random.choice(CATEGORIES)
            items = TOPIC_TEMPLATES.get(cat, [("tell me about ldce", "General")])
            tpl, top = random.choice(items)
            q = tpl.replace("{dept}", dept_short)
            session_items.append((cat, top, q, dept_canonical))

        base_ts = _random_timestamp()

        for e_idx, (cat, top, raw_q, dept) in enumerate(session_items):
            ts = base_ts + timedelta(seconds=random.randint(30, 300) * e_idx)

            # ~10% chance of unresolved/out-of-scope enquiry (yielding 8-12% overall)
            is_unresolved = random.random() < 0.10
            if is_unresolved:
                question = random.choice(UNRESOLVED_TEMPLATES)
                norm_q = normalize(question)
                cat = "Unknown"
                dept = None
                top = None
                confidence = round(random.uniform(0.12, 0.38), 3)
                resolved = False
            else:
                question = _add_noise(raw_q)
                norm_q = normalize(question)
                confidence = round(random.uniform(0.60, 0.98), 3)
                resolved = True

            enq = Enquiry(
                session_id=session_id,
                raw_question=question,
                normalized_question=norm_q,
                predicted_category=cat,
                predicted_department=dept,
                predicted_topic=top,
                confidence=confidence,
                resolved=resolved,
                is_synthetic=True,
                created_at=ts,
            )
            db.add(enq)
            total += 1

        if s_idx % 100 == 0:
            db.commit()
            print(f"  Seeded {total} rows so far…")

    db.commit()
    return total


if __name__ == "__main__":
    db = SessionLocal()
    try:
        print("Generating synthetic enquiries…")
        n = generate(db)
        print(f"Done. Inserted {n} synthetic rows.")
    finally:
        db.close()
