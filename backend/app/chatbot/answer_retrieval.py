"""Answer retrieval: matches (category, department, topic) to the best KB entry.

Uses TF-IDF cosine similarity to rank when multiple entries match.
"""
import json
from pathlib import Path
from typing import Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .normalizer import normalize

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

_kb: list[dict] = []
_kb_tfidf: Optional[TfidfVectorizer] = None
_kb_matrix = None


def _load_kb() -> None:
    """Load knowledge base once into module-level cache."""
    global _kb, _kb_tfidf, _kb_matrix
    if _kb:
        return
    kb_path = DATA_DIR / "knowledge_base.json"
    with open(kb_path, encoding="utf-8") as f:
        _kb = json.load(f)
    # Build a TF-IDF index over all entries' question_examples + keywords
    docs = []
    for entry in _kb:
        combined = " ".join(entry.get("question_examples", []) + entry.get("keywords", []))
        docs.append(normalize(combined))
    _kb_tfidf = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True).fit(docs)
    _kb_matrix = _kb_tfidf.transform(docs)


def get_kb() -> list[dict]:
    _load_kb()
    return _kb


def find_best_entry(
    query: str,
    category: str,
    department: Optional[str],
    topic: Optional[str],
) -> Optional[dict]:
    """Return the most relevant KB entry for the given (category, dept, topic)."""
    _load_kb()
    query_norm = normalize(query)

    # Filter by category
    candidates = [e for e in _kb if e["category"] == category]
    if not candidates:
        return None

    # Narrow by department if provided
    if department:
        dept_candidates = [e for e in candidates if e.get("department") == department]
        if dept_candidates:
            candidates = dept_candidates

    # Narrow by topic (subcategory or keyword match)
    if topic:
        topic_candidates = [
            e for e in candidates
            if topic in " ".join(e.get("keywords", [])).lower()
            or topic.lower() in (e.get("subcategory") or "").lower()
        ]
        if topic_candidates:
            candidates = topic_candidates

    if len(candidates) == 1:
        return candidates[0]

    # Rank by cosine similarity
    candidate_indices = [_kb.index(c) for c in candidates]
    q_vec = _kb_tfidf.transform([query_norm])
    candidate_matrix = _kb_matrix[candidate_indices]
    scores = cosine_similarity(q_vec, candidate_matrix)[0]
    best_local = int(np.argmax(scores))
    return candidates[best_local]


def get_categories_for_api() -> list[dict]:
    """Return category quick-action tiles (from KB categories)."""
    seen = set()
    tiles = []
    for entry in get_kb():
        cat = entry["category"]
        if cat not in seen:
            seen.add(cat)
            example_q = entry["question_examples"][0] if entry.get("question_examples") else f"Tell me about {cat}"
            tiles.append({"label": cat, "question": example_q})
    return tiles


def get_departments_for_api() -> list[dict]:
    """Return department cards with description (from KB)."""
    seen = set()
    cards = []
    for entry in get_kb():
        if entry["category"] != "Departments":
            continue
        dept = entry.get("department")
        if dept and dept not in seen:
            seen.add(dept)
            cards.append({
                "name": dept,
                "description": entry.get("answer", "")[:120].split("\n")[0].lstrip("#").strip(),
                "source_url": entry.get("source_url", "https://ldce.ac.in"),
            })
    return cards
