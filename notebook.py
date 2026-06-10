import json
from datetime import date
from db import get_cursor
import curator


def save_page(user_id: str, raw_text: str, annotations: dict) -> tuple[str, str]:
    """Curates the page (title/summary/type/resources), inserts into DB. Returns (page_id, title)."""
    import nlp as _nlp
    curated = curator.curate_page(raw_text)
    category = _nlp.detect_category(raw_text[:300])
    title = curated["title"]
    metadata = {
        "category": category,
        "summary": curated["summary"],
        "page_type": curated["page_type"],
        "links": curated["links"],
        "books": curated["books"],
    }
    with get_cursor() as cur:
        cur.execute(
            """INSERT INTO pages (user_id, title, date, raw_text, annotations, metadata)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING id::text""",
            (user_id, title, date.today(), raw_text,
             json.dumps(annotations), json.dumps(metadata)),
        )
        page_id = cur.fetchone()["id"]
    return page_id, title


def list_pages(user_id: str) -> list[dict]:
    """Sidebar list — returns [{id, title, date, category, page_type, preview}] newest-first, max 50.

    Fetches the first 300 chars of raw_text to detect category and build a hover
    preview without pulling the full lesson text over the wire.
    """
    import nlp as _nlp
    with get_cursor() as cur:
        cur.execute(
            "SELECT id::text, title, date::text, "
            "LEFT(raw_text, 300) AS snippet, "
            "COALESCE(metadata->>'category', '') AS stored_category, "
            "COALESCE(metadata->>'page_type', 'lesson') AS page_type "
            "FROM pages WHERE user_id = %s ORDER BY created_at DESC LIMIT 50",
            (user_id,),
        )
        rows = [dict(r) for r in cur.fetchall()]
    for row in rows:
        snippet = row.pop("snippet", "") or ""
        stored_cat = row.pop("stored_category", "") or ""
        row["category"] = stored_cat if stored_cat else _nlp.detect_category(snippet)
        preview = snippet[:100]
        row["preview"] = preview + ("…" if len(snippet) > 100 else "")
    return rows


def list_resources(user_id: str) -> list[dict]:
    """Return resource-type pages: [{id, title, links, books}], newest-first."""
    with get_cursor() as cur:
        cur.execute(
            "SELECT id::text, title, "
            "COALESCE(metadata->'links', '[]'::jsonb) AS links, "
            "COALESCE(metadata->'books', '[]'::jsonb) AS books "
            "FROM pages WHERE user_id = %s AND metadata->>'page_type' = 'resource' "
            "ORDER BY created_at DESC",
            (user_id,),
        )
        return [dict(r) for r in cur.fetchall()]


def update_title(page_id: str, user_id: str, title: str) -> str:
    """Persist a user-edited title (overrides the auto-generated one). Returns the saved title."""
    title = (title or "").strip()[:80] or "Untitled Lesson"
    with get_cursor() as cur:
        cur.execute(
            "UPDATE pages SET title = %s WHERE id = %s AND user_id = %s",
            (title, page_id, user_id),
        )
    return title


def get_page(page_id: str, user_id: str) -> dict | None:
    with get_cursor() as cur:
        cur.execute(
            "SELECT id::text, title, raw_text, annotations "
            "FROM pages WHERE id = %s AND user_id = %s",
            (page_id, user_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def update_annotations(page_id: str, annotations: dict) -> None:
    """Persist LLM-enriched annotations back to the page row."""
    with get_cursor() as cur:
        cur.execute(
            "UPDATE pages SET annotations = %s WHERE id = %s",
            (json.dumps(annotations), page_id),
        )


def update_page(page_id: str, user_id: str, raw_text: str, annotations: dict) -> str:
    """Update page content in-place, keep existing title. Returns the title."""
    with get_cursor() as cur:
        cur.execute(
            "SELECT title FROM pages WHERE id = %s AND user_id = %s",
            (page_id, user_id),
        )
        row = cur.fetchone()
        title = row["title"] if row else raw_text.split("\n")[0][:60]
    with get_cursor() as cur:
        cur.execute(
            "UPDATE pages SET raw_text = %s, annotations = %s WHERE id = %s AND user_id = %s",
            (raw_text, json.dumps(annotations), page_id, user_id),
        )
    return title


def delete_page(page_id: str, user_id: str) -> bool:
    """Delete page row (exercises cascade). Returns True if a row was deleted."""
    with get_cursor() as cur:
        cur.execute(
            "DELETE FROM pages WHERE id = %s AND user_id = %s RETURNING id",
            (page_id, user_id),
        )
        return cur.fetchone() is not None
