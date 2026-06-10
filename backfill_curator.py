"""
One-off script: run the curator pass over every existing page so the
notebook gets friendly auto-titles, summaries, page_type (lesson/resource),
and extracted links/books — without the user re-saving anything.

Run inside the app container (needs llm.py + nlp.py + curator.py):
    docker compose exec -T app python backfill_curator.py [--dry-run]
"""

import sys
import json
import db
import curator
import nlp as _nlp

USER_ID = "dev_user"


def main():
    dry_run = "--dry-run" in sys.argv
    with db.get_cursor() as cur:
        cur.execute(
            "SELECT id::text, title, raw_text, metadata "
            "FROM pages WHERE user_id = %s ORDER BY date, created_at",
            (USER_ID,),
        )
        pages = cur.fetchall()

    print(f"Curating {len(pages)} pages...\n")
    for page in pages:
        result = curator.curate_page(page["raw_text"])
        category = _nlp.detect_category(page["raw_text"][:300])
        metadata = dict(page["metadata"] or {})
        metadata.update({
            "category": category,
            "summary": result["summary"],
            "page_type": result["page_type"],
            "links": result["links"],
            "books": result["books"],
        })
        old_title = page["title"]
        new_title = result["title"]
        tag = "📚" if result["page_type"] == "resource" else "📓"
        print(f"  {tag} {old_title!r:35} -> {new_title!r}  [{category}]")
        if not dry_run:
            with db.get_cursor() as cur:
                cur.execute(
                    "UPDATE pages SET title = %s, metadata = %s WHERE id = %s",
                    (new_title, json.dumps(metadata), page["id"]),
                )

    if dry_run:
        print("\n(dry run — no changes made)")
    else:
        print(f"\nUpdated {len(pages)} pages.")


if __name__ == "__main__":
    main()
