"""
Exercise generators for text, dialogue, visual, and pronunciation features.
All feedback uses encouraging language — see prompts.py for tone constraints.
"""
import json
import base64
import io
import logging
import os
from db import get_cursor
import gamify
import llm
import prompts

logger = logging.getLogger(__name__)

# ── Text exercise (Day 6) — kept for app.py's themed-Blocks fallback ──────────

def generate_text_exercise(lesson_text: str, user_id: str) -> dict:
    result = llm.chat_json(
        prompts.TEXT_EXERCISE_SYSTEM,
        f"Lesson text:\n{lesson_text[:800]}",
        fallback=_FALLBACK_EXERCISES["fill_blank"],
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

# ── Coach Agent: plan → generate → critique → revise (Day 3) ──────────────────

_SYLLABUS_PATH = os.path.join(os.path.dirname(__file__), "syllabus_full_a1_c2.json")
_syllabus_concepts: list[dict] | None = None

EXERCISE_TYPES = ["fill_blank", "multiple_choice", "error_detection", "reorder", "translation"]

# Used if the LLM is unreachable — still gives a real, varied 5-item set
# (degrade gracefully, per CLAUDE.md §1).
_FALLBACK_EXERCISES = {
    "fill_blank": {
        "type": "fill_blank", "instruction": "Fill in the blank:",
        "sentence_with_blank": "Le ___ dort sur la table.",
        "answer": "chat", "hint": "a small household animal (masculine noun)",
        "explanation": "Chat (masc.) = cat. Articles: le chat, un chat.",
    },
    "multiple_choice": {
        "type": "multiple_choice", "instruction": "Choose the correct answer:",
        "question": "Comment dit-on « I am » en français ?",
        "options": ["Je suis", "Tu es", "Il est", "Nous sommes"],
        "answer": "Je suis",
        "explanation": "« Je suis » = « I am » — first-person singular of être.",
    },
    "error_detection": {
        "type": "error_detection", "instruction": "Find and fix the mistake:",
        "sentence": "Elle est un étudiante.",
        "answer": "Elle est une étudiante.",
        "explanation": "« Étudiante » is feminine, so it takes « une », not « un ».",
    },
    "reorder": {
        "type": "reorder", "instruction": "Put the words in the correct order:",
        "words": ["je", "le", "matin", "café", "bois", "un"],
        "answer": "Je bois un café le matin.",
        "explanation": "Subject + verb + object + time expression is the typical French word order.",
    },
    "translation": {
        "type": "translation", "instruction": "Translate to French:",
        "prompt": "I would like a coffee, please.",
        "answer": "Je voudrais un café, s'il vous plaît.",
        "explanation": "« Je voudrais » (I would like) is a polite, common way to make a request.",
    },
}


def _load_a1_a2_concepts() -> list[dict]:
    """A1/A2 concepts from the CEFR syllabus — the Coach Agent's grounding menu."""
    global _syllabus_concepts
    if _syllabus_concepts is None:
        try:
            with open(_SYLLABUS_PATH, encoding="utf-8") as f:
                concepts = json.load(f)["concepts"]
            _syllabus_concepts = [c for c in concepts if c.get("cefr_level") in ("A1", "A2")]
        except Exception as e:
            logger.warning("_load_a1_a2_concepts failed: %s", e)
            _syllabus_concepts = []
    return _syllabus_concepts


def generate_exercise_set(lesson_text: str, user_id: str, page_id: str | None = None, topic: str = "") -> dict:
    """Coach Agent: PLAN -> GENERATE -> CRITIQUE -> REVISE -> RETURN.

    Returns {"concepts": [...], "exercises": [...]} — 5-7 mixed, self-checked
    exercises grounded in the lesson and the A1/A2 syllabus. `topic` is an
    optional learner-chosen focus; if blank, the agent picks from the lesson.
    """
    concepts_menu = _load_a1_a2_concepts()
    menu_ids = {c["id"] for c in concepts_menu}

    plan = llm.chat_json(
        prompts.COACH_PLAN_SYSTEM,
        prompts.coach_plan_user(lesson_text, concepts_menu, topic),
        fallback={"concepts": [], "plan": [{"type": t, "focus": "general practice from this lesson"} for t in EXERCISE_TYPES]},
    )

    chosen_concepts = [c for c in concepts_menu if c["id"] in (plan.get("concepts") or []) and c["id"] in menu_ids]

    items_plan = [
        spec for spec in (plan.get("plan") or [])
        if isinstance(spec, dict) and spec.get("type") in EXERCISE_TYPES
    ][:7]
    if not items_plan:
        items_plan = [{"type": t, "focus": "general practice from this lesson"} for t in EXERCISE_TYPES]

    exercises = [
        _generate_and_critique(lesson_text, spec["type"], spec.get("focus", "general practice from this lesson"), topic=topic)
        for spec in items_plan
    ]

    if chosen_concepts:
        _mark_concepts_covered(chosen_concepts)

    result = {"concepts": chosen_concepts, "exercises": exercises}
    _save_exercise(user_id, page_id, "coach_set", None, None, result)
    return result


def _generate_and_critique(lesson_text: str, ex_type: str, focus: str, max_attempts: int = 2, topic: str = "") -> dict:
    """GENERATE -> CRITIQUE -> REVISE, bounded to max_attempts generations."""
    revise_note = ""
    exercise = _FALLBACK_EXERCISES[ex_type]
    for _ in range(max_attempts):
        exercise = llm.chat_json(
            prompts.COACH_EXERCISE_SYSTEM,
            prompts.coach_exercise_user(lesson_text, ex_type, focus, revise_note, topic),
            fallback=_FALLBACK_EXERCISES[ex_type],
        )
        exercise.setdefault("type", ex_type)
        critique = llm.chat_json(
            prompts.COACH_CRITIQUE_SYSTEM,
            prompts.coach_critique_user(exercise),
            fallback={"valid": True, "issue": ""},
        )
        if critique.get("valid", True):
            break
        revise_note = critique.get("issue", "")
    return exercise


def _mark_concepts_covered(concepts: list[dict]) -> None:
    """UPSERT concepts as covered today, so the Summary tab can draw on them."""
    try:
        with get_cursor() as cur:
            for c in concepts:
                cur.execute(
                    """INSERT INTO concepts (id, name, cefr_level, family, covered_on)
                       VALUES (%s, %s, %s, %s, CURRENT_DATE)
                       ON CONFLICT (id) DO UPDATE SET covered_on = CURRENT_DATE""",
                    (c["id"], c["name"], c["cefr_level"], c["family"]),
                )
    except Exception as e:
        logger.warning("_mark_concepts_covered failed: %s", e)


def check_coach_exercise(exercise: dict, user_answer: str, user_id: str) -> dict:
    """Check one answer. Always awards participation points — never deducts."""
    ex_type = exercise.get("type", "fill_blank")
    correct_answer = (exercise.get("answer") or "").strip()
    user_answer = (user_answer or "").strip()

    if ex_type in ("fill_blank", "multiple_choice"):
        correct = user_answer.lower() == correct_answer.lower()
        feedback = "Exactly right!" if correct else exercise.get("explanation", "")
    else:
        graded = llm.chat_json(
            prompts.COACH_CHECK_SYSTEM,
            prompts.coach_check_user(exercise, user_answer),
            fallback={
                "correct": user_answer.lower() == correct_answer.lower(),
                "feedback": exercise.get("explanation", ""),
            },
        )
        correct = bool(graded.get("correct"))
        feedback = graded.get("feedback") or exercise.get("explanation", "")

    gamify.add_points(user_id, "exercise_done")
    return {"correct": correct, "feedback": feedback, "answer": correct_answer}

# ── Dialogue exercise (Day 7) ─────────────────────────────────────────────────

def generate_dialogue(lesson_text: str, user_id: str, topic: str = "") -> dict:
    result = llm.chat_json(
        prompts.DIALOGUE_SYSTEM,
        prompts.dialogue_user(lesson_text, topic),
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
        hint = ex.get("hint", "")
        hint_html = f'<div style="font-size:0.85rem;color:#888;font-style:italic;margin-bottom:6px">Hint: {hint}</div>' if hint else ""
        parts.append(
            f'<div style="border:1px solid #e0e0e0;border-radius:8px;padding:14px;'
            f'margin-bottom:10px;background:#fff">'
            f'<div style="font-size:0.8rem;color:#888;margin-bottom:4px">Exercise {i} — {ex.get("type","").title()}</div>'
            f'<div style="font-size:0.95rem;font-weight:600;margin-bottom:6px">{ex.get("instruction","")}</div>'
            f'<div style="font-family:Georgia,serif;font-size:1.1rem;margin-bottom:8px">{ex.get("content","")}</div>'
            f'{hint_html}'
            f'<details style="font-size:0.9rem">'
            f'<summary style="cursor:pointer;color:#4A90D9">Show answer</summary>'
            f'<div style="margin-top:6px"><strong>{ex.get("answer","")}</strong> — {ex.get("explanation","")}</div>'
            f'</details></div>'
        )
    return "".join(parts)

# ── Visual exercise from a matched sample image (Day 4) ───────────────────────

_SAMPLE_IMAGES_DIR = os.path.join(os.path.dirname(__file__), "frontend", "public", "sample_images")
_sample_images: list[dict] | None = None


def _load_sample_images() -> list[dict]:
    """Pre-generated images + hand-written descriptions (see generate_sample_images.py)."""
    global _sample_images
    if _sample_images is None:
        try:
            with open(os.path.join(_SAMPLE_IMAGES_DIR, "manifest.json"), encoding="utf-8") as f:
                _sample_images = json.load(f)["images"]
        except Exception as e:
            logger.warning("_load_sample_images failed: %s", e)
            _sample_images = []
    return _sample_images


def pick_sample_image(topic: str, user_id: str) -> dict | None:
    """Pick a sample image matching the lesson's topic that this user hasn't
    seen yet. Falls back to any unseen image, then to the least-recently-used
    one, so images don't repeat until the set is exhausted."""
    images = _load_sample_images()
    if not images:
        return None

    try:
        with get_cursor() as cur:
            cur.execute("SELECT image_id FROM user_image_usage WHERE user_id = %s", (user_id,))
            seen = {r["image_id"] for r in cur.fetchall()}
    except Exception:
        seen = set()

    for candidates in (
        [img for img in images if img["topic"] == topic and img["id"] not in seen],
        [img for img in images if img["id"] not in seen],
    ):
        if candidates:
            return candidates[0]

    # Everyone's seen everything — cycle back to the least-recently-used image.
    try:
        with get_cursor() as cur:
            cur.execute(
                """SELECT image_id, MAX(used_at) AS last_used FROM user_image_usage
                   WHERE user_id = %s GROUP BY image_id ORDER BY last_used ASC LIMIT 1""",
                (user_id,),
            )
            row = cur.fetchone()
            if row:
                by_id = {img["id"]: img for img in images}
                if row["image_id"] in by_id:
                    return by_id[row["image_id"]]
    except Exception:
        pass
    return images[0]


def _mark_image_used(user_id: str, image_id: str) -> None:
    try:
        with get_cursor() as cur:
            cur.execute(
                "INSERT INTO user_image_usage (user_id, image_id) VALUES (%s, %s)",
                (user_id, image_id),
            )
    except Exception as e:
        logger.warning("_mark_image_used failed: %s", e)


def generate_visual_topic_exercise(image: dict, lesson_text: str, user_id: str, topic: str = "") -> dict:
    """Build 5-6 exercises grounded in a pre-generated sample image's
    description (no vision call at request time)."""
    result = llm.chat_json(
        prompts.VISUAL_TOPIC_EXERCISE_SYSTEM,
        prompts.visual_topic_exercise_user(image["description"], lesson_text, topic),
        fallback={"image_summary": image["description"], "exercises": []},
        max_tokens=1536,
    )
    _mark_image_used(user_id, image["id"])
    _save_exercise(user_id, None, "visual", None, None, result)
    return result

# ── Pronunciation (Day 9) ─────────────────────────────────────────────────────

def generate_pronunciation_target(lesson_text: str, topic: str = "") -> dict:
    parts = []
    if topic.strip():
        parts.append(f"Focus topic requested by the learner: {topic.strip()}")
    if lesson_text.strip():
        parts.append(f"Lesson: {lesson_text[:300]}")
    context = "\n".join(parts) if parts else "A common A1 phrase"
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
