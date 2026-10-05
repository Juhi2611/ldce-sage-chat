"""KDD Step 3 — Data Transformation.

Derives new features and builds two matrices needed for mining:
  1. time_period, day_of_week, is_weekend, month (temporal features)
  2. Session × (topic + department) binary basket matrix (for Apriori)
  3. TF-IDF document matrix of normalized_question (for KMeans clustering)
"""
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

# Department canonical to short tag mapping for clean association items
DEPT_TAGS = {
    "Computer Engineering": "CSE",
    "Information Technology": "IT",
    "Artificial Intelligence and Machine Learning": "AIML",
    "Mechanical Engineering": "Mech",
    "Civil Engineering": "Civil",
    "Electrical Engineering": "Electrical",
    "Electronics and Communication Engineering": "EC",
    "Chemical Engineering": "Chemical",
    "Automobile Engineering": "Automobile",
    "Biomedical Engineering": "Biomedical",
    "Environmental Engineering": "Environmental",
    "Plastic Technology": "Plastic",
    "Robotics and Automation": "Robotics",
    "Rubber Technology": "Rubber",
    "Textile Technology": "Textile",
}

GENERIC_STOPWORDS = [
    "what", "tell", "me", "is", "for", "the", "at", "in", "of", "and", "to", "a", "an",
    "ldce", "how", "much", "can", "please", "plz", "details", "about", "available", "there",
    "any", "i", "my", "we", "you", "your", "do", "does", "get", "give", "know", "want"
]


def _time_period(hour: int) -> str:
    if 5 <= hour < 12:
        return "Morning"
    if 12 <= hour < 17:
        return "Afternoon"
    if 17 <= hour < 21:
        return "Evening"
    return "Night"


def add_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add time-based columns derived from created_at."""
    df = df.copy()
    if "created_at" not in df.columns or df["created_at"].isna().all():
        df["time_period"] = "Unknown"
        df["day_of_week"] = "Unknown"
        df["is_weekend"] = False
        df["month"] = 0
        return df

    dt = pd.to_datetime(df["created_at"], utc=True)
    df["time_period"] = dt.dt.hour.apply(_time_period)
    df["day_of_week"] = dt.dt.day_name()
    df["is_weekend"] = dt.dt.dayofweek >= 5
    df["month"] = dt.dt.month
    return df


def build_basket_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Build a session × item binary basket matrix for Apriori.

    Items are topic-level items (e.g. Hostel, Transport, Scholarship, Placement,
    Eligibility, Admission, Fees) and department items (e.g. CSE, IT, Mech).
    Each row is one session; each column is an item.
    """
    if df.empty or "session_id" not in df.columns:
        return pd.DataFrame()

    session_items: list[dict] = []

    # Group by session_id
    for session_id, group in df.groupby("session_id"):
        items_set = set()
        for _, row in group.iterrows():
            # Add topic item if present, else category if valid
            topic = row.get("predicted_topic")
            cat = row.get("predicted_category")
            if topic and str(topic).strip() and str(topic).lower() not in ["none", "nan", "general"]:
                items_set.add(str(topic).strip())
            elif cat and str(cat).strip() and str(cat) not in ["Unknown", "nan"]:
                items_set.add(str(cat).strip())

            # Add department item if present
            dept = row.get("predicted_department")
            if dept and dept in DEPT_TAGS:
                items_set.add(DEPT_TAGS[dept])

        for item in items_set:
            session_items.append({"session_id": session_id, "item": item})

    if not session_items:
        return pd.DataFrame()

    items_df = pd.DataFrame(session_items)
    basket = pd.crosstab(items_df["session_id"], items_df["item"]) > 0

    # Keep only sessions that have ≥ 2 distinct items (needed for rules)
    basket = basket[basket.sum(axis=1) >= 2]
    return basket


def build_tfidf_matrix(df: pd.DataFrame) -> tuple[np.ndarray, TfidfVectorizer]:
    """Build TF-IDF matrix of normalized questions for clustering with English + custom stopwords.

    Returns (matrix, fitted_vectorizer).
    """
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
    all_stop_words = list(ENGLISH_STOP_WORDS.union(set(GENERIC_STOPWORDS)))

    vectorizer = TfidfVectorizer(
        max_features=500,
        ngram_range=(1, 2),
        sublinear_tf=True,
        stop_words=all_stop_words,
    )
    matrix = vectorizer.fit_transform(df["normalized_question"].fillna("")).toarray()
    return matrix, vectorizer


def transform(df: pd.DataFrame) -> dict:
    """Run all transformation steps and return a dict of outputs."""
    df = add_temporal_features(df)
    basket = build_basket_matrix(df)
    tfidf_matrix, vectorizer = build_tfidf_matrix(df)
    return {
        "df": df,
        "basket": basket,
        "tfidf_matrix": tfidf_matrix,
        "vectorizer": vectorizer,
    }
