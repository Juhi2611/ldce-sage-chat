"""KDD Step 2 — Data Preprocessing.

Applies:
  1. Duplicate removal — same session_id + same normalized_question within 60 seconds
  2. Null / blank value handling
  3. Text re-normalisation of normalized_question column
  4. Returns a preprocessing report with row counts

This module is intentionally kept readable for viva presentation.
"""
import pandas as pd
from datetime import timedelta

from ..chatbot.normalizer import normalize


def preprocess(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Clean and deduplicate the selected dataset.

    Parameters
    ----------
    df : pd.DataFrame
        Raw selected dataset from selection.select_data().

    Returns
    -------
    (cleaned_df, report)
    report contains: rows_before, rows_after, duplicates_removed, nulls_handled
    """
    report: dict = {
        "rows_before": len(df),
        "duplicates_removed": 0,
        "nulls_handled": 0,
        "rows_after": 0,
    }

    if df.empty:
        report["rows_after"] = 0
        return df, report

    # --- Step 2.1: Handle missing values ---
    # Count rows with at least one null field, bounded by total row count
    df = df.copy()
    rows_with_nulls = int(df.isnull().any(axis=1).sum())

    df["predicted_department"] = df["predicted_department"].fillna("General")
    df["predicted_topic"] = df["predicted_topic"].fillna("general")
    df["normalized_question"] = df["normalized_question"].fillna("")
    # Drop rows where normalized_question is empty even after fill
    df = df[df["normalized_question"].str.strip() != ""]

    report["nulls_handled"] = min(rows_with_nulls, report["rows_before"])

    # --- Step 2.2: Re-normalise text ---
    df["normalized_question"] = df["normalized_question"].apply(normalize)

    # --- Step 2.3: Remove 60-second session duplicates ---
    if "created_at" in df.columns and not df["created_at"].isna().all():
        df = df.sort_values(["session_id", "normalized_question", "created_at"])
        mask = []
        seen: dict[tuple, pd.Timestamp] = {}
        for _, row in df.iterrows():
            key = (row["session_id"], row["normalized_question"])
            ts = row["created_at"]
            if pd.isna(ts):
                mask.append(True)
                continue
            if key in seen:
                delta = abs((pd.Timestamp(ts) - seen[key]).total_seconds())
                if delta <= 60:
                    mask.append(False)  # duplicate within 60 s
                    continue
            seen[key] = pd.Timestamp(ts)
            mask.append(True)
        before = len(df)
        df = df[mask].reset_index(drop=True)
        report["duplicates_removed"] = before - len(df)

    report["rows_after"] = len(df)
    return df, report
