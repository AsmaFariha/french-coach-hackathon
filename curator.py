"""
Curator pass — one LLM call per saved page.

Classifies a page as a "lesson" (French class notes/vocab/grammar) or a
"resource" (links, apps, book recommendations) and extracts a friendly
title, a one-line summary, and — for resource pages — structured links/books
for the Resources tab.
"""
import logging
import llm
import prompts

logger = logging.getLogger(__name__)


def _fallback(raw_text: str) -> dict:
    first_line = raw_text.strip().split("\n", 1)[0].lstrip("#").strip()
    return {
        "title": (first_line or "Untitled Lesson")[:80],
        "summary": "",
        "page_type": "lesson",
        "links": [],
        "books": [],
    }


def curate_page(raw_text: str) -> dict:
    """Return {title, summary, page_type, links, books} for a page's raw text."""
    fallback = _fallback(raw_text)
    result = llm.chat_json(prompts.CURATOR_SYSTEM, raw_text[:2000], fallback=fallback)

    title = (result.get("title") or fallback["title"]).strip()[:80]
    summary = (result.get("summary") or "").strip()
    page_type = result.get("page_type") if result.get("page_type") in ("lesson", "resource") else "lesson"

    links, books = [], []
    if page_type == "resource":
        for link in result.get("links") or []:
            if isinstance(link, dict) and link.get("url"):
                links.append({
                    "label": str(link.get("label") or link["url"])[:120],
                    "url": str(link["url"]),
                })
        for book in result.get("books") or []:
            if isinstance(book, dict) and book.get("title"):
                books.append({
                    "title": str(book.get("title"))[:200],
                    "author": str(book.get("author") or "")[:120],
                    "note": str(book.get("note") or "")[:200],
                })

    return {
        "title": title,
        "summary": summary,
        "page_type": page_type,
        "links": links,
        "books": books,
    }
