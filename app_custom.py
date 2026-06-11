"""
Custom-UI entrypoint (UI_UPGRADE_PLAN.md Phase 2+). Phase 5: this is the
Gradio Space entrypoint (see root README.md front matter `app_file`).

Serves the React frontend (built to `frontend/dist/`) as static assets and
exposes the backend (db, nlp, llm, exercises, gamify) as a small JSON API
under `/api/...` — all attached to the same Gradio app object (`gr.Server`)
returned by `demo.launch(prevent_thread_lock=True)`, so the process stays a
Gradio-SDK app (see UI_UPGRADE_PLAN.md CONSTRAINT section).

- `/` serves the React build's index.html directly. Gradio's default Blocks
  "/" route (registered by demo.launch() below) is dropped at startup to make
  room for it; the Blocks object below exists only to give us a gr.Server app
  to attach routes to.
- The React build is ALSO served at `/custom` (StaticFiles, html=True), per
  frontend/README.md's dev workflow.
- `/api/...` routes implement frontend/API_CONTRACT.md.

Does NOT modify app.py, which remains the themed-Blocks fallback entrypoint
(see root README.md "Reverting" note). Defaults to the standard Gradio port
(7860); local Docker Compose overrides CUSTOM_UI_PORT=7861 so it can run
alongside app.py on 7860.
"""
import json
import os

from dotenv import load_dotenv
from fastapi import HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
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
        "## French Coach — custom UI\n\n"
        "This Blocks tab exists only so a Gradio app object (`gr.Server`) is "
        "available to mount the React build and the `/api/...` routes on. "
        "Since Phase 5, the React build is served at `/` (the Space "
        "entrypoint) — this tab itself isn't reachable."
    )
    gr.HTML('<a href="/custom/" target="_blank">Open the custom UI (dev URL) →</a>')


if __name__ == "__main__":
    app, local_url, share_url = demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("CUSTOM_UI_PORT", 7860)),
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

    # ── Coach Agent: mixed exercise set ─────────────────────────────────────

    @app.post("/api/exercises/coach")
    async def api_exercise_coach(payload: dict):
        lesson_text = payload.get("lesson_text") or ""
        page_id = payload.get("page_id")
        result = ex.generate_exercise_set(lesson_text, USER_ID, page_id)
        return result

    @app.post("/api/exercises/coach/check")
    async def api_exercise_coach_check(payload: dict):
        exercise = payload.get("exercise") or {}
        answer = payload.get("answer") or ""
        return ex.check_coach_exercise(exercise, answer, USER_ID)

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

    @app.post("/api/exercises/visual/sample")
    async def api_exercise_visual_sample(payload: dict):
        """Matched-image visual exercise (Day 4): no upload needed — pick a
        pre-generated image for this lesson's topic and build exercises from
        its description."""
        lesson_text = payload.get("lesson_text") or ""
        topic = nlp.detect_category(lesson_text) if lesson_text.strip() else "Daily Life"
        image = ex.pick_sample_image(topic, USER_ID)
        if not image:
            raise HTTPException(status_code=404, detail="no sample images available")
        result = ex.generate_visual_topic_exercise(image, lesson_text, USER_ID)
        gamify.add_points(USER_ID, "photo_exercise")
        return {
            "image_url": f"/custom/sample_images/{image['filename']}",
            "topic": topic,
            "html": ex.render_visual_exercises(result),
        }

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

    # ── React build, served at / (Space root, Phase 5) and /custom ──────────
    # `/` is the Space entrypoint: drop Gradio's default Blocks "/" route(s)
    # (registered by demo.launch() above) and serve the built index.html in
    # their place. That file's asset URLs are rooted at /custom/ (see
    # vite.config.js `base`), which the StaticFiles mount below continues to
    # serve, so no assets need duplicating. /custom/ is kept too, for the dev
    # workflow described in frontend/README.md.

    if os.path.isdir(FRONTEND_DIST):
        with open(os.path.join(FRONTEND_DIST, "index.html"), encoding="utf-8") as f:
            _index_html = f.read()

        app.router.routes = [r for r in app.router.routes if getattr(r, "path", None) != "/"]

        @app.get("/", response_class=HTMLResponse)
        @app.head("/", response_class=HTMLResponse)
        def custom_ui_root():
            return _index_html

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
