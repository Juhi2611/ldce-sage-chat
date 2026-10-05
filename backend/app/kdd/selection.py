"""KDD Step 1 — Data Selection.

Load relevant enquiry rows from the database, excluding:
  - Small-talk records (is_smalltalk flag stored at logging time is absent in model,
    so we exclude rows where predicted_category is NULL or 'unknown')
  - Rows with empty/blank normalized_question
  - Optionally, rows flagged is_synthetic=True if include_synthetic=False
"""
import pandas as pd
from sqlalchemy.orm import Session

from ..models import Enquiry


def select_data(db: Session, include_synthetic: bool = True) -> pd.DataFrame:
    """Select and return a DataFrame of valid enquiry rows.

    Parameters
    ----------
    db : sqlalchemy Session
    include_synthetic : bool
        If False, synthetic demo rows are excluded from analysis.

    Returns
    -------
    pandas DataFrame with columns matching the Enquiry model.
    """
    query = db.query(Enquiry)

    if not include_synthetic:
        query = query.filter(Enquiry.is_synthetic == False)  # noqa: E712

    # Exclude rows without a valid category (unresolved noise at intake)
    query = query.filter(
        Enquiry.normalized_question != "",
        Enquiry.normalized_question.isnot(None),
        Enquiry.predicted_category.isnot(None),
        Enquiry.predicted_category != "Unknown",
    )

    rows = query.all()

    data = [
        {
            "id": r.id,
            "session_id": r.session_id,
            "raw_question": r.raw_question,
            "normalized_question": r.normalized_question,
            "predicted_category": r.predicted_category,
            "predicted_department": r.predicted_department,
            "predicted_topic": r.predicted_topic,
            "confidence": r.confidence,
            "resolved": r.resolved,
            "created_at": r.created_at,
            "is_synthetic": r.is_synthetic,
        }
        for r in rows
    ]
    return pd.DataFrame(data)
