# French Coach — Dev Log

A running record of what was built each day. Written for both technical and non-technical readers.
Each entry gets appended after a build session completes.

---

## Day 0 — 2026-06-06 — Infrastructure: getting the foundations in place

### What changed (plain English)

Before this session, the project was just a single test file with no real structure. Now there is a proper development environment: one command (`docker compose up`) spins up the app *and* a database together, and the database is already set up with the right tables to store your French lessons, exercises, and points. You won't lose any data if you restart your computer — it's saved to a named volume. The app opens at `http://localhost:7860`.

### What changed (technical)

- **`docker-compose.yml`** — two-service stack: `app` (Python/Gradio, built from Dockerfile) + `db` (Postgres 16). DB healthcheck gates app startup so the app never starts before Postgres is ready. Named volume `pgdata` persists data across container restarts.
- **`db/init.sql`** — full schema applied on first Postgres start:
  - `pages` — stores notebook pages (raw text + cached spaCy annotations as JSONB)
  - `concepts` — CEFR-tagged vocabulary/grammar topics
  - `exercises` — per-page exercises of any kind (text, dialogue, visual, pronunciation)
  - `points` — append-only participation ledger (`CHECK amount > 0` enforces no deductions)
  - `mistakes` — private table, defined but never written by the public Space
- **`requirements.txt`** — added `openai` (for OpenBMB API via OpenAI-compatible client) and `psycopg2-binary`
- **`.env` / `.env.example`** — all env vars documented: OpenBMB API keys, `LLM_BACKEND`, `POSTGRES_PASSWORD`, `DATABASE_URL`. `DATABASE_URL` in docker-compose overrides the `.env` value so the hostname is always `db` (the service name) inside Docker.
- **`syllabus.json`** — placeholder; needs real Notion A1/A2 export
- **`seed_texts/lesson_01_greetings.txt`** — sample lesson for cold-start / demo

---

## Day 1 — 2026-06-06 — Gender-colored editor with clickable word cards

### What changed (plain English)

The app now does something genuinely useful: paste any French text and it instantly colour-codes the nouns — **blue underline for masculine, rose underline for feminine**. Click any word and a card pops up on the right showing the gender, the base form (lemma), and what part of speech it is. The word is also spoken aloud in French the moment you click it (using your browser's built-in voice). There's a toggle to turn the colours on and off. This is the core "see gender at a glance" feature from the project plan.

### What changed (technical)

- **`app.py`** — full rewrite from smoke-test to Day 1 prototype:
  - `annotate(text)` — runs spaCy `fr_core_news_sm`, returns annotation dict matching the DB `annotations` JSONB schema: `{ "tokens": [{ idx, text, pos, gender, lemma, is_space, whitespace }] }`
  - `render_html(annotations, colors_on)` — converts annotation dict to `<span data-token data-gender …>` HTML; noun spans get coloured borders (hex with `1A` alpha for background tint)
  - `show_word_card(click_data)` — receives a JSON click payload, returns an HTML card with a `data-speak` button for TTS
  - `gr.State` holds annotation JSON between events so toggling colours doesn't re-run spaCy
  - `demo.load(...)` auto-annotates the sample text on page load
- **JS event delegation** — `PAGE_JS` passed to `launch(js=...)` runs once on page load and attaches a single listener to `document`. This survives `gr.HTML` re-renders (which would kill any listeners attached to the HTML component's own DOM). This is the gotcha called out in CLAUDE.md §12 — proved working here.
- **TTS** — word spoken immediately on token click via `SpeechSynthesisUtterance` (`lang: 'fr-FR'`); also triggered by the `data-speak` button in the word card. `speechSynthesis.cancel()` before each call prevents queuing.
- **Hidden Gradio textbox** (`elem_id="word-click-data"`) bridges JS → Python: JS updates the textarea value using the React/native setter trick (required to trigger Gradio's change event), then dispatches `input` event. Python `.change()` handler fires and updates the word card component.
- **Gotcha hit**: Gradio 6 moved `js=` from `Blocks(js=…)` to `launch(js=…)` — fixed after seeing the UserWarning in container logs.

---

## Day 1.5 — 2026-06-06 — Multi-user support with Hugging Face login

### What changed (plain English)

The app now supports multiple users — each person's notes and data are kept completely separate. On the Hugging Face Space (the public version), visitors will see a "Sign in with Hugging Face" button in the top-right corner; only after signing in can they use the app. When you're running it locally on your own computer, it skips the login step automatically and uses a developer account so you can keep working without friction. If someone tries to use the Space without logging in, they see a polite message asking them to sign in rather than seeing someone else's data.

### What changed (technical)

- **`db/init.sql`** — added `user_id TEXT NOT NULL` to `pages`, `exercises`, `points`, and `mistakes` tables. Added `(user_id, created_at DESC)` indexes on the three active tables for efficient per-user queries. Volume wiped and recreated since no real data existed yet (cleanest migration path).
- **`app.py`**:
  - `IS_SPACE = bool(os.environ.get("SPACE_ID"))` — HF sets this env var automatically on Spaces; False locally
  - `get_user_id(profile: gr.OAuthProfile | None) → str | None` — returns `profile.username` on Space (logged in), `None` on Space (logged out, blocks access), `"dev_user"` locally (bypasses auth)
  - `gr.LoginButton` / `gr.LogoutButton` rendered conditionally only when `IS_SPACE` is True — avoids broken OAuth clicks in local dev
  - All event handlers (`process_text`, `toggle_colors`, `show_word_card`) now accept `profile: gr.OAuthProfile | None`; Gradio auto-injects the current session's profile. Unauthenticated calls return a lock-screen prompt instead of content
  - `on_load(profile)` replaces the old `demo.load` call — checks auth, shows username in header, auto-annotates sample text for authenticated users
  - `user_display` Markdown component in header shows `👤 username` when logged in, `🛠 local dev` when running locally
- **Gotcha hit**: `gr.Markdown` doesn't accept `scale=` — must wrap in `gr.Column(scale=0)` to control header layout width

---

## Days 4–9 — 2026-06-06 — LLM word cards, notebook persistence, chat, exercises, gamification

### What changed (plain English)

The app went from a clever annotation demo to a full French learning companion in one session. Click any word and you'll now see its English meaning and a grammar tip fetched live from the AI — shown instantly from cache if you've clicked it before. You can save your lesson notes with one click and the AI gives the page a sensible title automatically; all your saved pages appear in a sidebar and survive a browser refresh. A chat panel lets you ask any French question in plain English and get a helpful, encouraging answer. The Exercises tab has four types of practice generated directly from whatever you're studying: fill-in-the-blank, spoken dialogue (type your lines, the app reads the agent's lines aloud), photo-based exercises (upload a café menu or street sign and get French exercises from it), and pronunciation practice (speak a phrase, the app transcribes it and gives gentle feedback). Every action earns points — they only ever go up — and the Summary tab shows an encouraging recap of the day's wins.

### What changed (technical)

**New modules (all in root):**
- **`nlp.py`** — spaCy helpers extracted from `app.py`: `annotate()`, `render_html()`, `_legend()`. Lazy-loads model on first call.
- **`llm.py`** — OpenBMB API clients (text + vision). Auto-detects served model name via `/v1/models`; falls back to env var `MINICPM_MODEL` / `MINICPM_VISION_MODEL`, then hardcoded name. `chat()` supports streaming via generator. `chat_json()` strips markdown code fences before parsing. `get_word_meaning()` and `generate_page_title()` are thin wrappers over `chat_json`.
- **`prompts.py`** — All LLM prompt templates in one place. Encouraging-tone constraint enforced here: feedback prompts explicitly ban the words *wrong, error, mistake, fail, weak*. Prompts for: word meaning, page title, text exercise, dialogue scene, dialogue feedback, visual exercise, daily summary, pronunciation target, pronunciation feedback.
- **`db.py`** — `get_cursor()` context manager. New connection per call (psycopg2 thread-safety). Commits on clean exit, rolls back on exception.
- **`models.py`** — `Page` and `Exercise` dataclasses mirroring DB schema.
- **`notebook.py`** — `save_page()` (LLM title → DB insert), `list_pages()`, `get_page()`, `update_annotations()`.
- **`exercises.py`** — `generate_text_exercise()`, `generate_dialogue()`, `dialogue_feedback()`, `generate_visual_exercise()` (PIL → base64 → vision LLM → text LLM), `generate_pronunciation_target()`, `get_pronunciation_feedback()`. All save to `exercises` table. HTML renderers co-located with generators.
- **`gamify.py`** — `try_daily_open()` (once-per-day guard), `add_points()`, `get_total_points()`, `get_daily_stats()` (5-column single-query), `get_daily_summary()` (LLM-generated with fallback). Point values: daily_open=5, saved_lesson=10, exercise_done=5, dialogue_turn=3, pronunciation=5, word_explored=1, photo_exercise=8.

**`app.py` (major rewrite):**
- 4-tab layout: Notebook | Chat | Exercises | Summary using `gr.Tabs`
- `user_id_state = gr.State(None)` set in `on_load` — all handlers use this instead of threading `profile` everywhere
- **Day 4 word card** — `show_word_card()` is now a generator: yields basic spaCy card immediately (< 1ms), then yields LLM-enriched card after API call. Meaning cached in `ann_state["meanings"][lemma]` so repeat clicks are instant. Points awarded on first click per word.
- **Day 5 notebook** — save/load/sidebar wired up; `pages_dropdown` populated on load and after save.
- **Day 6 chat** — `gr.Chatbot` with streaming via generator; lesson text passed as context in system prompt via `additional_inputs`.
- **Day 7 dialogue** — `dialogue_state` holds full JSON + replies list; each `send_dialogue_reply()` call advances the turn, fetches LLM feedback, and updates the transcript HTML.
- **Day 8 visual** — `gr.Image(type="pil")` → PIL Image passed to `exercises.generate_visual_exercise()`.
- **Day 8 gamification** — points awarded for every meaningful action; Summary tab triggers `get_daily_summary()`.
- **Day 9 pronunciation** — `speak_btn.click(fn=None, js=...)` runs Web Speech API entirely client-side (no Python); transcript lands in the `pronunciation-input` textbox via the same React-setter trick as the word-click bridge.
- **Gotcha hit**: `theme=` also moved to `launch()` in Gradio 6 (same as `js=`).
- **`requirements.txt`** — added `Pillow` explicitly.

---

## LLM Backend Pivot — 2026-06-06 — Switched from OpenBMB to HF Inference (local) + ZeroGPU (Space)

### What changed (plain English)

The free OpenBMB API we were using for the AI stopped accepting our key (returned "Unauthorized"). Rather than wait for it to come back, we switched to a more stable arrangement: when you're running the app locally, it now calls Hugging Face's hosted inference service using your HF token. When the app is deployed as a public Space, it will use ZeroGPU — a free GPU provided by Hugging Face that runs the model directly on the server. Both paths are handled by the same code; a single environment variable (`LLM_BACKEND`) controls which one runs. The working model for local dev is **Qwen/Qwen2.5-7B-Instruct**, which has an active HF Inference endpoint and gives sensible French coaching responses. Vision (photo exercises) still uses the OpenBMB vision endpoint as a fallback — MiniCPM-V isn't yet available on HF Inference.

Also fixed: the Chat Coach tab was broken — it was sending messages in the old Gradio tuple format (pairs of `[user, assistant]` strings) but Gradio 6.16 expects a flat list of `{"role": ..., "content": ...}` dicts. This was the error visible in the screenshot. Multi-turn conversation (context carried across messages) confirmed working after the fix.

### What changed (technical)

- **`llm.py`** (full rewrite) — three-backend router controlled by `LLM_BACKEND` env var:
  - `huggingface_inference` — `InferenceClient.chat_completion()` from `huggingface_hub >= 0.24`; supports streaming; lazy-init singleton. **Default for local dev.**
  - `zerogpu` — `@spaces.GPU` decorated function created at *module load time* (required by the ZeroGPU runtime). If `import spaces` fails (not on a Space), gracefully falls back to `openbmb`. **For Space deploy only.**
  - `openbmb` — original OpenBMB OpenAI-compatible client; kept as legacy fallback. Vision stays on this endpoint.
- **`.env`** — `LLM_BACKEND=huggingface_inference`, `HUGGINGFACE_MODEL=Qwen/Qwen2.5-7B-Instruct` (tested; confirmed working). OpenBMB keys kept for vision fallback.
- **`.env.example`** — documents all three backends and why ZeroGPU is Space-only.
- **`requirements.txt`** — added `huggingface_hub>=0.24` (minimum for `InferenceClient.chat_completion`).
- **`requirements-space.txt`** (new file) — `transformers>=4.40`, `accelerate>=0.30`, `torch>=2.2`; only installed on the Space (would bloat local image significantly).
- **`app.py`** — fixed `chat_fn`: history is now built/yielded in Gradio 6 messages format (`{"role": ..., "content": ...}` dicts). History iteration uses `isinstance(item, dict)` to handle both formats gracefully. `history[-1]["content"] += chunk` replaces `history[-1][1] += chunk`.
- **Gotcha hit**: `openbmb/MiniCPM4.1-8B-Instruct` doesn't exist on HF Hub under that ID. `openbmb/MiniCPM4-8B` exists but has no enabled inference provider. `Qwen/Qwen2.5-7B-Instruct` confirmed working — chat, streaming, and multi-turn all verified inside the Docker container.

---

## Sprint Day 1 — 2026-06-09 — Smart Lesson Browser with Auto-Category Detection

### What changed (plain English)

The sidebar on the Notebook tab is completely new. Instead of a plain dropdown list, it now shows all 40 of your saved lessons in two collapsible sections: **By Date** (newest first) and **By Topic** (auto-detected). Hover over any lesson and a tooltip pops up with the first 100 characters as a preview. Type in the search box to instantly filter by title — no page reload. Click any lesson in either section to load it straight into the editor. The app automatically guesses the topic (Grammar, Food & Dining, Greetings, Weather, etc.) by scanning the first 300 characters of each lesson for French vocabulary patterns; existing lessons got 11 distinct categories assigned on load.

### What changed (technical)

- **`db/init.sql`** — added `metadata JSONB DEFAULT '{}'` column to `pages` table; added GIN index on metadata. Migration applied live via `ALTER TABLE pages ADD COLUMN IF NOT EXISTS metadata JSONB`.
- **`nlp.py`** — two new functions:
  - `detect_category(text)` — keyword scoring over 13 topic buckets (Greetings, Numbers, Grammar, Food & Dining, Transportation, Family, Time & Calendar, Shopping, Weather, Daily Life, Health, Places & Directions, Hobbies & Leisure). spaCy NER gives a +1 bonus to LOC-matching categories *only if they already have keyword matches* — NER reinforces, never creates. This prevents `LOC` entities from hijacking every lesson that mentions a city name.
  - `get_lesson_categories(pages)` — groups a list of page dicts by detected category; returns an alphabetically sorted `dict[category → [pages]]`.
- **`notebook.py`** — `list_pages()` now queries `LEFT(raw_text, 300) AS snippet` + `metadata->>'category'` in a single query. If stored category is blank (all pre-existing pages), it falls back to `detect_category(snippet)`. `save_page()` now writes detected category into `metadata` at insert time so future queries are instant.
- **`app.py`** — major sidebar refactor:
  - `_safe_attr(s)` — HTML attribute escaper (handles `"`, `'`, `&`, newlines).
  - `_render_sidebar_html(user_id)` — builds the full collapsible sidebar HTML: search input, By Date `<details open>`, By Topic `<details>` (collapsed by default), hover tooltip div. Each lesson item is a `<div class="fc-lesson-item" data-page-id="..." data-preview="...">` card.
  - Removed `_page_choices()` and all `gr.Dropdown(choices=...)` returns from handlers. Every handler that previously returned a Dropdown update now returns `_render_sidebar_html(user_id)` instead.
  - Sidebar UI: `pages_dropdown` (Dropdown) → `pages_sidebar_html` (HTML) + `sidebar_page_click` (hidden Textbox). The hidden textbox receives a page UUID from JS and triggers `load_page_handler`.
  - Event wiring: `pages_dropdown.change` → `sidebar_page_click.change`; `refresh_pages_btn` → `refresh_sidebar_btn`.
  - `PAGE_JS` extended: `window.fcSidebarSearch(q)` filters `.fc-lesson-item` divs client-side; mouseover/mousemove/mouseout handlers position the preview tooltip; click on `.fc-lesson-item` highlights it, hides tooltip, and writes page UUID to the hidden Gradio textbox using the React-setter trick.
- **Gotcha hit**: spaCy NER assigns `LOC` to many common French nouns (any proper noun can be detected as location). Giving unconditional +2 bonus caused 23/40 lessons to land in "Places & Directions". Fix: NER only reinforces (`+1`) categories that already have keyword matches. Result: 40 lessons spread across 11 categories.

---

## Sprint Day 2 — 2026-06-09 — Curator pass, Resources tab, real lesson dates, editable titles

### What changed (plain English)

The notebook now tells the difference between a class lesson and a "resource" page (your book list, online resource links, listening log) — resource pages are pulled out of the lecture sidebar and shown in a brand-new **📚 Resources** tab as nice link cards (with site icons) and a book list, instead of cluttering your lessons. Every saved page now also gets a friendlier auto-generated title and a one-line summary, and you can rename any page yourself with the new title field + "✏️ Rename" button above the editor. The 20 imported "Class 1.1" … "Class A2 U2 L2" lessons now have real, spaced-out dates running from April 28 through June 5, 2026, so they sort correctly in the "By Date" view.

### What changed (technical)

- **`prompts.py`** — replaced the old `PAGE_TITLE_SYSTEM` (title-only) with `CURATOR_SYSTEM`: a single prompt that classifies a page as `"lesson"` or `"resource"` and returns `{title, summary, page_type, links[], books[]}` in one JSON response. Rules enforce Title Case titles, empty `links`/`books` for lessons, real URLs only, and `""` (never `"N/A"`) for unknown book authors.
- **`curator.py`** (new) — `curate_page(raw_text)` calls `llm.chat_json(CURATOR_SYSTEM, ...)`, with a text-derived fallback (`_fallback`) if the LLM is unavailable. Sanitizes/truncates all fields (title ≤80, link label ≤120, book title ≤200, etc.) and validates `page_type`.
- **`notebook.py`**:
  - `save_page()` now calls `curator.curate_page()` instead of the old `llm.generate_page_title()`; stores `summary`, `page_type`, `links`, `books` in `metadata` alongside `category`.
  - `list_pages()` also returns `page_type` (defaults to `"lesson"` for old rows).
  - New `list_resources(user_id)` — returns resource-type pages with their `links`/`books` for the Resources tab.
  - New `update_title(page_id, user_id, title)` — lets the user override the auto-generated title.
- **`llm.py`** — removed the now-unused `generate_page_title()`.
- **`app.py`**:
  - New `_safe_html()` (escapes `&<>` for text content, vs. `_safe_attr()` for attributes) and `_domain(url)` helpers.
  - `_render_sidebar_html()` filters out `page_type == "resource"` pages — they no longer appear in the lecture browser.
  - New `_render_resources_html(user_id)` renders a `.fc-resources` block: one `.fc-resource-section` per resource page, each with a `.fc-link-grid` of `.fc-link-card`s (Google favicon + label + domain, opens in a new tab) and/or a `.fc-book-list` of `.fc-book-row`s (📖 title + author · note). New CSS added for all of these.
  - New **📚 Resources** tab (between Notebook and Chat Coach) with a refresh button wired to `_render_resources_html`.
  - Notebook tab: new `title_input` textbox + `rename_btn` (hidden until a page is loaded/saved) above the editor, wired via new `rename_page_handler`. `save_page_handler`, `load_page_handler`, `delete_page_handler`, `sidebar_click_handler` all updated to populate/clear the title field and toggle the rename button — required careful attention to keep return-tuple order in sync with each `outputs=[...]` list.
- **`backfill_class_dates.py`** (new, one-time, run from host) — assigns the 20 "Class N M" / "Class A2..." lessons consecutive dates starting April 28, 2026, every 2 days, in their natural curriculum order (1.1→1.5, 2.1→2.7, A2 1-3, A2 U1 L4-6, A2 U2 L1-2), ending June 5, 2026.
- **`backfill_curator.py`** (new, one-time, run inside the container) — re-runs the curator pass over all 36 existing pages so old lessons get the new friendly titles/summaries/page_type without the user re-saving anything. Result: 33 pages classified `"lesson"`, 3 classified `"resource"` ("Online Resource", "Book Recommendations", "Listening Log").
- **Gotcha hit**: new `.py` files aren't visible inside the app container until `docker compose up -d --build` (no volume mount) — hit this for both `curator.py` and `backfill_curator.py`.
- **Gotcha hit**: first curator pass on "Book Recommendations" produced a lowercase title and `"author": "N/A"` for a book with no listed author. Fixed by tightening `CURATOR_SYSTEM`'s title/author rules; full 36-page backfill confirms `author: ""` instead of `"N/A"`.

---
