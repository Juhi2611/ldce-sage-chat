"""Delete all non-synthetic enquiry records and their feedback rows.

Usage
-----
    python scripts/clear_test_enquiries.py
"""
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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, init_db
from app.models import Enquiry, Feedback


def clear_test_enquiries() -> tuple[int, int]:
    init_db()
    db = SessionLocal()
    try:
        test_enquiries = db.query(Enquiry).filter(Enquiry.is_synthetic == False).all()  # noqa: E712
        test_ids = [e.id for e in test_enquiries]

        deleted_feedback = 0
        if test_ids:
            deleted_feedback = (
                db.query(Feedback).filter(Feedback.enquiry_id.in_(test_ids)).delete(synchronize_session=False)
            )
            deleted_enquiries = (
                db.query(Enquiry).filter(Enquiry.id.in_(test_ids)).delete(synchronize_session=False)
            )
        else:
            deleted_enquiries = 0

        db.commit()
        return deleted_enquiries, deleted_feedback
    finally:
        db.close()


def main():
    print("Clearing test (non-synthetic) enquiries…")
    del_enq, del_fb = clear_test_enquiries()
    db = SessionLocal()
    remaining_total = db.query(Enquiry).count()
    remaining_synth = db.query(Enquiry).filter(Enquiry.is_synthetic == True).count()  # noqa: E712
    db.close()

    print(f"  Deleted {del_enq} test enquiry rows.")
    print(f"  Deleted {del_fb} associated feedback rows.")
    print(f"  Remaining rows in DB: {remaining_total} (all synthetic: {remaining_synth})")


if __name__ == "__main__":
    main()
