"""KDD Step 4 — Data Mining.

Three mining tasks:
  (a) Classification — benchmark Naive Bayes, Decision Tree, KNN
  (b) Clustering     — K-Means with silhouette-based k selection (k in 3..5, 5 keyword chips)
  (c) Association    — Apriori on session × (topic + dept) basket matrix
"""
import json
import os
import warnings
from typing import Any

import numpy as np
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from sklearn.cluster import KMeans
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    confusion_matrix,
)
from sklearn.metrics import silhouette_score
from sklearn.model_selection import cross_val_score, StratifiedShuffleSplit
from sklearn.naive_bayes import MultinomialNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
from sklearn.tree import DecisionTreeClassifier
from sklearn.feature_extraction.text import TfidfVectorizer

from ..config import settings

# Prevent joblib physical-cores warning on Windows
os.environ.setdefault("LOKY_MAX_CPU_COUNT", "4")

warnings.filterwarnings("ignore")


# ---------------------------------------------------------------------------
# (a) Classification
# ---------------------------------------------------------------------------

def _make_pipeline(clf_name: str) -> Pipeline:
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)
    if clf_name == "naive_bayes":
        clf = MultinomialNB(alpha=0.5)
    elif clf_name == "knn":
        clf = KNeighborsClassifier(n_neighbors=5, metric="cosine")
    else:
        clf = DecisionTreeClassifier(max_depth=None, random_state=42)
    return Pipeline([("tfidf", vectorizer), ("clf", clf)])


def run_classification(
    texts: list[str],
    labels: list[str],
    holdout_df: pd.DataFrame | None = None,
) -> list[dict]:
    """Train and evaluate all three classifiers."""
    results = []
    split = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    idx = list(split.split(texts, labels))
    train_idx, test_idx = idx[0]
    X_train = [texts[i] for i in train_idx]
    y_train = [labels[i] for i in train_idx]
    X_test = [texts[i] for i in test_idx]
    y_test = [labels[i] for i in test_idx]

    for clf_name in ["naive_bayes", "decision_tree", "knn"]:
        pipe = _make_pipeline(clf_name)
        pipe.fit(X_train, y_train)
        y_pred = pipe.predict(X_test)

        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, average="weighted", zero_division=0)
        rec = recall_score(y_test, y_pred, average="weighted", zero_division=0)
        f1 = f1_score(y_test, y_pred, average="weighted", zero_division=0)
        cm = confusion_matrix(y_test, y_pred).tolist()

        cv_scores = cross_val_score(pipe, texts, labels, cv=5, scoring="accuracy")

        holdout_acc = None
        if holdout_df is not None and not holdout_df.empty:
            hx = holdout_df["text"].tolist()
            hy = holdout_df["expected_category"].tolist()
            try:
                hy_pred = pipe.predict(hx)
                holdout_acc = float(accuracy_score(hy, hy_pred))
            except Exception:
                holdout_acc = None

        results.append({
            "model_name": clf_name,
            "accuracy": round(acc, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
            "cv_accuracy_mean": round(float(cv_scores.mean()), 4),
            "cv_accuracy_std": round(float(cv_scores.std()), 4),
            "confusion_matrix": cm,
            "holdout_accuracy": round(holdout_acc, 4) if holdout_acc is not None else None,
            "pipeline": pipe,
        })

    return results


# ---------------------------------------------------------------------------
# (b) Clustering
# ---------------------------------------------------------------------------

def run_clustering(tfidf_matrix: np.ndarray, vectorizer: TfidfVectorizer) -> list[dict]:
    """K-Means clustering with silhouette k selection restricted to k in [3, 4, 5].

    Returns list of cluster descriptor dicts with readable label and 5 keyword chips.
    """
    n_samples = tfidf_matrix.shape[0]
    if n_samples < 4:
        return []

    best_k = 3
    best_score = -1.0
    k_range = [k for k in [3, 4, 5] if k < n_samples]

    for k in k_range:
        km = KMeans(n_clusters=k, random_state=42, n_init="auto")
        labels = km.fit_predict(tfidf_matrix)
        if len(set(labels)) < 2:
            continue
        score = silhouette_score(tfidf_matrix, labels)
        if score > best_score:
            best_score = score
            best_k = k

    km_final = KMeans(n_clusters=best_k, random_state=42, n_init="auto")
    cluster_labels = km_final.fit_predict(tfidf_matrix)

    feature_names = vectorizer.get_feature_names_out()
    clusters = []
    total = len(cluster_labels)

    for cid in range(best_k):
        indices = np.where(cluster_labels == cid)[0]
        size_pct = round(100 * len(indices) / total, 1)

        centroid = km_final.cluster_centers_[cid]
        top_idx = centroid.argsort()[-10:][::-1]
        top_terms = [str(feature_names[i]) for i in top_idx[:5]]

        label = _auto_label(top_terms)
        clusters.append({
            "cluster_id": cid,
            "label": label,
            "size_pct": size_pct,
            "top_terms": top_terms,
        })

    return clusters


def _auto_label(terms: list[str]) -> str:
    """Generate a clean human-readable cluster label from top terms."""
    label_map = {
        "placement": "Placements & Career Opportunities",
        "companies": "Campus Recruitment & Placements",
        "package": "Salary Packages & Placement",
        "internship": "Internships & Training",
        "fee": "Tuition Fees & Financials",
        "tuition": "Tuition & College Fees",
        "scholarship": "Scholarships & Financial Aid",
        "hostel": "Hostel & Accommodation",
        "admission": "Admissions & Application Process",
        "acpc": "ACPC Admissions & Cutoffs",
        "eligibility": "Eligibility & Criteria",
        "transport": "Campus Transport & Facilities",
        "library": "Library & Campus Resources",
        "canteen": "Canteen & Campus Dining",
        "syllabus": "Academics & Course Syllabus",
        "exam": "Exams & Academic Calendar",
        "department": "Engineering Departments",
        "cse": "Computer Engineering & IT",
    }
    for term in terms:
        for k, v in label_map.items():
            if k in term.lower():
                return v
    return f"Enquiries on {' & '.join([t.title() for t in terms[:2]])}"


# ---------------------------------------------------------------------------
# (c) Association Rules (Apriori)
# ---------------------------------------------------------------------------

def run_apriori(
    basket: pd.DataFrame,
    min_support: float | None = None,
    min_confidence: float | None = None,
    min_lift: float | None = None,
) -> list[dict]:
    """Run Apriori on session × topic/department basket and return raw rules."""
    _min_support = min_support if min_support is not None else settings.min_support
    _min_confidence = min_confidence if min_confidence is not None else settings.min_confidence
    _min_lift = min_lift if min_lift is not None else settings.min_lift

    if basket.empty or basket.shape[0] < 5:
        print(f"  [Apriori] Basket too small: {basket.shape[0]} sessions")
        return []

    n_sessions = basket.shape[0]
    items_per_session = basket.sum(axis=1)
    avg_items = items_per_session.mean()
    print(f"\n  [Apriori] Basket diagnostics:")
    print(f"    Sessions (≥2 items): {n_sessions}")
    print(f"    Avg items/session:   {avg_items:.2f}")
    print(f"    Item frequency table:")
    item_freq = basket.sum(axis=0).sort_values(ascending=False)
    for item, freq in item_freq.items():
        print(f"      {item}: {freq} ({100*freq/n_sessions:.1f}%)")

    try:
        print("\n    Frequent itemset diagnostics:")
        for supp in [0.05, 0.02, 0.01]:
            fi = apriori(basket, min_support=supp, use_colnames=True, max_len=3)
            print(f"      min_support={supp:.2f}: {len(fi)} itemsets found")

        frequent_items = apriori(
            basket,
            min_support=_min_support,
            use_colnames=True,
            max_len=3,
        )

        if frequent_items.empty:
            print(f"    No frequent itemsets found at min_support={_min_support}")
            return []

        rules_df = association_rules(
            frequent_items,
            metric="confidence",
            min_threshold=_min_confidence,
        )

        if not rules_df.empty:
            rules_df = rules_df[rules_df["lift"] > _min_lift]

        print(f"\n    Association rules found (min_support={_min_support}, min_conf={_min_confidence}, min_lift={_min_lift}): {len(rules_df)}")
        if not rules_df.empty:
            print("    Top 10 rules by lift × confidence:")
            rules_df = rules_df.copy()
            rules_df["score"] = rules_df["lift"] * rules_df["confidence"]
            top10 = rules_df.nlargest(10, "score")
            for _, row in top10.iterrows():
                ant = ", ".join(sorted(row["antecedents"]))
                con = ", ".join(sorted(row["consequents"]))
                print(f"      {ant} → {con}  "
                      f"sup={row['support']:.4f} conf={row['confidence']:.4f} lift={row['lift']:.4f}")

        raw_rules = []
        for _, row in rules_df.iterrows():
            raw_rules.append({
                "antecedent": ", ".join(sorted(row["antecedents"])),
                "consequent": ", ".join(sorted(row["consequents"])),
                "support": round(float(row["support"]), 4),
                "confidence": round(float(row["confidence"]), 4),
                "lift": round(float(row["lift"]), 4),
            })
        return raw_rules
    except Exception as e:
        print(f"  [Apriori] Error: {e}")
        import traceback
        traceback.print_exc()
        return []
