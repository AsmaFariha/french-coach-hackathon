"""
Points ledger and daily summary.
Points are ALWAYS additive — never deducted.
"""
import json
import logging
import os
from db import get_cursor
import llm
import prompts

logger = logging.getLogger(__name__)

_SYLLABUS_PATH = os.path.join(os.path.dirname(__file__), "syllabus_full_a1_c2.json")
_a1_a2_concepts: list[dict] | None = None

POINT_VALUES = {
    "daily_open":     5,
    "saved_lesson":  10,
    "exercise_done":  5,
    "dialogue_turn":  3,
    "pronunciation":  5,
    "word_explored":  1,
    "photo_exercise": 8,
}


def try_daily_open(user_id: str) -> int:
    """Award daily-open points once per calendar day. Returns points awarded (0 if already awarded)."""
    try:
        with get_cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS n FROM points "
                "WHERE user_id = %s AND reason = 'daily_open' AND earned_at::date = CURRENT_DATE",
                (user_id,),
            )
            if cur.fetchone()["n"] > 0:
                return 0
            amount = POINT_VALUES["daily_open"]
            cur.execute(
                "INSERT INTO points (user_id, reason, amount) VALUES (%s, %s, %s)",
                (user_id, "daily_open", amount),
            )
            return amount
    except Exception as e:
        logger.warning("try_daily_open failed: %s", e)
        return 0


def add_points(user_id: str, reason: str) -> int:
    """Award points for an action. Returns points awarded."""
    amount = POINT_VALUES.get(reason, 2)
    try:
        with get_cursor() as cur:
            cur.execute(
                "INSERT INTO points (user_id, reason, amount) VALUES (%s, %s, %s)",
                (user_id, reason, amount),
            )
    except Exception as e:
        logger.warning("add_points failed: %s", e)
    return amount


def get_total_points(user_id: str) -> int:
    try:
        with get_cursor() as cur:
            cur.execute(
                "SELECT COALESCE(SUM(amount), 0) AS total FROM points WHERE user_id = %s",
                (user_id,),
            )
            return int(cur.fetchone()["total"])
    except Exception:
        return 0


def get_daily_stats(user_id: str) -> dict:
    try:
        with get_cursor() as cur:
            cur.execute(
                """SELECT
                   (SELECT COUNT(*) FROM pages     WHERE user_id=%s AND date=CURRENT_DATE)          AS pages_today,
                   (SELECT COUNT(*) FROM exercises WHERE user_id=%s AND created_at::date=CURRENT_DATE) AS exercises_today,
                   (SELECT COUNT(*) FROM points    WHERE user_id=%s AND reason='dialogue_turn'
                                                    AND earned_at::date=CURRENT_DATE)               AS dialogue_turns,
                   (SELECT COUNT(*) FROM points    WHERE user_id=%s AND reason='word_explored'
                                                    AND earned_at::date=CURRENT_DATE)               AS words_clicked,
                   (SELECT COALESCE(SUM(amount),0) FROM points WHERE user_id=%s)                    AS total_points""",
                (user_id,)*5,
            )
            return {k: int(v) for k, v in dict(cur.fetchone()).items()}
    except Exception:
        return {"pages_today":0,"exercises_today":0,"dialogue_turns":0,"words_clicked":0,"total_points":0}


def _load_a1_a2_concepts() -> list[dict]:
    global _a1_a2_concepts
    if _a1_a2_concepts is None:
        try:
            with open(_SYLLABUS_PATH, encoding="utf-8") as f:
                concepts = json.load(f)["concepts"]
            _a1_a2_concepts = [c for c in concepts if c.get("cefr_level") in ("A1", "A2")]
        except Exception as e:
            logger.warning("_load_a1_a2_concepts failed: %s", e)
            _a1_a2_concepts = []
    return _a1_a2_concepts


def get_concepts_progress() -> dict:
    """Concepts the Coach Agent has identified as covered, plus the next one
    up in syllabus order — powers the Summary tab's strengths + next focus."""
    try:
        with get_cursor() as cur:
            cur.execute("SELECT id FROM concepts WHERE covered_on IS NOT NULL")
            covered_ids = {r["id"] for r in cur.fetchall()}
    except Exception:
        covered_ids = set()
    a1_a2 = _load_a1_a2_concepts()
    covered = [c["name"] for c in a1_a2 if c["id"] in covered_ids]
    next_concept = next((c["name"] for c in a1_a2 if c["id"] not in covered_ids), None)
    return {"covered": covered, "next": next_concept}


def get_daily_summary(user_id: str) -> str:
    stats = get_daily_stats(user_id)
    concepts = get_concepts_progress()
    result = llm.chat([
        {"role": "system", "content": prompts.DAILY_SUMMARY_SYSTEM},
        {"role": "user",   "content": prompts.daily_summary_user(stats, concepts)},
    ])
    if result.startswith("⚠"):
        return _fallback(stats, concepts)
    return result


def _fallback(stats: dict, concepts: dict | None = None) -> str:
    total = stats.get("total_points", 0)
    pages = stats.get("pages_today", 0)
    ex    = stats.get("exercises_today", 0)
    lines = [f"You've earned **{total} points** — great work!"]
    if pages:
        lines.append(f"You saved {pages} lesson{'s' if pages > 1 else ''} today.")
    if ex:
        lines.append(f"You completed {ex} exercise{'s' if ex > 1 else ''}.")
    covered = (concepts or {}).get("covered") or []
    if covered:
        lines.append(f"You're building skills in: {', '.join(covered[-3:])}.")
    next_concept = (concepts or {}).get("next")
    if next_concept:
        lines.append(f"Ready to practice next: {next_concept}.")
    else:
        lines.append("Ready to explore next: more vocabulary and dialogue practice. 🇫🇷")
    return "\n\n".join(lines)
