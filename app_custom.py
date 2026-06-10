"""
Phase 1 — smallest possible proof that a hand-written custom frontend can be
served from a Gradio app object (so the Space entrypoint stays Gradio/gr.Server,
keeping hackathon eligibility) instead of Gradio's built-in Blocks components.

How it works:
- `demo.launch(prevent_thread_lock=True)` starts the Gradio server and returns
  the underlying `gr.Server` (a FastAPI app) as `app`.
- We attach two plain routes directly to that `app`:
    GET  /custom       -> hand-written HTML/CSS/JS page (no Gradio components)
    POST /api/exercise -> calls the existing exercises.generate_text_exercise()
                           backend function, unchanged, and returns JSON
- `demo.block_thread()` keeps the process alive (same as a normal launch()).

Runs on port 7861, separate from app.py (port 7860) — both can run side by side.
Does NOT modify app.py.
"""
import os
from dotenv import load_dotenv
from fastapi.responses import HTMLResponse
import gradio as gr

import exercises as ex

load_dotenv()

USER_ID = "dev_user"

SAMPLE_LESSON = (
    "Le petit chat noir dort sur la grande table. "
    "La femme mange une pomme délicieuse avec son ami. "
    "Le livre est ouvert sur le bureau."
)

CUSTOM_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>French Coach — Custom UI proof</title>
<style>
  body { font-family: 'Poppins', system-ui, sans-serif; background: #FDFAF3; color: #111;
         max-width: 640px; margin: 40px auto; padding: 0 20px; }
  h1 { color: #002395; }
  button { background: #002395; color: #fff; border: none; border-radius: 8px;
           padding: 10px 18px; font-size: 1rem; cursor: pointer; }
  button:hover { background: #001b73; }
  button:disabled { background: #94aaed; cursor: default; }
  .card { border: 1px solid #eee; border-radius: 12px; padding: 16px 20px; margin-top: 20px;
          background: #fff; box-shadow: 0 1px 4px rgba(0,35,149,0.08); }
  .hint { color: #888; font-style: italic; font-size: 0.9rem; margin: 0 0 6px; }
  .sentence { font-size: 1.2rem; margin: 0 0 10px; }
</style>
</head>
<body>
  <h1>🇫🇷 French Coach — Custom UI proof</h1>
  <p>This page is plain HTML/CSS/JS — no Gradio components — served by the same
     Gradio app object (<code>gr.Server</code>) on port 7861. Click the button to
     call the real backend (an LLM-generated exercise from a sample lesson).</p>
  <button id="go">Generate exercise from backend</button>
  <div id="result"></div>
<script>
document.getElementById('go').addEventListener('click', async (e) => {
  const btn = e.target;
  const resultEl = document.getElementById('result');
  btn.disabled = true;
  resultEl.innerHTML = '<p class="hint">Calling backend…</p>';
  try {
    const resp = await fetch('/api/exercise', { method: 'POST' });
    const data = await resp.json();
    resultEl.innerHTML = `
      <div class="card">
        <p class="hint">${data.instruction || ''}</p>
        <p class="sentence">${data.sentence_with_blank || ''}</p>
        <p class="hint">Hint: ${data.hint || ''}</p>
      </div>`;
  } catch (err) {
    resultEl.innerHTML = `<p class="hint">⚠ ${err}</p>`;
  } finally {
    btn.disabled = false;
  }
});
</script>
</body>
</html>"""


# A near-empty Blocks app — its only job is to give us a Gradio app object
# (gr.Server) to attach the custom routes onto, so the entrypoint stays Gradio.
with gr.Blocks(title="French Coach — Custom UI (dev)") as demo:
    gr.Markdown(
        "## French Coach — custom UI dev server (Phase 1)\n\n"
        "The hand-built frontend lives at **/custom** — this Blocks tab only "
        "exists so a Gradio app object (`gr.Server`) is available to mount it on."
    )
    gr.HTML('<a href="/custom" target="_blank">Open the custom page →</a>')


if __name__ == "__main__":
    app, local_url, share_url = demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("CUSTOM_UI_PORT", 7861)),
        prevent_thread_lock=True,
    )

    @app.get("/custom", response_class=HTMLResponse)
    def custom_page():
        return CUSTOM_PAGE

    @app.post("/api/exercise")
    def api_exercise():
        """Calls the unchanged exercises backend and returns the result as JSON."""
        return ex.generate_text_exercise(SAMPLE_LESSON, USER_ID)

    demo.block_thread()
