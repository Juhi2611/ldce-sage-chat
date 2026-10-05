"""Run the KDD pipeline from the command line.

Usage
-----
    python run_kdd.py [--exclude-synthetic]

Options
-------
  --exclude-synthetic   Analyse only real (non-synthetic) enquiries.
"""
import argparse
import os
import sys
import uuid
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
from app.kdd.pipeline import run_kdd


def main():
    parser = argparse.ArgumentParser(description="Run the LDCE KDD analytics pipeline.")
    parser.add_argument(
        "--exclude-synthetic",
        action="store_true",
        help="If set, synthetic demo rows are excluded from analysis.",
    )
    args = parser.parse_args()

    include_synthetic = not args.exclude_synthetic
    run_id = str(uuid.uuid4())[:8]

    print(f"\nKDD Pipeline — run_id: {run_id}")
    print(f"Include synthetic data: {include_synthetic}")
    print("Starting…\n")

    init_db()
    db = SessionLocal()
    try:
        summary = run_kdd(run_id=run_id, db=db, include_synthetic=include_synthetic)
        if "error" in summary:
            print(f"❌ Error: {summary['error']}")
            sys.exit(1)
        print("\n✅ KDD pipeline completed!")
        print(f"   Best model         : {summary.get('best_model')}")
        print(f"   Clusters discovered: {summary.get('n_clusters')}")
        print(f"   Association rules  : {summary.get('n_rules_useful')} useful / {summary.get('n_rules_total')} total")
        print(f"\nPreprocessing report : {summary.get('preprocessing')}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
