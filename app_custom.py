"""
Custom-UI entrypoint (HF Space: app_file in README.md, sdk: gradio).

Architecture:
  HF Spaces (sdk: gradio) imports this module and calls demo.launch() — the
  __main__ block never runs. We hook into every App.create_app() call via a
  module-level monkey-patch so our routes are injected regardless of who
  starts the server.

  HF's proxy strips the /gradio_api prefix before forwarding to our server:
    external /gradio_api/fc/*  → internal /fc/*   → our API handlers
    external /gradio_api/custom/* → internal /custom/* → StaticFiles (React)

  Route prefix /fc/ (French Coach) avoids Gradio's built-in
  POST /api/{api_name} wildcard. The React app uses BASE = '/gradio_api/fc'.

Import order for ZeroGPU (critical):
  1. spaces   — intercepts CUDA before anything else touches it
  2. @spaces.GPU defined HERE in app_file (ZeroGPU static scan only checks app_file)
  3. llm      — wired via register_gpu_fn() so it can call the GPU function
  4. gradio   — safe after spaces is set up
"""

# ── ZeroGPU setup — MUST be at the very top of app_file ─────────────────────
try:
    import spaces
except ImportError:
    class spaces:  # noqa: N801
        @staticmethod
        def GPU(fn):
            return fn

_zgpu_tok   = None
_zgpu_model = None


@spaces.GPU
def _zgpu_generate(messages_json: str, max_tokens: int) -> str:
    """ZeroGPU text generation — lazy model load on first GPU call."""
    import torch  # noqa: PLC0415
    from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: PLC0415
    import json as _json, os as _os  # noqa: PLC0415
    global _zgpu_tok, _zgpu_model
    hf_model = _os.environ.get("HF_MODEL", "openbmb/MiniCPM4-8B")
    if _zgpu_model is None:
        _zgpu_tok   = AutoTokenizer.from_pretrained(hf_model, trust_remote_code=True)
        _zgpu_model = AutoModelForCausalLM.from_pretrained(
            hf_model, trust_remote_code=True, torch_dtype=torch.bfloat16,
        ).eval()
    msgs   = _json.loads(messages_json)
    text   = _zgpu_tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    inputs = _zgpu_tok(text, return_tensors="pt").to(_zgpu_model.device)
    with torch.no_grad():
        out = _zgpu_model.generate(
            **inputs, max_new_tokens=min(max_tokens, 400),
            do_sample=True, temperature=0.7,
        )
    return _zgpu_tok.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)


# ── Other imports (after spaces) ─────────────────────────────────────────────
import llm
llm.register_gpu_fn(_zgpu_generate)

import json
import os

from dotenv import load_dotenv
from fastapi import HTTPException
from fastapi.staticfiles import StaticFiles
import gradio as gr
from gradio.routes import App as _GradioApp

import nlp
import prompts
import notebook as nb
import exercises as ex
import gamify

load_dotenv()

USER_ID       = "dev_user"
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "frontend", "dist")

_index_html = ""
_index_path = os.path.join(FRONTEND_DIST, "index.html")
if os.path.isfile(_index_path):
    with open(_index_path, encoding="utf-8") as _f:
        _index_html = _f.read()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _pron_target_html(target: dict) -> str:
    return (
        f'<div style="border:1px solid #e0e0e0;border-radius:8px;padding:16px;background:#fff">'
        f'<div style="font-size:1.4rem;font-family:Georgia,serif;margin-bottom:8px">'
        f'🎯 <strong>{target.get("phrase","")}</strong></div>'
        f'<div style="color:#666;margin-bottom:6px">{target.get("translation","")}</div>'
        f'<div style="color:#888;font-size:0.85rem">{target.get("tip","")}</div>'
        f'</div>'
    )


def _pron_feedback_html(fb_data: dict) -> str:
    score = fb_data.get("score", 0)
    color = "#2d8a4e" if score >= 80 else "#d97706" if score >= 50 else "#dc2626"
    return (
        f'<div style="border-left:4px solid {color};padding:10px 14px;'
        f'background:{color}1A;border-radius:0 8px 8px 0;font-size:0.92rem">'
        f'<strong>{score}/100</strong> — {fb_data.get("feedback","")}'
        + (f'<br><span style="color:{color};font-style:italic">💡 {fb_data.get("correction","")}</span>'
           if fb_data.get("correction") else "")
        + '</div>'
    )


def _dialogue_feedback_html(fb_data: dict) -> str:
    feedback = fb_data.get("feedback", "")
    natural  = fb_data.get("natural_version", "")
    return (
        f'<div style="border-left:4px solid #4A90D9;padding:10px 14px;'
        f'background:#4A90D91A;border-radius:0 8px 8px 0;font-size:0.92rem">'
        f'{feedback}'
        + (f'<br><span style="color:#4A90D9;font-style:italic">💡 {natural}</span>' if natural else "")
        + '</div>'
    )


def _domain(url: str) -> str:
    import urllib.parse
    try:
        netloc = urllib.parse.urlparse(url).netloc
        return netloc[4:] if netloc.startswith("www.") else netloc
    except ValueError:
        return url


# ── Route handlers (defined before monkey-patch is applied) ──────────────────

def _fc_probe():
    return {"ok": True, "index_html_len": len(_index_html)}

def _fc_list_lessons():
    pages = nb.list_pages(USER_ID)
    pages = [p for p in pages if p.get("page_type") != "resource"]
    return {"lessons": pages}

def _fc_get_lesson(page_id: str):
    page = nb.get_page(page_id, USER_ID)
    if not page:
        raise HTTPException(status_code=404, detail="not found")
    ann = page.get("annotations") or {}
    if isinstance(ann, str):
        ann = json.loads(ann)
    return {"id": page["id"], "title": page["title"],
            "raw_text": page["raw_text"], "annotations": ann}

async def _fc_save_lesson(payload: dict):
    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    ann = payload.get("annotations") or {}
    page_id, title = nb.save_page(USER_ID, payload.get("text", ""), ann)
    gamify.add_points(USER_ID, "saved_lesson")
    return {"id": page_id, "title": title}

async def _fc_update_lesson(page_id: str, payload: dict):
    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    ann = payload.get("annotations") or {}
    title = nb.update_page(page_id, USER_ID, payload.get("text", ""), ann)
    return {"title": title}

async def _fc_rename_lesson(page_id: str, payload: dict):
    title = (payload.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="title is required")
    new_title = nb.update_title(page_id, USER_ID, title)
    return {"title": new_title}

def _fc_delete_lesson(page_id: str):
    deleted = nb.delete_page(page_id, USER_ID)
    return {"deleted": deleted}

def _fc_resources():
    pages = nb.list_resources(USER_ID)
    out = []
    for page in pages:
        links = page.get("links") or []
        books = page.get("books") or []
        if not links and not books:
            continue
        out.append({
            "id": page["id"],
            "title": page.get("title") or "Resources",
            "links": [{"url": l.get("url", ""), "label": l.get("label") or l.get("url", ""),
                       "domain": _domain(l.get("url", ""))} for l in links],
            "books": [{"title": b.get("title", ""), "author": b.get("author", ""),
                       "note": b.get("note", "")} for b in books],
        })
    return {"resources": out}

async def _fc_annotate(payload: dict):
    text      = payload.get("text", "")
    colors_on = bool(payload.get("colors_on", True))
    ann       = nlp.annotate(text)
    html      = nlp.render_html(ann, colors_on)
    return {"html": html, "tokens": ann.get("tokens", []), "meanings": ann.get("meanings", {})}

async def _fc_render(payload: dict):
    ann       = payload.get("annotations") or {"tokens": [], "meanings": {}}
    colors_on = bool(payload.get("colors_on", True))
    return {"html": nlp.render_html(ann, colors_on)}

async def _fc_word_card(payload: dict):
    text     = payload.get("text", "")
    lemma    = payload.get("lemma") or text
    pos      = payload.get("pos", "")
    gender   = payload.get("gender") or ""
    meanings = dict(payload.get("meanings") or {})
    cache_key = lemma or text
    if cache_key not in meanings:
        meanings[cache_key] = llm.get_word_meaning(text, lemma, pos, gender)
        try:
            gamify.add_points(USER_ID, "word_explored")
        except Exception:
            pass
    data = meanings[cache_key]
    return {"text": text, "lemma": lemma, "pos": pos, "gender": gender,
            "meaning": data.get("meaning", ""), "grammar": data.get("grammar", ""),
            "meanings": meanings}

async def _fc_gender_check(payload: dict):
    word = (payload.get("word") or "").strip()
    if not word:
        raise HTTPException(status_code=400, detail="word is required")
    info  = nlp.word_info(word)
    extra = llm.get_gender_check(info["word"], info.get("pos") or "")
    return {**info, **extra}

async def _fc_translate(payload: dict):
    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    direction   = payload.get("direction") or "auto"
    lesson_text = payload.get("lesson_text") or ""
    return llm.translate_text(text, direction, lesson_text)

async def _fc_chat(payload: dict):
    message = (payload.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is required")
    history     = payload.get("history") or []
    lesson_text = payload.get("lesson_text") or ""
    system      = prompts.CHAT_SYSTEM
    if lesson_text.strip():
        system += f"\n\nCurrent lesson context:\n{lesson_text[:500]}"
    messages = [{"role": "system", "content": system}]
    for item in history:
        if item.get("role") in ("user", "assistant") and item.get("content"):
            messages.append({"role": item["role"], "content": item["content"]})
    messages.append({"role": "user", "content": message})
    reply = llm.chat(messages, stream=False, max_tokens=600)
    return {"reply": reply}

async def _fc_exercise_coach(payload: dict):
    lesson_text = payload.get("lesson_text") or ""
    page_id     = payload.get("page_id")
    topic       = (payload.get("topic") or "").strip()
    return ex.generate_exercise_set(lesson_text, USER_ID, page_id, topic)

async def _fc_exercise_coach_check(payload: dict):
    exercise = payload.get("exercise") or {}
    answer   = payload.get("answer") or ""
    return ex.check_coach_exercise(exercise, answer, USER_ID)

async def _fc_exercise_dialogue(payload: dict):
    lesson_text    = payload.get("lesson_text") or ""
    topic          = (payload.get("topic") or "").strip()
    dialogue       = ex.generate_dialogue(lesson_text, USER_ID, topic)
    hint           = ex.get_next_user_hint(dialogue, 0)
    transcript_html = ex.render_dialogue(dialogue, [])
    return {"dialogue": dialogue, "replies": [], "hint": f"Your turn: {hint}",
            "transcript_html": transcript_html}

async def _fc_exercise_dialogue_reply(payload: dict):
    dialogue = payload.get("dialogue") or {}
    replies  = list(payload.get("replies") or [])
    reply    = (payload.get("reply") or "").strip()
    if not reply:
        raise HTTPException(status_code=400, detail="reply is required")
    hint           = ex.get_next_user_hint(dialogue, len(replies))
    fb_data        = ex.dialogue_feedback(reply, hint, dialogue.get("scene", ""), USER_ID)
    feedback_html  = _dialogue_feedback_html(fb_data)
    replies.append(reply)
    transcript_html = ex.render_dialogue(dialogue, replies)
    next_hint      = ex.get_next_user_hint(dialogue, len(replies))
    hint_text      = f"Your turn: {next_hint}" if next_hint else "🎉 Dialogue complete! Great work!"
    return {"replies": replies, "transcript_html": transcript_html,
            "hint": hint_text, "feedback_html": feedback_html}

async def _fc_exercise_visual_sample(payload: dict):
    lesson_text = payload.get("lesson_text") or ""
    topic       = (payload.get("topic") or "").strip()
    image_topic = nlp.detect_category(topic) if topic else "General"
    if image_topic == "General":
        image_topic = nlp.detect_category(lesson_text) if lesson_text.strip() else "Daily Life"
    image = ex.pick_sample_image(image_topic, USER_ID)
    if not image:
        raise HTTPException(status_code=404, detail="no sample images available")
    result = ex.generate_visual_topic_exercise(image, lesson_text, USER_ID, topic)
    gamify.add_points(USER_ID, "photo_exercise")
    return {"image_url": f"/gradio_api/custom/sample_images/{image['filename']}", "topic": image_topic,
            "image_summary": result.get("image_summary", ""), "exercises": result.get("exercises", [])}

async def _fc_pron_target(payload: dict):
    lesson_text = payload.get("lesson_text") or ""
    topic       = (payload.get("topic") or "").strip()
    target      = ex.generate_pronunciation_target(lesson_text, topic)
    return {"target": target, "html": _pron_target_html(target)}

async def _fc_pron_check(payload: dict):
    target        = payload.get("target") or {}
    transcription = (payload.get("transcription") or "").strip()
    if not transcription:
        raise HTTPException(status_code=400, detail="transcription is required")
    fb_data = ex.get_pronunciation_feedback(target.get("phrase", ""), transcription)
    gamify.add_points(USER_ID, "pronunciation")
    return {"html": _pron_feedback_html(fb_data)}

def _fc_summary():
    try:
        gamify.try_daily_open(USER_ID)
    except Exception:
        pass
    summary     = gamify.get_daily_summary(USER_ID)
    total       = gamify.get_total_points(USER_ID)
    daily_stats = gamify.get_daily_stats(USER_ID)
    concepts    = gamify.get_concepts_progress()
    return {"summary": summary, "total_points": total,
            "daily_stats": daily_stats, "concepts": concepts}


# ── Monkey-patch App.create_app ───────────────────────────────────────────────
# Applied BEFORE the `with gr.Blocks()` block so it runs for every App created,
# including the one HF's runner uses when it calls demo.launch() after import.
# create_app is @staticmethod so we wrap it directly.

_orig_create_app = _GradioApp.create_app

def _patched_create_app(blocks, **kwargs):
    app = _orig_create_app(blocks, **kwargs)

    # Static files — React bundle served at /custom/*
    if os.path.isdir(FRONTEND_DIST):
        app.mount("/custom", StaticFiles(directory=FRONTEND_DIST, html=True), name="custom-ui")

    # API routes — /fc/* prefix avoids Gradio's POST /api/{api_name} wildcard
    app.add_api_route("/fc/probe",                          _fc_probe,                    methods=["GET"])
    app.add_api_route("/fc/lessons",                        _fc_list_lessons,             methods=["GET"])
    app.add_api_route("/fc/lessons/{page_id}",              _fc_get_lesson,               methods=["GET"])
    app.add_api_route("/fc/lessons",                        _fc_save_lesson,              methods=["POST"])
    app.add_api_route("/fc/lessons/{page_id}",              _fc_update_lesson,            methods=["PUT"])
    app.add_api_route("/fc/lessons/{page_id}/title",        _fc_rename_lesson,            methods=["PATCH"])
    app.add_api_route("/fc/lessons/{page_id}",              _fc_delete_lesson,            methods=["DELETE"])
    app.add_api_route("/fc/resources",                      _fc_resources,                methods=["GET"])
    app.add_api_route("/fc/annotate",                       _fc_annotate,                 methods=["POST"])
    app.add_api_route("/fc/render",                         _fc_render,                   methods=["POST"])
    app.add_api_route("/fc/word-card",                      _fc_word_card,                methods=["POST"])
    app.add_api_route("/fc/gender-check",                   _fc_gender_check,             methods=["POST"])
    app.add_api_route("/fc/translate",                      _fc_translate,                methods=["POST"])
    app.add_api_route("/fc/chat",                           _fc_chat,                     methods=["POST"])
    app.add_api_route("/fc/exercises/coach",                _fc_exercise_coach,           methods=["POST"])
    app.add_api_route("/fc/exercises/coach/check",          _fc_exercise_coach_check,     methods=["POST"])
    app.add_api_route("/fc/exercises/dialogue",             _fc_exercise_dialogue,        methods=["POST"])
    app.add_api_route("/fc/exercises/dialogue/reply",       _fc_exercise_dialogue_reply,  methods=["POST"])
    app.add_api_route("/fc/exercises/visual/sample",        _fc_exercise_visual_sample,   methods=["POST"])
    app.add_api_route("/fc/exercises/pronunciation/target", _fc_pron_target,              methods=["POST"])
    app.add_api_route("/fc/exercises/pronunciation/check",  _fc_pron_check,               methods=["POST"])
    app.add_api_route("/fc/summary",                        _fc_summary,                  methods=["GET"])

    return app

_GradioApp.create_app = staticmethod(_patched_create_app)


# ── Gradio demo ───────────────────────────────────────────────────────────────
# The iframe src uses the /gradio_api/ prefix because HF's proxy only forwards
# that prefix to our server (strips it before forwarding: /gradio_api/X → /X).

with gr.Blocks(title="French Coach") as demo:
    gr.HTML(
        '<iframe src="/gradio_api/custom/index.html" '
        'style="position:fixed;top:0;left:0;width:100%;height:100%;border:none;" '
        'allow="microphone;camera;autoplay;clipboard-write">'
        '</iframe>'
    )


# ── Entrypoint ────────────────────────────────────────────────────────────────
# HF Spaces imports this module (not __main__) and calls demo.launch().
# The monkey-patch above ensures our routes are in every App.create_app().
# The __main__ block is kept for local development: python app_custom.py

if __name__ == "__main__":
    demo.launch()
