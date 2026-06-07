"""
One-off script: import exported Notion .md files into the pages table.
Run from the project root (host machine) — uses localhost:5432 directly.

Usage:
    python import_lessons.py [--dry-run]
"""

import os
import re
import sys
import glob
from datetime import date
import psycopg2
from psycopg2.extras import RealDictCursor

NOTES_DIR = "/tmp/french_notes/part1/French Learning Dashboard"
USER_ID = "dev_user"
TODAY = date.today().isoformat()

# When running from the host (not inside Docker), db hostname → localhost
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:localdevpassword@localhost:5432/frenchcoach",
).replace("@db:", "@localhost:")

# Strip the Notion UUID hash appended to filenames: "Class A2 U2 L2 <32-hex>.md"
_NOTION_HASH = re.compile(r"\s+[0-9a-f]{32}$", re.IGNORECASE)


def clean_title(filename: str) -> str:
    stem = os.path.splitext(os.path.basename(filename))[0]
    return _NOTION_HASH.sub("", stem).strip()


def load_md_files():
    # Top-level .md files only — nested ones (inside Class X/ subdirs) are the same
    # lesson duplicated as Notion sub-pages; we import each unique path.
    paths = sorted(glob.glob(os.path.join(NOTES_DIR, "**", "*.md"), recursive=True))
    seen_titles: set[str] = set()
    results = []
    for path in paths:
        title = clean_title(path)
        if title in seen_titles:
            continue
        seen_titles.add(title)
        with open(path, encoding="utf-8") as f:
            raw_text = f.read().strip()
        if not raw_text:
            continue
        results.append((title, raw_text, path))
    return results


def main():
    dry_run = "--dry-run" in sys.argv
    lessons = load_md_files()
    print(f"Found {len(lessons)} unique lessons to import.")

    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            imported = 0
            skipped = 0
            for title, raw_text, path in lessons:
                # Skip if a page with the same title + user already exists
                cur.execute(
                    "SELECT id FROM pages WHERE user_id = %s AND title = %s",
                    (USER_ID, title),
                )
                if cur.fetchone():
                    print(f"  SKIP (exists): {title}")
                    skipped += 1
                    continue

                if dry_run:
                    print(f"  DRY-RUN: would insert '{title}'")
                    imported += 1
                    continue

                cur.execute(
                    """
                    INSERT INTO pages (user_id, title, date, raw_text, annotations)
                    VALUES (%s, %s, %s, %s, %s::jsonb)
                    """,
                    (USER_ID, title, TODAY, raw_text, "{}"),
                )
                print(f"  Imported: {title}")
                imported += 1

        if not dry_run:
            conn.commit()
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM pages WHERE user_id = %s", (USER_ID,))
                total = cur.fetchone()[0]
            print(f"\nDone. Imported {imported} lessons, skipped {skipped} duplicates.")
            print(f"Total pages in DB for '{USER_ID}': {total}")
        else:
            print(f"\nDry-run complete. Would import {imported} lessons.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
