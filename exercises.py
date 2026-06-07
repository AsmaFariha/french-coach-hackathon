"""
Exercise generators for text, dialogue, visual, and pronunciation features.
All feedback uses encouraging language — see prompts.py for tone constraints.
"""
import json
import base64
import io
import logging
from db import get_cursor
import llm
import prompts

logger = logging.getLogger(__name__)

# ── Text exercise (Day 6) ─────────────────────────────────────────────────────

def generate_text_exercise(lesson_text: str, user_id: str) -> dict:
    result = llm.chat_json(
        prompts.TEXT_EXERCISE_SYSTEM,
        f"Lesson text:\n{lesson_text[:800]}",
        fallback={
            "instruction": "Fill in the blank:",
            "sentence_with_blank": "Le ___ dort sur la table.",
            "answer": "chat",
            "hint": "a small household animal (masculine noun)",
            "explanation": "Chat (masc.) = cat. Articles: le chat, un chat.",
        },
    )
    _save_exercise(user_id, None, "text", result.get("sentence_with_blank"), result.get("answer"), result)
    return result


def render_text_exercise(ex: dict) -> str:
    if not ex:
        return ""
    return (
        f'<div style="border:1px solid #e0e0e0;border-radius:8px;padding:18px;background:#fff">'
        f'<p style="font-size:0.9rem;color:#888;margin:0 0 6px">{ex.get("instruction","")}</p>'
        f'<p style="font-size:1.2rem;font-family:Georgia,serif;margin:0 0 12px">'
        f'{ex.get("sentence_with_blank","")}</p>'
        f'<p style="font-size:0.85rem;color:#777;font-style:italic">Hint: {ex.get("hint","")}</p>'
        f'</div>'
    )


def render_exercise_feedback(correct: bool, answer: str, explanation: str) -> str:
    color = "#2e7d32" if correct else "#1565c0"
    icon  = "✅" if correct else "💡"
    label = "Exactly right!" if correct else f"The answer is: <strong>{answer}</strong>"
    return (
        f'<div style="border-left:4px solid {color};padding:12px 16px;'
        f'background:{color}11;border-radius:0 8px 8px 0">'
        f'<div style="font-weight:600;color:{color};margin-bottom:6px">{icon} {label}</div>'
        f'<div style="font-size:0.92rem">{explanation}</div>'
        f'</div>'
    )

# ── Dialogue exercise (Day 7) ─────────────────────────────────────────────────

def generate_dialogue(lesson_text: str, user_id: str) -> dict:
    result = llm.chat_json(
        prompts.DIALOGUE_SYSTEM,
        f"Lesson text:\n{lesson_text[:600]}",
        fallback={
            "scene": "At a café in Montréal",
            "agent_role": "Serveur",
            "user_role": "Client",
            "turns": [
                {"speaker": "agent", "text": "Bonjour! Qu'est-ce que vous désirez?",
                 "translation": "Hello! What would you like?"},
                {"speaker": "user", "hint": "Order a coffee"},
                {"speaker": "agent", "text": "Très bien! Un café pour vous.",
                 "translation": "Very well! A coffee for you."},
                {"speaker": "user", "hint": "Say thank you"},
            ],
        },
    )
    _save_exercise(user_id, None, "dialogue", None, None, result)
    return result


def render_dialogue(dialogue: dict, completed_replies: list[str]) -> str:
    """Render all turns completed so far as a chat-style HTML transcript."""
    if not dialogue:
        return ""
    scene       = dialogue.get("scene", "")
    agent_role  = dialogue.get("agent_role", "Agent")
    user_role   = dialogue.get("user_role", "You")
    turns       = dialogue.get("turns", [])
    reply_idx   = 0
    parts       = [
        f'<div style="font-size:0.85rem;color:#888;margin-bottom:12px;font-style:italic">📍 {scene}</div>'
    ]
    for turn in turns:
        if turn["speaker"] == "agent":
            parts.append(
                f'<div style="margin-bottom:10px">'
                f'<span style="font-size:0.8rem;color:#888">{agent_role}</span><br>'
                f'<span style="font-size:1.1rem;font-family:Georgia,serif">{turn["text"]}</span>'
                f'<span style="font-size:0.8rem;color:#aaa;margin-left:8px">'
                f'({turn.get("translation","")})</span>'
                f'</div>'
            )
        else:  # user turn
            if reply_idx < len(completed_replies):
                reply = completed_replies[reply_idx]
                parts.append(
                    f'<div style="margin-bottom:10px;text-align:right">'
                    f'<span style="font-size:0.8rem;color:#888">{user_role}</span><br>'
                    f'<span style="background:#4A90D91A;border:1px solid #4A90D9;'
                    f'border-radius:8px;padding:4px 10px;font-size:1rem">{reply}</span>'
                    f'</div>'
                )
                reply_idx += 1
    return f'<div style="padding:12px;border:1px solid #e0e0e0;border-radius:8px;background:#fafafa">{"".join(parts)}</div>'


def get_next_user_hint(dialogue: dict, replies_count: int) -> str:
    """Return the hint for the next user turn."""
    user_turns = [t for t in dialogue.get("turns", []) if t["speaker"] == "user"]
    if replies_count < len(user_turns):
        return user_turns[replies_count].get("hint", "Respond naturally")
    return ""


def dialogue_feedback(user_reply: str, hint: str, scene: str, user_id: str) -> dict:
    result = llm.chat_json(
        prompts.DIALOGUE_FEEDBACK_SYSTEM,
        prompts.dialogue_feedback_user(user_reply, hint, scene),
        fallback={
            "feedback": f"Bien essayé! A natural way to say this: try using '{hint}'.",
            "natural_version": hint,
        },
    )
    _save_points_for_dialogue(user_id)
    return result


def _save_points_for_dialogue(user_id: str):
    try:
        from gamify import add_points
        add_points(user_id, "dialogue_turn")
    except Exception:
        pass

# ── Visual exercise (Day 8) ───────────────────────────────────────────────────

def generate_visual_exercise(pil_image, user_id: str) -> dict:
    """Upload image → vision LLM describes → text LLM builds exercises."""
    import io, base64
    buf = io.BytesIO()
    pil_image.save(buf, format="JPEG", quality=85)
    image_b64 = base64.b64encode(buf.getvalue()).decode()

    description = llm.vision_chat(image_b64, prompts.VISUAL_DESCRIBE_PROMPT)
    if description.startswith("⚠"):
        return {"error": description, "exercises": []}

    result = llm.chat_json(
        prompts.VISUAL_EXERCISE_SYSTEM,
        f"Image content:\n{description}",
        fallback={"image_summary": description, "exercises": []},
    )
    _save_exercise(user_id, None, "visual", None, None, result)
    return result


def render_visual_exercises(result: dict) -> str:
    if "error" in result:
        return f'<div style="color:#c62828;padding:12px">{result["error"]}</div>'
    exercises = result.get("exercises", [])
    summary   = result.get("image_summary", "")
    if not exercises:
        return '<div style="color:#888;padding:12px">No exercises generated.</div>'

    parts = [f'<p style="color:#666;font-size:0.9rem;font-style:italic">📷 {summary}</p>']
    for i, ex in enumerate(exercises, 1):
        parts.append(
            f'<div style="border:1px solid #e0e0e0;border-radius:8px;padding:14px;'
            f'margin-bottom:10px;background:#fff">'
            f'<div style="font-size:0.8rem;color:#888;margin-bottom:4px">Exercise {i} — {ex.get("type","").title()}</div>'
            f'<div style="font-size:0.95rem;font-weight:600;margin-bottom:6px">{ex.get("instruction","")}</div>'
            f'<div style="font-family:Georgia,serif;font-size:1.1rem;margin-bottom:8px">{ex.get("content","")}</div>'
            f'<details style="font-size:0.9rem">'
            f'<summary style="cursor:pointer;color:#4A90D9">Show answer</summary>'
            f'<div style="margin-top:6px"><strong>{ex.get("answer","")}</strong> — {ex.get("explanation","")}</div>'
            f'</details></div>'
        )
    return "".join(parts)

# ── Pronunciation (Day 9) ─────────────────────────────────────────────────────

def generate_pronunciation_target(lesson_text: str) -> dict:
    context = f"Lesson: {lesson_text[:300]}" if lesson_text.strip() else "A common A1 phrase"
    return llm.chat_json(
        prompts.PRONUNCIATION_TARGET_SYSTEM,
        context,
        fallback={
            "phrase": "Bonjour, je m'appelle Marie.",
            "translation": "Hello, my name is Marie.",
            "tip": "The French 'r' is pronounced at the back of the throat.",
        },
    )


def get_pronunciation_feedback(target: str, transcription: str) -> dict:
    return llm.chat_json(
        prompts.PRONUNCIATION_FEEDBACK_SYSTEM,
        prompts.pronunciation_feedback_user(target, transcription),
        fallback={
            "feedback": "Excellent effort — every attempt builds your pronunciation muscle memory!",
            "focus": "Try to match the rhythm of the phrase.",
            "tip": "Read slowly first, then speed up gradually.",
        },
    )

# ── Shared DB helper ──────────────────────────────────────────────────────────

def _save_exercise(user_id, page_id, kind, prompt_text, answer, content):
    try:
        with get_cursor() as cur:
            cur.execute(
                """INSERT INTO exercises (user_id, page_id, kind, prompt, model_answer, content)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (user_id, page_id, kind, prompt_text, answer, json.dumps(content)),
            )
    except Exception as e:
        logger.warning("_save_exercise failed: %s", e)
