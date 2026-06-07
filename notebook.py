import json
from datetime import date
from db import get_cursor
import llm


def save_page(user_id: str, raw_text: str, annotations: dict) -> tuple[str, str]:
    """LLM-titles the page, inserts into DB. Returns (page_id, title)."""
    title = llm.generate_page_title(raw_text)
    with get_cursor() as cur:
        cur.execute(
            """INSERT INTO pages (user_id, title, date, raw_text, annotations)
               VALUES (%s, %s, %s, %s, %s) RETURNING id::text""",
            (user_id, title, date.today(), raw_text, json.dumps(annotations)),
        )
        page_id = cur.fetchone()["id"]
    return page_id, title


def list_pages(user_id: str) -> list[dict]:
    """Sidebar list — returns [{id, title, date}] newest-first, max 50."""
    with get_cursor() as cur:
        cur.execute(
            "SELECT id::text, title, date::text FROM pages "
            "WHERE user_id = %s ORDER BY created_at DESC LIMIT 50",
            (user_id,),
        )
        return [dict(r) for r in cur.fetchall()]


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
