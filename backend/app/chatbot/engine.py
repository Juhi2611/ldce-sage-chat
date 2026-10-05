"""Main chatbot engine: orchestrates normalisation → smalltalk → classify → extract → retrieve.

This is the single entry point called by the API layer.
"""
from typing import Optional
from sqlalchemy.orm import Session as DBSession

from ..config import settings
from .normalizer import normalize
from .entity_extraction import extract_department, extract_topic
from .classifier import load_model, train_and_save, predict, detect_smalltalk, CATEGORIES
from .answer_retrieval import find_best_entry, get_categories_for_api

# Small-talk replies (not logged to analytics)
_SMALLTALK_REPLIES = {
    "greeting": (
        "Namaste! 👋 I'm the LDCE Smart Enquiry Assistant. "
        "I can help you with admissions, fees, hostel, placements, departments and more. "
        "What would you like to know?"
    ),
    "thanks": "You're welcome! Feel free to ask if you have any other questions about LDCE. 😊",
    "goodbye": "Goodbye! Best of luck with your LDCE journey. Feel free to come back anytime. 🎓",
}

# Cached pipeline per algorithm
_pipeline_cache: dict[str, object] = {}


def _get_pipeline(algorithm: str):
    if algorithm not in _pipeline_cache:
        pipe = load_model(algorithm)
        if pipe is None:
            pipe = train_and_save(algorithm)
        _pipeline_cache[algorithm] = pipe
    return _pipeline_cache[algorithm]


def invalidate_pipeline_cache() -> None:
    """Call after retraining to force re-load on next request."""
    _pipeline_cache.clear()


def chat(
    query: str,
    session_id: str,
    db: DBSession,
    algorithm: Optional[str] = None,
) -> dict:
    """Process one user message and return a structured response dict."""
    algo = algorithm or settings.classifier_algorithm

    # 1. Small-talk detection (not logged)
    smalltalk_intent = detect_smalltalk(query)
    if smalltalk_intent:
        return {
            "answer_markdown": _SMALLTALK_REPLIES.get(smalltalk_intent, _SMALLTALK_REPLIES["greeting"]),
            "intent": smalltalk_intent,
            "department": None,
            "topic": None,
            "confidence": 1.0,
            "resolved": True,
            "suggestions": _build_category_suggestions(None, None, None, db),
            "enquiry_id": None,
            "source_url": None,
            "is_smalltalk": True,
        }

    # 2. Normalise
    query_norm = normalize(query)

    # 3. Classify
    pipe = _get_pipeline(algo)
    category, confidence = predict(query, pipe)

    # 4. Entity extraction
    department = extract_department(query_norm)
    topic = extract_topic(query_norm)

    # 5. Low confidence fallback — skip if entity extraction found dept/topic
    resolved = confidence >= settings.confidence_threshold
    entity_detected = department is not None or topic is not None
    if not resolved and not entity_detected:
        answer = (
            "I'm not quite sure how to help with that. Here are some topics I can assist with:\n\n"
            + "\n".join(f"- **{c}**" for c in _get_fallback_categories())
            + "\n\nPlease try rephrasing your question, or choose one of the topics above."
        )
        enquiry_id = _log_enquiry(
            db, session_id, query, query_norm, category or "Unknown",
            department, topic, confidence, resolved=False
        )
        return {
            "answer_markdown": answer,
            "intent": f"{category} · Low confidence",
            "department": department,
            "topic": topic,
            "confidence": confidence,
            "resolved": False,
            "suggestions": _build_category_suggestions(None, None, None, db),
            "enquiry_id": enquiry_id,
            "source_url": None,
            "is_smalltalk": False,
        }
    if not resolved and entity_detected:
        resolved = True

    # 6. Retrieve answer
    entry = find_best_entry(query_norm, category, department, topic)
    if entry:
        answer = entry["answer"]
        source_url = entry.get("source_url")
        intent_label = f"{category} · {department or 'General'}"
    else:
        answer = (
            f"For information about **{category}** at LDCE, please visit the official website.\n\n"
            "📎 [ldce.ac.in](https://ldce.ac.in)"
        )
        source_url = "https://ldce.ac.in"
        intent_label = f"{category} · General"

    # 7. Log to DB (with predicted_topic stored)
    enquiry_id = _log_enquiry(
        db, session_id, query, query_norm, category,
        department, topic, confidence, resolved=True
    )

    # 8. Suggestions (mined rules preferred or natural context defaults, excluding current topic)
    suggestions = _build_category_suggestions(category, department, topic, db)

    return {
        "answer_markdown": answer,
        "intent": intent_label,
        "department": department,
        "topic": topic,
        "confidence": confidence,
        "resolved": True,
        "suggestions": suggestions,
        "enquiry_id": enquiry_id,
        "source_url": source_url,
        "is_smalltalk": False,
    }


def _log_enquiry(
    db: DBSession,
    session_id: str,
    raw: str,
    normalized: str,
    category: str,
    department: Optional[str],
    topic: Optional[str],
    confidence: float,
    resolved: bool,
) -> int:
    from ..models import Enquiry, Session as SessionModel
    import re

    # Ensure session exists
    sess = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not sess:
        sess = SessionModel(id=session_id)
        db.add(sess)
        db.flush()

    # Privacy: mask phone numbers and email addresses in raw question
    masked = re.sub(r"\b\d{10,}\b", "[PHONE]", raw)
    masked = re.sub(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", "[EMAIL]", masked)

    enq = Enquiry(
        session_id=session_id,
        raw_question=masked,
        normalized_question=normalized,
        predicted_category=category,
        predicted_department=department,
        predicted_topic=topic.title() if topic else None,
        confidence=confidence,
        resolved=resolved,
        is_synthetic=False,
    )
    db.add(enq)
    db.commit()
    db.refresh(enq)
    return enq.id


def _get_fallback_categories() -> list[str]:
    return CATEGORIES[:5]


# Natural topic mappings to full sentence questions and clean readable labels
_ITEM_TO_QUESTION_LABEL: dict[str, tuple[str, str]] = {
    "Transport": ("Transport Facilities", "What transport facilities and bus routes are available near LDCE?"),
    "Hostel": ("Hostel Accommodation", "What hostel facilities and rooms are available at LDCE?"),
    "Hostel Fee": ("Hostel Fees", "What are the hostel and mess charges per semester?"),
    "Scholarship": ("Scholarships & Aid", "What scholarships and fee waivers are available at LDCE?"),
    "Tuition": ("Tuition Fees", "What is the annual tuition fee structure at LDCE?"),
    "Placement": ("Placement Records", "What are the latest placement records and recruiters at LDCE?"),
    "Package": ("Salary Packages", "What are the highest and average salary packages offered at LDCE?"),
    "Internship": ("Internship Opportunities", "Does LDCE facilitate internships for students?"),
    "Eligibility": ("Eligibility Criteria", "What is the eligibility criteria for admission to LDCE?"),
    "Admission": ("Admission Process", "What is the ACPC admission process for LDCE?"),
    "Cutoff": ("Admission Cutoffs", "What was the previous year's cutoff rank for admission?"),
    "Library": ("Library Facilities", "What resources and timings are available at the LDCE library?"),
    "Canteen": ("Canteen & Dining", "What food and canteen options are available on campus?"),
    "Sports": ("Sports Facilities", "What sports and gym facilities are available on campus?"),
    "Curriculum": ("Course Curriculum", "What subjects and courses are taught in the department?"),
    "Overview": ("Department Overview", "Can you give me an overview of the engineering department?"),
    "Syllabus": ("Syllabus & Exams", "Where can I find the GTU academic syllabus?"),
    "CSE": ("Computer Engineering", "What are the placement and curriculum details for Computer Engineering?"),
    "IT": ("Information Technology", "What are the placement and lab details for Information Technology?"),
    "AIML": ("AI & Machine Learning", "What are the details about the AI and Machine Learning program?"),
}


def _build_category_suggestions(
    current_category: Optional[str],
    current_department: Optional[str] = None,
    current_topic: Optional[str] = None,
    db: Optional[DBSession] = None,
) -> list[dict]:
    """Return up to 3 de-duplicated suggestion dicts with full questions and topic labels.
    Never suggests the topic or category the user just asked about.
    """
    suggestions = []
    seen_labels = set()

    # Normalize current topic / category to exclude self-suggestions
    excluded_items = set()
    if current_category:
        excluded_items.add(current_category.lower())
    if current_topic:
        excluded_items.add(current_topic.lower())
    if current_department:
        excluded_items.add(current_department.lower())

    # 1. Try mined rules first
    if db:
        from ..models import MinedRule
        # Check rule antecedents matching current_topic, current_category, or department
        search_terms = []
        if current_topic:
            search_terms.append(current_topic)
        if current_category:
            search_terms.append(current_category)

        for term in search_terms:
            rules = (
                db.query(MinedRule)
                .filter(
                    MinedRule.status == "Useful",
                    MinedRule.antecedent.ilike(f"%{term}%"),
                )
                .order_by((MinedRule.lift * MinedRule.confidence).desc())
                .limit(4)
                .all()
            )
            for rule in rules:
                consequent = rule.consequent.strip()
                if consequent.lower() in excluded_items:
                    continue

                if consequent in _ITEM_TO_QUESTION_LABEL:
                    label, q = _ITEM_TO_QUESTION_LABEL[consequent]
                else:
                    label = consequent
                    q = f"What are the details regarding {consequent} at LDCE?"

                if label not in seen_labels:
                    seen_labels.add(label)
                    suggestions.append({"label": label, "question": q, "source": "mined"})
                    if len(suggestions) >= 3:
                        break
            if len(suggestions) >= 3:
                break

    # 2. Contextual defaults based on current category/topic
    category_defaults: dict[str, list[tuple[str, str]]] = {
        "Hostel": [
            ("Transport Facilities", "What transport facilities and bus routes are available near LDCE?"),
            ("Canteen & Dining", "What food options and canteen facilities are available on campus?"),
            ("Campus Facilities", "What other campus facilities and amenities does LDCE provide?"),
        ],
        "Fees": [
            ("Scholarships & Aid", "What scholarships and financial aid can I apply for at LDCE?"),
            ("Hostel Accommodation", "What are the hostel and accommodation fees at LDCE?"),
            ("Admission Process", "How does the fee payment integrate with ACPC admission?"),
        ],
        "Placements": [
            ("Salary Packages", "What are the highest and average placement packages offered?"),
            ("Internship Opportunities", "Does LDCE provide internship and industrial training assistance?"),
            ("Recruiting Companies", "Which top companies visit LDCE for campus recruitment?"),
        ],
        "Admissions": [
            ("Eligibility Criteria", "What is the eligibility criteria and minimum marks required?"),
            ("Documents Required", "What documents are required during ACPC counselling and reporting?"),
            ("Tuition Fees", "What is the fee structure for admitted students?"),
        ],
        "Departments": [
            ("Placement Records", "What is the placement record for this department?"),
            ("Course Curriculum", "What subjects and lab facilities are available in this branch?"),
            ("Admission Cutoffs", "What are the cutoff ranks for this department?"),
        ],
        "Campus Facilities": [
            ("Hostel Accommodation", "Is hostel accommodation available on the LDCE campus?"),
            ("Sports Facilities", "What sports ground and indoor gym facilities are available?"),
            ("Library Resources", "What are the library timings and book borrowing facilities?"),
        ],
    }

    ctx_list = category_defaults.get(current_category or "", [])
    for label, q in ctx_list:
        if len(suggestions) >= 3:
            break
        # Skip if matches current query topic/category
        if any(exc in label.lower() for exc in excluded_items):
            continue
        if label not in seen_labels:
            seen_labels.add(label)
            suggestions.append({"label": label, "question": q, "source": "default"})

    # 3. Universal fallbacks
    universal_fallbacks = [
        ("Admission Process", "What is the complete ACPC admission process for LDCE?"),
        ("Placement Records", "What are the campus placement statistics at LDCE?"),
        ("Campus Facilities", "What facilities and hostels are available on campus?"),
        ("Contact & Location", "How can I contact the LDCE administrative office?"),
    ]
    for label, q in universal_fallbacks:
        if len(suggestions) >= 3:
            break
        if label not in seen_labels:
            seen_labels.add(label)
            suggestions.append({"label": label, "question": q, "source": "default"})

    return suggestions[:3]
