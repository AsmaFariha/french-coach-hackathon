"""
Custom-UI entrypoint (UI_UPGRADE_PLAN.md Phase 2+).

Serves the React frontend (built to `frontend/dist/`) as static assets and
exposes the backend (db, nlp, llm, exercises, gamify) as a small JSON API
under `/api/...` — all attached to the same Gradio app object (`gr.Server`)
returned by `demo.launch(prevent_thread_lock=True)`, so the process stays a
Gradio-SDK app (see UI_UPGRADE_PLAN.md CONSTRAINT section).

- The Gradio Blocks tab at `/` is a tiny "what is this" page (kept so a
  Gradio app object exists to attach routes to).
- The React build is served at `/custom` (StaticFiles, html=True).
- `/api/...` routes implement frontend/API_CONTRACT.md.

Does NOT modify app.py. Runs on port 7861, separate from app.py (port 7860).
"""
import io
import json
import os

from dotenv import load_dotenv
from fastapi import UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
import gradio as gr

import nlp
import llm
import prompts
import notebook as nb
import exercises as ex
import gamify

load_dotenv()

USER_ID = "dev_user"
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "frontend", "dist")


# ── Helpers ─────────────────────────────────────────────────────────────────

def _pron_target_html(target: dict) -> str:
    return (
        f'<div style="border:1px solid #e0e0e0;border-radius:8px;padding:16px;background:#fff">'
        f'<div style="font-size:1.4rem;font-family:Georgia,serif;margin-bottom:8px">'
        f'🎯 <strong>{target.get("phrase","")}</strong></div>'
        f'<div style="color:#666;margin-bottom:6px">{target.get("translation","")}</div>'
        f'<div style="color:#888;font-size:0.85rem;font-style:italic">💡 {target.get("tip","")}</div>'
        f'</div>'
    )


def _pron_feedback_html(fb_data: dict) -> str:
    return (
        f'<div style="border-left:4px solid #2e7d32;padding:12px 16px;'
        f'background:#2e7d3211;border-radius:0 8px 8px 0">'
        f'<div style="font-weight:600;margin-bottom:6px">🌟 {fb_data.get("feedback","")}</div>'
        f'<div style="font-size:0.9rem;color:#555">Focus: {fb_data.get("focus","")}</div>'
        f'<div style="font-size:0.9rem;color:#555">Tip: {fb_data.get("tip","")}</div>'
        f'</div>'
    )


def _dialogue_feedback_html(fb_data: dict) -> str:
    feedback = fb_data.get("feedback", "")
    natural = fb_data.get("natural_version", "")
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


# A near-empty Blocks app — its only job is to give us a Gradio app object
# (gr.Server) to attach the custom routes onto, so the entrypoint stays Gradio.
with gr.Blocks(title="French Coach — Custom UI (dev)") as demo:
    gr.Markdown(
        "## French Coach — custom UI dev server\n\n"
        "The React frontend lives at **/custom** — this Blocks tab only "
        "exists so a Gradio app object (`gr.Server`) is available to mount "
        "it and the `/api/...` routes on."
    )
    gr.HTML('<a href="/custom/" target="_blank">Open the custom UI →</a>')


if __name__ == "__main__":
    app, local_url, share_url = demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("CUSTOM_UI_PORT", 7861)),
        prevent_thread_lock=True,
    )

    # ── Lessons ──────────────────────────────────────────────────────────────

    @app.get("/api/lessons")
    def api_list_lessons():
        pages = nb.list_pages(USER_ID)
        pages = [p for p in pages if p.get("page_type") != "resource"]
        return {"lessons": pages}

    @app.get("/api/lessons/{page_id}")
    def api_get_lesson(page_id: str):
        page = nb.get_page(page_id, USER_ID)
        if not page:
            raise HTTPException(status_code=404, detail="not found")
        ann = page.get("annotations") or {}
        if isinstance(ann, str):
            ann = json.loads(ann)
        return {"id": page["id"], "title": page["title"], "raw_text": page["raw_text"], "annotations": ann}

    @app.post("/api/lessons")
    async def api_save_lesson(payload: dict):
        text = (payload.get("text") or "").strip()
        if not text:
            raise HTTPException(status_code=400, detail="text is required")
        ann = payload.get("annotations") or {}
        page_id, title = nb.save_page(USER_ID, payload.get("text", ""), ann)
        gamify.add_points(USER_ID, "saved_lesson")
        return {"id": page_id, "title": title}

    @app.put("/api/lessons/{page_id}")
    async def api_update_lesson(page_id: str, payload: dict):
        text = (payload.get("text") or "").strip()
        if not text:
            raise HTTPException(status_code=400, detail="text is required")
        ann = payload.get("annotations") or {}
        title = nb.update_page(page_id, USER_ID, payload.get("text", ""), ann)
        return {"title": title}

    @app.patch("/api/lessons/{page_id}/title")
    async def api_rename_lesson(page_id: str, payload: dict):
        title = (payload.get("title") or "").strip()
        if not title:
            raise HTTPException(status_code=400, detail="title is required")
        new_title = nb.update_title(page_id, USER_ID, title)
        return {"title": new_title}

    @app.delete("/api/lessons/{page_id}")
    def api_delete_lesson(page_id: str):
        deleted = nb.delete_page(page_id, USER_ID)
        return {"deleted": deleted}

    # ── Resources ────────────────────────────────────────────────────────────

    @app.get("/api/resources")
    def api_resources():
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
                "links": [
                    {"url": l.get("url", ""), "label": l.get("label") or l.get("url", ""),
                     "domain": _domain(l.get("url", ""))}
                    for l in links
                ],
                "books": [
                    {"title": b.get("title", ""), "author": b.get("author", ""), "note": b.get("note", "")}
                    for b in books
                ],
            })
        return {"resources": out}

    # ── Annotation / word card ───────────────────────────────────────────────

    @app.post("/api/annotate")
    async def api_annotate(payload: dict):
        text = payload.get("text", "")
        colors_on = bool(payload.get("colors_on", True))
        ann = nlp.annotate(text)
        html = nlp.render_html(ann, colors_on)
        return {"html": html, "tokens": ann.get("tokens", []), "meanings": ann.get("meanings", {})}

    @app.post("/api/render")
    async def api_render(payload: dict):
        """Re-render cached annotations (no spaCy/LLM calls) — used when loading
        a saved lesson or toggling gender colors, so cached word-card meanings
        in `annotations.meanings` survive."""
        ann = payload.get("annotations") or {"tokens": [], "meanings": {}}
        colors_on = bool(payload.get("colors_on", True))
        return {"html": nlp.render_html(ann, colors_on)}

    @app.post("/api/word-card")
    async def api_word_card(payload: dict):
        text = payload.get("text", "")
        lemma = payload.get("lemma") or text
        pos = payload.get("pos", "")
        gender = payload.get("gender") or ""
        meanings = dict(payload.get("meanings") or {})

        cache_key = lemma or text
        if cache_key not in meanings:
            meanings[cache_key] = llm.get_word_meaning(text, lemma, pos, gender)
            try:
                gamify.add_points(USER_ID, "word_explored")
            except Exception:
                pass

        data = meanings[cache_key]
        return {
            "text": text, "lemma": lemma, "pos": pos, "gender": gender,
            "meaning": data.get("meaning", ""), "grammar": data.get("grammar", ""),
            "meanings": meanings,
        }

    # ── Chat ─────────────────────────────────────────────────────────────────

    @app.post("/api/chat")
    async def api_chat(payload: dict):
        message = (payload.get("message") or "").strip()
        if not message:
            raise HTTPException(status_code=400, detail="message is required")
        history = payload.get("history") or []
        lesson_text = payload.get("lesson_text") or ""

        system = prompts.CHAT_SYSTEM
        if lesson_text.strip():
            system += f"\n\nCurrent lesson context:\n{lesson_text[:500]}"

        messages = [{"role": "system", "content": system}]
        for item in history:
            if item.get("role") in ("user", "assistant") and item.get("content"):
                messages.append({"role": item["role"], "content": item["content"]})
        messages.append({"role": "user", "content": message})

        reply = llm.chat(messages, stream=False, max_tokens=600)
        return {"reply": reply}

    # ── Text exercise ────────────────────────────────────────────────────────

    @app.post("/api/exercises/text")
    async def api_exercise_text(payload: dict):
        lesson_text = payload.get("lesson_text") or ""
        exercise = ex.generate_text_exercise(lesson_text, USER_ID)
        return {"exercise": exercise, "html": ex.render_text_exercise(exercise)}

    @app.post("/api/exercises/text/check")
    async def api_exercise_text_check(payload: dict):
        exercise = payload.get("exercise") or {}
        answer = (payload.get("answer") or "").strip().lower()
        correct = answer == (exercise.get("answer", "") or "").strip().lower()
        gamify.add_points(USER_ID, "exercise_done")
        html = ex.render_exercise_feedback(correct, exercise.get("answer", ""), exercise.get("explanation", ""))
        return {"correct": correct, "html": html}

    # ── Dialogue ─────────────────────────────────────────────────────────────

    @app.post("/api/exercises/dialogue")
    async def api_exercise_dialogue(payload: dict):
        lesson_text = payload.get("lesson_text") or ""
        dialogue = ex.generate_dialogue(lesson_text, USER_ID)
        hint = ex.get_next_user_hint(dialogue, 0)
        transcript_html = ex.render_dialogue(dialogue, [])
        return {"dialogue": dialogue, "replies": [], "hint": f"Your turn: {hint}", "transcript_html": transcript_html}

    @app.post("/api/exercises/dialogue/reply")
    async def api_exercise_dialogue_reply(payload: dict):
        dialogue = payload.get("dialogue") or {}
        replies = list(payload.get("replies") or [])
        reply = (payload.get("reply") or "").strip()
        if not reply:
            raise HTTPException(status_code=400, detail="reply is required")

        hint = ex.get_next_user_hint(dialogue, len(replies))
        fb_data = ex.dialogue_feedback(reply, hint, dialogue.get("scene", ""), USER_ID)
        feedback_html = _dialogue_feedback_html(fb_data)

        replies.append(reply)
        transcript_html = ex.render_dialogue(dialogue, replies)

        next_hint = ex.get_next_user_hint(dialogue, len(replies))
        hint_text = f"Your turn: {next_hint}" if next_hint else "🎉 Dialogue complete! Great work!"

        return {"replies": replies, "transcript_html": transcript_html, "hint": hint_text, "feedback_html": feedback_html}

    # ── Visual exercise ──────────────────────────────────────────────────────

    @app.post("/api/exercises/visual")
    async def api_exercise_visual(image: UploadFile = File(...)):
        data = await image.read()
        try:
            pil_image = Image.open(io.BytesIO(data))
            pil_image.load()
        except Exception:
            raise HTTPException(status_code=400, detail="could not read image")
        result = ex.generate_visual_exercise(pil_image, USER_ID)
        gamify.add_points(USER_ID, "photo_exercise")
        return {"html": ex.render_visual_exercises(result)}

    # ── Pronunciation ────────────────────────────────────────────────────────

    @app.post("/api/exercises/pronunciation/target")
    async def api_pron_target(payload: dict):
        lesson_text = payload.get("lesson_text") or ""
        target = ex.generate_pronunciation_target(lesson_text)
        return {"target": target, "html": _pron_target_html(target)}

    @app.post("/api/exercises/pronunciation/check")
    async def api_pron_check(payload: dict):
        target = payload.get("target") or {}
        transcription = (payload.get("transcription") or "").strip()
        if not transcription:
            raise HTTPException(status_code=400, detail="transcription is required")
        fb_data = ex.get_pronunciation_feedback(target.get("phrase", ""), transcription)
        gamify.add_points(USER_ID, "pronunciation")
        return {"html": _pron_feedback_html(fb_data)}

    # ── Summary ──────────────────────────────────────────────────────────────

    @app.get("/api/summary")
    def api_summary():
        try:
            gamify.try_daily_open(USER_ID)
        except Exception:
            pass
        summary = gamify.get_daily_summary(USER_ID)
        total = gamify.get_total_points(USER_ID)
        return {"summary": summary, "total_points": total}

    # ── React build (served last so /api/* above takes precedence) ──────────

    if os.path.isdir(FRONTEND_DIST):
        app.mount("/custom", StaticFiles(directory=FRONTEND_DIST, html=True), name="custom-ui")
    else:
        @app.get("/custom", response_class=HTMLResponse)
        def custom_placeholder():
            return (
                "<h1>Frontend not built yet</h1>"
                "<p>Run <code>cd frontend && npm install && npm run build</code>, "
                "then restart this server.</p>"
            )

    demo.block_thread()
