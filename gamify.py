"""
Points ledger and daily summary.
Points are ALWAYS additive — never deducted.
"""
import logging
from db import get_cursor
import llm
import prompts

logger = logging.getLogger(__name__)

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


def get_daily_summary(user_id: str) -> str:
    stats = get_daily_stats(user_id)
    result = llm.chat([
        {"role": "system", "content": prompts.DAILY_SUMMARY_SYSTEM},
        {"role": "user",   "content": prompts.daily_summary_user(stats)},
    ])
    if result.startswith("⚠"):
        return _fallback(stats)
    return result


def _fallback(stats: dict) -> str:
    total = stats.get("total_points", 0)
    pages = stats.get("pages_today", 0)
    ex    = stats.get("exercises_today", 0)
    lines = [f"You've earned **{total} points** — great work!"]
    if pages:
        lines.append(f"You saved {pages} lesson{'s' if pages > 1 else ''} today.")
    if ex:
        lines.append(f"You completed {ex} exercise{'s' if ex > 1 else ''}.")
    lines.append("Ready to explore next: more vocabulary and dialogue practice. 🇫🇷")
    return "\n\n".join(lines)
