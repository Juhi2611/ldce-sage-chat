"""List all knowledge base entries that still need verification.

Run this script to see which entries need facts to be confirmed from ldce.ac.in.

Usage
-----
    python list_unverified.py
"""
import json
import sys
from pathlib import Path

KB_PATH = Path(__file__).resolve().parent.parent / "data" / "knowledge_base.json"


def main():
    with open(KB_PATH, encoding="utf-8") as f:
        kb = json.load(f)

    unverified = [e for e in kb if e.get("needs_verification")]
    verified = [e for e in kb if not e.get("needs_verification")]

    print(f"\nKnowledge Base Verification Status")
    print(f"  Total entries     : {len(kb)}")
    print(f"  Verified          : {len(verified)}")
    print(f"  Needs verification: {len(unverified)}\n")

    if not unverified:
        print("✅ All entries verified!")
        return

    print(f"{'ID':<20} {'Category':<20} {'Subcategory':<25} {'Source URL'}")
    print("-" * 90)
    for e in unverified:
        print(
            f"{e['id']:<20} {e['category']:<20} {(e.get('subcategory') or ''):<25} "
            f"{e.get('source_url', 'N/A')}"
        )

    print(f"\nTo verify: open each source URL and fill in the exact values in knowledge_base.json,")
    print(f"then set needs_verification: false for that entry.")


if __name__ == "__main__":
    main()
