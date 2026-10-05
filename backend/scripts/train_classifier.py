"""Train and evaluate all three classifiers.

Usage
-----
    python train_classifier.py [--algorithm naive_bayes|decision_tree|knn]

Outputs
-------
- Trains on KB + template corpus (+ external intents.json if present)
- Prints per-model: accuracy, precision, recall, F1, 5-fold CV stats
- Prints holdout accuracy on backend/data/holdout_questions.csv
- Prints confidence-distribution percentile table for threshold tuning
- Saves best model to backend/models_saved/
"""
import argparse
import os
import sys
from pathlib import Path

# Prevent joblib physical-cores warning on Windows
os.environ.setdefault("LOKY_MAX_CPU_COUNT", "4")

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix
)
from sklearn.model_selection import StratifiedShuffleSplit, cross_val_score

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.chatbot.classifier import (
    get_training_data, train_and_save, _build_pipeline, CATEGORIES
)
from app.chatbot.normalizer import normalize


def print_confidence_distribution(pipe, texts: list[str]) -> None:
    """Print a percentile table of classifier confidence scores for threshold tuning."""
    proba = pipe.predict_proba(texts)
    max_conf = proba.max(axis=1)
    percentiles = [10, 25, 50, 60, 70, 80, 90, 95, 99]
    print("\n--- Confidence Distribution (max-class probability) ---")
    print(f"{'Percentile':>12} | {'Confidence':>12}")
    print("-" * 28)
    for p in percentiles:
        val = np.percentile(max_conf, p)
        print(f"{p:>11}% | {val:>12.4f}")
    print(f"\n  Mean:   {max_conf.mean():.4f}")
    print(f"  Median: {np.median(max_conf):.4f}")
    print(f"  Std:    {max_conf.std():.4f}")
    print(f"\n  Suggested threshold review:")
    pct_above = {t: (max_conf >= t).mean() for t in [0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.60]}
    for t, frac in pct_above.items():
        print(f"    >= {t:.2f}: {frac*100:.1f}% of examples answered (not fallback)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--algorithm", default=None,
                        choices=["naive_bayes", "decision_tree", "knn"],
                        help="Train only this algorithm; default trains all three.")
    args = parser.parse_args()

    print("Loading training data…")
    texts, labels = get_training_data()
    print(f"  Total examples: {len(texts)}")
    from collections import Counter
    for cat, cnt in sorted(Counter(labels).items()):
        print(f"    {cat}: {cnt}")

    holdout_path = Path(__file__).parent.parent / "data" / "holdout_questions.csv"
    holdout_df = None
    if holdout_path.exists():
        holdout_df = pd.read_csv(holdout_path)[["text", "expected_category"]].dropna()
        print(f"\nHoldout set: {len(holdout_df)} hand-written examples")

    # Split
    split = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    idx = list(split.split(texts, labels))
    train_idx, test_idx = idx[0]
    X_train = [texts[i] for i in train_idx]
    y_train = [labels[i] for i in train_idx]
    X_test = [texts[i] for i in test_idx]
    y_test = [labels[i] for i in test_idx]

    algos = [args.algorithm] if args.algorithm else ["naive_bayes", "decision_tree", "knn"]
    best = {"algo": None, "f1": -1.0}

    for algo in algos:
        print(f"\n{'='*60}")
        print(f"  Algorithm: {algo.upper()}")
        print(f"{'='*60}")

        pipe = _build_pipeline(algo)
        pipe.fit(X_train, y_train)
        y_pred = pipe.predict(X_test)

        acc = accuracy_score(y_test, y_pred)
        print(f"\n  Accuracy  (test set):  {acc:.4f}")
        print(classification_report(y_test, y_pred, target_names=sorted(set(labels)), zero_division=0))

        cv = cross_val_score(pipe, texts, labels, cv=5, scoring="accuracy")
        print(f"  5-fold CV accuracy:    {cv.mean():.4f} ± {cv.std():.4f}")

        # Holdout
        if holdout_df is not None:
            hx = holdout_df["text"].apply(normalize).tolist()
            hy = holdout_df["expected_category"].tolist()
            hy_pred = pipe.predict(hx)
            h_acc = accuracy_score(hy, hy_pred)
            print(f"\n  Holdout accuracy:      {h_acc:.4f}  (hand-written, not template)")

        # Confidence distribution
        all_proba = pipe.predict_proba(X_test)
        pipe_for_dist = type("Pipe", (), {"predict_proba": lambda s, X: pipe.predict_proba(X)})()
        print_confidence_distribution(pipe, X_test)

        from sklearn.metrics import f1_score
        f1 = f1_score(y_test, y_pred, average="weighted", zero_division=0)
        if f1 > best["f1"]:
            best = {"algo": algo, "f1": f1}

    # Save all models
    print("\nSaving all trained models…")
    for algo in algos:
        saved = train_and_save(algo)
        print(f"  Saved: models_saved/classifier_{algo}.joblib")

    print(f"\n✅ Best model: {best['algo']} (F1 = {best['f1']:.4f})")
    print("Re-run with --algorithm <name> to retrain a single model.")


if __name__ == "__main__":
    main()
