"""Intent classifier using TF-IDF + scikit-learn Pipeline.

Supports three algorithms selectable via config:
  - naive_bayes    → MultinomialNB
  - decision_tree  → DecisionTreeClassifier
  - knn            → KNeighborsClassifier

Training data is seeded from:
  (a) knowledge_base.json question_examples
  (b) backend/data/external/intents.json (Kaggle dataset, skipped if absent)
  (c) Template-based augmentation for each category (>= 40 examples each)
"""
import json
import os
import random
import re
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
from sklearn.tree import DecisionTreeClassifier

from .normalizer import normalize

from ..config import DATA_DIR, MODELS_DIR

CATEGORIES = [
    "Admissions",
    "Departments",
    "Fees",
    "Hostel",
    "Placements",
    "Academics",
    "Campus Facilities",
    "Contact",
]

# Small-talk intents handled before the classifier
SMALLTALK_PATTERNS = {
    "greeting": [r"\b(hi|hello|hey|namaste|hii|helo|greetings|good morning|good afternoon|good evening)\b"],
    "thanks": [r"\b(thank|thanks|thx|ty|thank you|thankyou)\b"],
    "goodbye": [r"\b(bye|goodbye|good bye|see you|take care|ok bye)\b"],
}

_DEPT_NAMES = [
    "cse", "computer engineering", "it", "information technology",
    "aiml", "ai ml", "mechanical", "mech", "civil", "electrical",
    "ec", "electronics", "instrumentation", "ic", "chemical",
    "automobile", "auto", "biomedical", "plastic", "robotics", "rubber",
    "textile",
]

_TEMPLATE_SEEDS: dict[str, list[str]] = {
    "Admissions": [
        "what is the admission process",
        "how do i apply to ldce",
        "acpc admission process",
        "ddcet eligibility criteria",
        "d2d lateral entry process",
        "how to get admission",
        "documents required for admission",
        "admission eligibility",
        "application procedure for ldce",
        "when does admission start",
        "seat allotment process",
        "cutoff rank for ldce",
        "closing rank for {dept}",
        "how to apply for {dept}",
        "is {dept} available at ldce",
        "seats available in {dept}",
        "admission procedure for {dept}",
        "eligibility for {dept}",
        "nri admission process",
        "oci admission ldce",
        "pg admission process",
        "mca admission ldce",
    ],
    "Departments": [
        "tell me about {dept} department",
        "about {dept} at ldce",
        "{dept} department overview",
        "what does {dept} cover",
        "is {dept} a good branch",
        "subjects in {dept}",
        "labs in {dept} department",
        "career scope after {dept}",
        "{dept} engineering at ldce",
        "details about {dept}",
        "overview of {dept}",
        "information about {dept} department",
        "plastic technology at ldce",
        "rubber technology department",
        "robotics automation at ldce",
        "textile technology ldce",
        "science humanities department",
        "biomedical engineering department",
        "automobile engineering ldce",
        "environmental engineering at ldce",
    ],
    "Fees": [
        "what is the fee for {dept}",
        "fee for {dept}",
        "{dept} fees",
        "{dept} fee??",
        "fees for {dept}",
        "how much is {dept} fee",
        "annual fee at ldce",
        "tuition fee structure",
        "fee details ldce",
        "total cost for ldce",
        "how much does ldce cost",
        "semester fees at ldce",
        "fee for mba at ldce",
        "fee for mca",
        "fees for working professional",
        "scholarship deduction in fees",
        "fee structure government college",
    ],
    "Hostel": [
        "hostel available at ldce",
        "is there hostel at ldce",
        "hostel fee at ldce",
        "hostel facilities ldce",
        "boys hostel ldce",
        "girls hostel ldce",
        "hostel for first year",
        "can i get hostel",
        "hostel accommodation",
        "hostel application process",
        "hostel rules at ldce",
        "mess food at hostel",
        "hostel charges",
        "hostel rent per semester",
        "how to apply for hostel",
        "hostel seat availability",
        "hostel for mca students",
    ],
    "Placements": [
        "placement record at ldce",
        "companies visiting ldce",
        "campus recruitment ldce",
        "placement package for {dept}",
        "highest package at ldce",
        "average salary ldce",
        "internship through ldce",
        "placement cell ldce",
        "how are placements at ldce",
        "job after {dept} from ldce",
        "top recruiters at ldce",
        "placement statistics ldce",
        "any internship through college",
        "summer internship ldce",
        "off campus hiring ldce",
        "percentage placed ldce",
        "does ldce provide internship",
    ],
    "Academics": [
        "syllabus for {dept}",
        "curriculum at ldce",
        "how many semesters in be",
        "academic calendar ldce",
        "exam schedule ldce",
        "when are mid sem exams",
        "semester timetable",
        "gtu affiliation ldce",
        "how is the academic structure",
        "electives in {dept}",
        "project in final year",
        "lab work at ldce",
        "industrial training semester",
        "exam pattern at ldce",
        "result portal ldce",
    ],
    "Campus Facilities": [
        "library facilities at ldce",
        "does ldce have library",
        "canteen at ldce",
        "sports ground ldce",
        "wifi on campus",
        "campus bus timings",
        "transport facility ldce",
        "gym at ldce",
        "medical facility ldce",
        "clubs at ldce",
        "ncc nss at ldce",
        "student chapter ldce",
        "campus infrastructure",
        "lab facilities ldce",
        "super computing facility",
        "bosch lab ldce",
    ],
    "Contact": [
        "contact ldce",
        "address of ldce",
        "phone number of ldce",
        "email of ldce",
        "how to reach ldce",
        "where is ldce located",
        "ldce admission office contact",
        "navrangpura ahmedabad",
        "how to contact principal",
        "ldce website link",
        "official site ldce",
        "contact details for ldce",
        "ldce map location",
    ],
}


def _build_training_data() -> tuple[list[str], list[str]]:
    """Build (texts, labels) training corpus from KB + templates + external."""
    texts: list[str] = []
    labels: list[str] = []

    # (a) Knowledge base question_examples
    kb_path = DATA_DIR / "knowledge_base.json"
    if kb_path.exists():
        with open(kb_path, encoding="utf-8") as f:
            kb = json.load(f)
        for entry in kb:
            cat = entry["category"]
            for q in entry.get("question_examples", []):
                texts.append(normalize(q))
                labels.append(cat)

    # (b) External Kaggle intents.json (optional)
    ext_path = DATA_DIR / "external" / "intents.json"
    if ext_path.exists():
        _load_external_intents(ext_path, texts, labels)

    # (c) Template augmentation – ensure >= 40 examples per category
    cat_counts: dict[str, int] = {c: labels.count(c) for c in CATEGORIES}
    for cat, seeds in _TEMPLATE_SEEDS.items():
        needed = max(0, 40 - cat_counts.get(cat, 0))
        generated: list[str] = []
        while len(generated) < needed + 10:
            seed = random.choice(seeds)
            # Fill {dept} placeholder
            if "{dept}" in seed:
                dept = random.choice(_DEPT_NAMES)
                seed = seed.replace("{dept}", dept)
            # Random typo / casing variation
            seed = _augment(seed)
            generated.append(normalize(seed))
        for g in generated:
            texts.append(g)
            labels.append(cat)

    return texts, labels


def _load_external_intents(path: Path, texts: list, labels: list) -> None:
    """Load Kaggle university chatbot intents and map to our categories."""
    _tag_map = {
        "Admission": "Admissions",
        "Fee": "Fees",
        "Hostel": "Hostel",
        "Placement": "Placements",
        "Department": "Departments",
        "Academic": "Academics",
        "Facility": "Campus Facilities",
        "Contact": "Contact",
    }
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        intents = data if isinstance(data, list) else data.get("intents", [])
        for intent in intents:
            tag = intent.get("tag", "")
            cat = next((v for k, v in _tag_map.items() if k.lower() in tag.lower()), None)
            if cat is None:
                continue
            for pattern in intent.get("patterns", []):
                texts.append(normalize(pattern))
                labels.append(cat)
    except Exception:
        pass  # Gracefully skip if file is absent or malformed


def _augment(text: str) -> str:
    """Apply mild random augmentation: random casing, duplicate chars, swap digits."""
    if random.random() < 0.3:
        text = text.upper()
    elif random.random() < 0.3:
        text = text.title()
    # Occasionally repeat a character
    if random.random() < 0.2 and len(text) > 3:
        pos = random.randint(0, len(text) - 1)
        text = text[:pos] + text[pos] + text[pos:]
    # Append question mark variants
    suffix = random.choice(["", "?", "??", "plz", "please tell me", "can u help"])
    return f"{text} {suffix}".strip()


def _build_pipeline(algorithm: str) -> Pipeline:
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=1,
        sublinear_tf=True,
    )
    if algorithm == "naive_bayes":
        clf = MultinomialNB(alpha=0.5)
    elif algorithm == "knn":
        clf = KNeighborsClassifier(n_neighbors=5, metric="cosine")
    else:  # default: decision_tree
        clf = DecisionTreeClassifier(max_depth=None, random_state=42)

    return Pipeline([("tfidf", vectorizer), ("clf", clf)])


def train_and_save(algorithm: str = "decision_tree") -> Pipeline:
    """Train classifier on seeded data and persist to disk. Returns the pipeline."""
    texts, labels = _build_training_data()
    pipe = _build_pipeline(algorithm)
    pipe.fit(texts, labels)
    model_path = MODELS_DIR / f"classifier_{algorithm}.joblib"
    joblib.dump({"pipeline": pipe, "algorithm": algorithm, "categories": CATEGORIES}, model_path)
    return pipe


def load_model(algorithm: str = "decision_tree") -> Optional[Pipeline]:
    """Load a previously trained pipeline from disk, or None if not found."""
    model_path = MODELS_DIR / f"classifier_{algorithm}.joblib"
    if not model_path.exists():
        return None
    data = joblib.load(model_path)
    return data["pipeline"]


def get_training_data() -> tuple[list[str], list[str]]:
    """Public access to the training corpus (used by train_classifier.py script)."""
    return _build_training_data()


def predict(text: str, pipeline: Pipeline) -> tuple[str, float]:
    """Return (predicted_category, confidence_score) for *text* with safety calibration."""
    normalized = normalize(text)
    tfidf_vec = pipeline.named_steps["tfidf"].transform([normalized])
    if tfidf_vec.nnz == 0:
        # Out-of-vocabulary query with zero TF-IDF terms
        classes = pipeline.classes_
        return str(classes[0]), 0.1

    proba = pipeline.predict_proba([normalized])[0]
    classes = pipeline.classes_
    idx = int(np.argmax(proba))
    conf = float(proba[idx])

    # Calibrate confidence if non-probabilistic tree/kNN model or weak vocabulary coverage
    words = [w for w in normalized.split() if len(w) > 1]
    if words:
        vocab = pipeline.named_steps["tfidf"].vocabulary_
        matched_words = sum(1 for w in words if w in vocab)
        match_ratio = matched_words / len(words)
        if match_ratio < 0.35:
            # Low vocabulary overlap query — scale down confidence so fallback catches it
            conf = min(conf, round(match_ratio * 0.9, 3))

    return str(classes[idx]), round(conf, 3)


def detect_smalltalk(text: str) -> Optional[str]:
    """Return smalltalk intent name if matched, else None. Not logged."""
    t = text.lower().strip()
    for intent, patterns in SMALLTALK_PATTERNS.items():
        for p in patterns:
            if re.search(p, t):
                return intent
    return None
