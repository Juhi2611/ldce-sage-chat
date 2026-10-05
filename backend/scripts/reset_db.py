"""Reset the database: delete all rows (or recreate) and reseed once.

Usage
-----
    python scripts/reset_db.py [--keep-schema]

Options
-------
  --keep-schema   DELETE rows but keep the schema. Default: drop + recreate all tables.
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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, init_db, engine, Base
from app.models import Enquiry, Session as SessionModel, Feedback, MinedRule, MinedCluster, ModelMetric, KDDRunLog


def reset(keep_schema: bool = False):
    if keep_schema:
        print("Deleting all rows (keeping schema)…")
        db = SessionLocal()
        try:
            for model in [Feedback, Enquiry, MinedRule, MinedCluster, ModelMetric, KDDRunLog, SessionModel]:
                n = db.query(model).delete()
                print(f"  Deleted {n} rows from {model.__tablename__}")
            db.commit()
        finally:
            db.close()
    else:
        print("Dropping all tables and recreating…")
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        print("  Tables recreated.")


def seed_once():
    """Import and run the seed script exactly once."""
    from scripts.seed_synthetic import generate
    db = SessionLocal()
    try:
        # Guard against duplicate seeding: check if synthetic rows exist
        existing = db.query(Enquiry).filter(Enquiry.is_synthetic == True).count()  # noqa: E712
        if existing > 0:
            print(f"\n⚠  Already {existing} synthetic rows — skipping reseed.")
            return existing
        print("\nSeeding synthetic data…")
        n = generate(db)
        print(f"  Inserted {n} synthetic rows.")
        return n
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Reset LDCE database and reseed.")
    parser.add_argument("--keep-schema", action="store_true",
                        help="DELETE rows but preserve table schema.")
    args = parser.parse_args()

    init_db()
    reset(keep_schema=args.keep_schema)
    n = seed_once()

    # Verify
    db = SessionLocal()
    total = db.query(Enquiry).count()
    synthetic = db.query(Enquiry).filter(Enquiry.is_synthetic == True).count()  # noqa: E712
    sessions = db.query(SessionModel).count()
    db.close()

    print(f"\n✅ Database reset complete.")
    print(f"   Total rows:     {total}")
    print(f"   Synthetic rows: {synthetic}")
    print(f"   Sessions:       {sessions}")


if __name__ == "__main__":
    main()
