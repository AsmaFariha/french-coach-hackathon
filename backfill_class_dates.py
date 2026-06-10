"""
One-off script: assign real-feeling sequential dates to the "Class N M" /
"Class A2 ..." lecture pages, which were all imported with the same date
(the day of the Notion export). These 20 pages are an actual chronological
course sequence (Class 1.1 -> 1.5, 2.1 -> 2.7, A2 1 -> 3, A2 U1 L4 -> L6,
A2 U2 L1 -> L2), so we space them every other day starting April 28 — that
lands the last one (Class A2 U2 L2) on June 5, just before "today".

Run from the host (uses localhost:5432) or inside the app container.

Usage:
    python backfill_class_dates.py [--dry-run]
"""

import os
import sys
from datetime import date, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor

USER_ID = "dev_user"
START_DATE = date(2026, 4, 28)
STEP_DAYS = 2

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:localdevpassword@localhost:5432/frenchcoach",
).replace("@db:", "@localhost:")

# Chronological order of the course sequence
CLASS_TITLES = (
    [f"Class 1 {n}" for n in range(1, 6)]
    + [f"Class 2 {n}" for n in range(1, 8)]
    + [f"Class A2 {n}" for n in range(1, 4)]
    + [f"Class A2 U1 L{n}" for n in range(4, 7)]
    + [f"Class A2 U2 L{n}" for n in range(1, 3)]
)


def main():
    dry_run = "--dry-run" in sys.argv
    conn = psycopg2.connect(DATABASE_URL)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        for i, title in enumerate(CLASS_TITLES):
            new_date = START_DATE + timedelta(days=i * STEP_DAYS)
            cur.execute(
                "SELECT id::text, date::text FROM pages WHERE user_id = %s AND title = %s",
                (USER_ID, title),
            )
            row = cur.fetchone()
            if not row:
                print(f"  ⚠ not found: {title!r}")
                continue
            print(f"  {title:<18} {row['date']} -> {new_date.isoformat()}")
            if not dry_run:
                cur.execute("UPDATE pages SET date = %s WHERE id = %s", (new_date, row["id"]))
    if dry_run:
        conn.rollback()
        print("\n(dry run — no changes made)")
    else:
        conn.commit()
        print(f"\nUpdated {len(CLASS_TITLES)} lesson dates.")
    conn.close()


if __name__ == "__main__":
    main()
