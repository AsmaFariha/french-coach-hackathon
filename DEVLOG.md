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

## Sprint Day 3 — 2026-06-10 — Coach Agent generates self-checked mixed exercises

### What changed (plain English)

The Exercises tab has a new **🧠 Coach** practice set. Press "Generate" and the coach reads your current lesson, picks a balanced mix of 5–7 exercises (fill-in-the-blank, multiple choice, find-the-change, put-the-words-in-order, and translation), and walks you through them one at a time. Every answer gets warm, encouraging feedback right away — even when an answer isn't quite right, you still earn points and get a gentle tip toward the model answer. Behind the scenes, the coach also quietly notes which grammar topics your lesson covers, so the daily summary can name them as strengths and suggest what to try next.

### What changed (technical)

- **`prompts.py`** — added the Coach Agent's prompt set: `COACH_PLAN_SYSTEM`/`coach_plan_user` (identify 1-4 syllabus concept IDs + plan 5-7 items mixing the 5 exercise types), `COACH_EXERCISE_SYSTEM`/`coach_exercise_user` (per-type JSON shapes, with a `revise_note` hook for retries), `COACH_CRITIQUE_SYSTEM`/`coach_critique_user` (reviewer pass: correctness, single unambiguous answer, MC distractors, reorder word-set match, A1-A2 level), and `COACH_CHECK_SYSTEM`/`coach_check_user` (lenient grading for free-text types — accepts spelling/accent variation, never uses shaming language). Also restored `TEXT_EXERCISE_SYSTEM` (still used by `app.py`'s themed-Blocks fallback) and extended `DAILY_SUMMARY_SYSTEM`/`daily_summary_user` to weave in covered/next concepts.
- **`exercises.py`** — new Coach Agent section: `generate_exercise_set()` runs PLAN → GENERATE → CRITIQUE → REVISE → RETURN; `_generate_and_critique()` bounds each item to 2 generation attempts, feeding the critique's `issue` back as a revise hint if the first attempt fails review; `_FALLBACK_EXERCISES` gives one real exercise per type if the LLM is unreachable; `_load_a1_a2_concepts()` loads the A1/A2 slice of `syllabus_full_a1_c2.json` as the grounding menu; `_mark_concepts_covered()` upserts identified concepts into `concepts` with `covered_on = today`; `check_coach_exercise()` grades fill_blank/multiple_choice by exact match and the other three types via the lenient LLM check, always awarding `exercise_done` points. Also restored `generate_text_exercise()`/`render_text_exercise()`/`render_exercise_feedback()` (still called by `app.py`).
- **`gamify.py`** — new `get_concepts_progress()` reads covered concept IDs from the DB and returns `{covered, next}` against the A1/A2 syllabus order; `get_daily_summary()` and the `_fallback()` text now both use this for "strengths + next focus".
- **`app_custom.py`** — new `POST /api/exercises/coach` and `POST /api/exercises/coach/check`, replacing the old single-item `/api/exercises/text` endpoints.
- **`frontend/`** — `api.js` swaps `generateTextExercise`/`checkTextExercise` for `generateCoachSet`/`checkCoachExercise`; `Exercises.jsx` replaces the old single fill-in-the-blank `TextExercise` with `CoachExercises`, a one-item-at-a-time flow covering all 5 types (including a click-to-build word-chip UI for `reorder`), with a blue "nice try" / green "exactly right" feedback card — no red states; new styles in `App.css`. `API_CONTRACT.md` updated to match.
- **Verified end-to-end via curl** against the running `app-custom` container: `/api/exercises/coach` returned 2 grounded concepts + 7 mixed exercises (one per type plus extras) in ~18s; concepts were upserted with `covered_on = CURRENT_DATE`; `/api/exercises/coach/check` tested for all 5 types (exact-match for fill_blank/multiple_choice, lenient LLM grading accepting missing accents/spaces for the rest, no shaming language); `exercise_done` points (+5 each) recorded; `/api/summary` now names the covered concepts as strengths and suggests the next one.
- **Gotcha hit**: the first full implementation pass removed `generate_text_exercise`/`render_text_exercise`/`render_exercise_feedback`/`TEXT_EXERCISE_SYSTEM`, which `app.py` (the README-documented fallback Blocks UI) still calls. Restored all four in clearly-labeled "kept for app.py's fallback" sections before committing — keeps the degrade-gracefully fallback intact.

---

## Sprint Day 4 — 2026-06-10 — Matched-image visual exercises + reliable TTS playback

### What changed (plain English)

The Visual exercise tab now has a "✨ Sample photo" mode — no upload needed. The app picks a photo that matches what your current lesson is about (a café menu for food vocabulary, a métro sign for transport, etc.) from a set of 15 ready-made scenes, and builds 3-5 exercises with hints from it. It keeps track of which photos you've already practiced with so you keep seeing fresh ones as you go. You can still upload your own photo in "📤 Upload your own" mode. Separately, every "🔊 hear it" button — word cards, dialogue lines, pronunciation targets — now reliably speaks in a French voice instead of sometimes falling back to a default English-sounding one on first use.

### What changed (technical)

- **`generate_sample_images.py`** (new, one-off) — generates 15 topic-themed images via HF `InferenceClient.text_to_image(..., model="black-forest-labs/FLUX.1-schnell")`, one per topic bucket from `nlp.detect_category` (Food & Dining and Daily Life have 2 each). Each entry also has a hand-written English `description` embedding the relevant French vocabulary — this is what grounds the exercises, not OCR/vision, since FLUX doesn't render legible in-image text reliably. Resizes to 640x640 JPEG (q=82, 46-114KB each, ~970KB total) and writes `frontend/public/sample_images/manifest.json`. Run once inside the `app-custom` container (no local Python env) and the output `docker cp`'d back to the host.
- **`db/init.sql`** — new `user_image_usage(user_id, image_id, used_at)` table + index, applied to the running Postgres so the matched-image picker can avoid repeats per user.
- **`prompts.py`** — new `VISUAL_TOPIC_EXERCISE_SYSTEM`/`visual_topic_exercise_user`: builds 3-5 exercises (vocabulary/translation/question) **with a `hint` field** from an image's `description` + (optionally) the current lesson text. Kept separate from the existing upload-flow `VISUAL_EXERCISE_SYSTEM` (2-3 exercises, no hints) so that flow's behavior is unchanged.
- **`exercises.py`** — new section: `_load_sample_images()` (cached manifest read), `pick_sample_image(topic, user_id)` (topic + unseen first, then any unseen, then least-recently-used, then `images[0]` as a final fallback), `_mark_image_used()`, `generate_visual_topic_exercise(image, lesson_text, user_id)` (calls `llm.chat_json` with the topic prompt — no vision call). `render_visual_exercises()` extended to render a `hint` line per exercise when present, shared by both the upload and sample flows.
- **`app_custom.py`** — new `POST /api/exercises/visual/sample`: detects the lesson's topic via `nlp.detect_category`, calls `pick_sample_image` + `generate_visual_topic_exercise`, awards `photo_exercise` points, returns `{image_url, topic, html}`.
- **`frontend/`** — `Exercises.jsx`'s `VisualExercise` is now a mode toggle (`✨ Sample photo` / `📤 Upload your own`, reusing the existing `.fc-subtab` styles) over two components: new `SampleVisualExercise` (calls `generateSampleVisualExercise`, shows the matched image + exercises, "🔄 Try another photo" to re-roll) and `UploadVisualExercise` (the original upload flow, unchanged). `api.js` adds `generateSampleVisualExercise`. `App.css` adds one rule (`.fc-visual-modes`). `API_CONTRACT.md` documents the new endpoint.
- **`tts.js`** — `getVoices()` returns `[]` on first call in Chrome until the `voiceschanged` event fires, so `speak()`/`speakAll()` could silently use a non-French default voice on first use. Now caches the voice list, refreshes it on `voiceschanged`, and explicitly sets `utterance.voice` to an `fr-FR` (or any `fr-*`) voice when available, while still setting `lang = 'fr-FR'` as a baseline.
- **Verified end-to-end via curl** against the rebuilt `app-custom` container: a Food & Dining lesson text matched `food_dining.jpg` with 3 hinted exercises; a second call for the same user cycled to `food_dining_2.jpg` (confirmed via `SELECT * FROM user_image_usage`); a Greetings lesson matched `greetings.jpg`; empty `lesson_text` fell back to `Daily Life`; `/custom/sample_images/food_dining.jpg` returns `200 image/jpeg`; `photo_exercise` points (+8) recorded for each call.
- **Regression check**: `/api/exercises/pronunciation/target` and `/api/exercises/pronunciation/check` still work correctly after the `exercises.py`/`prompts.py` changes. The upload-based `/api/exercises/visual` currently returns a `401 Unauthorized` from the OpenBMB vision endpoint — pre-existing and unrelated to this session's changes (no edits to `llm.py`); CLAUDE.md already flags this endpoint as subject to change. The new sample-photo flow has no dependency on it, since it doesn't call the vision model.

---

## Sprint Day 5 — 2026-06-10 — Gender Checker, Translator, and a real Summary dashboard

### What changed (plain English)

Two new tools live under the **🔤 Tools** tab: a **Gender Checker** — type any French noun and instantly see its gender, articles (le/la, un/une), an example sentence, and a memory tip — and a **Translator** for English↔French with alternative phrasings and an in-context example you can hear spoken aloud. The **⭐ Summary** tab is now a real dashboard: your total points, today's activity (lessons saved, exercises done, dialogue turns, words explored), a progress bar of A1-A2 concepts covered so far, and a gentle "ready to practice next" suggestion — alongside the existing encouraging recap. The app also picked up a small French-flag favicon. Just before this, the photo-exercise feature was simplified to drop the (currently non-working) photo-upload option, keeping only the "pick a matching photo for your lesson" mode that already works well.

### What changed (technical)

- **Pre-Day-5 cleanup (`91ee466`)**: removed the upload-based visual exercise entirely — `Exercises.jsx`'s mode toggle and `UploadVisualExercise`, `api.js`'s `generateVisualExercise`, and the `/api/exercises/visual` endpoint (plus its now-unused `UploadFile`/`File`/`Form`/`PIL.Image`/`io` imports in `app_custom.py`). `VisualExercise` is now just the working sample-photo flow. `app.py` (the Blocks fallback) is unaffected — it calls `exercises.generate_visual_exercise`/`llm.vision_chat` directly, not the removed endpoint.
- **`nlp.py`** — new `word_info(word)`: spaCy lemma + POS for a single word, instant/offline. **Gotcha**: spaCy's `fr_core_news_sm` morphologizer needs determiner-agreement context to tag noun gender correctly — an isolated "pomme" tags `Gender=Masc` (wrong; it's feminine) while "la pomme" correctly tags `Fem`. So gender/articles for the Gender Checker come from the LLM, not spaCy; `word_info` only supplies `lemma`/`pos` as a hint.
- **`prompts.py`** — new `GENDER_CHECK_SYSTEM`/`gender_check_user` (gender, le/la, un/une, example + translation, a memorable "pattern note"). New `TRANSLATE_SYSTEM`/`translate_user`, revised mid-session: the LLM was inconsistent about whether `example`/`example_translation` held the source or target language regardless of direction, so the schema is now language-explicit — `example_fr` is always French, `example_en` is always English.
- **`llm.py`** — `get_gender_check(word, pos)` and `translate_text(text, direction, lesson_text)`, both `chat_json` wrappers with offline-safe fallbacks.
- **`gamify.py`** — `get_concepts_progress()` now also returns `covered_count`/`total_count` (size of the A1-A2 syllabus slice) for the dashboard's progress bar.
- **`app_custom.py`** — new `POST /api/gender-check` (combines `nlp.word_info` + `llm.get_gender_check`) and `POST /api/translate`. `GET /api/summary` extended to also return `daily_stats` (from `gamify.get_daily_stats`) and `concepts` (from `gamify.get_concepts_progress`).
- **`frontend/`** — `Tools.jsx` restructured into three subtabs reusing the `.fc-subtabs` pattern: **Gender Checker** and **Translator** (both new) plus the existing paste-and-annotate flow renamed **Text Checker**. `App.jsx` now passes `lessonText` to `Tools` so the Translator can offer "use my current lesson as context". `Summary.jsx` gained a stats grid, a concepts-covered progress bar with pills for recently-covered concepts, and a next-focus line. New CSS in `App.css`: `.fc-gender-result`/`.fc-gender-pills`/`.fc-gender-example`/`.fc-gender-pattern`, `.fc-translate-result`/`.fc-translate-main`/`.fc-translate-alts`/`.fc-translate-example`, `.fc-btn-icon` (small inline speak buttons), and `.fc-summary-stats`/`.fc-stat-card`/`.fc-summary-progress`/`.fc-progress-bar`/`.fc-progress-fill`/`.fc-summary-pills`/`.fc-summary-next`. `api.js` adds `genderCheck`/`translateText`.
- **Polish**: replaced the default Vite favicon with a small French-tricolor square (`frontend/public/favicon.svg`), referenced via `<link rel="icon">` in `index.html` (Vite rewrites this to `/custom/favicon.svg` for the Space-root build, served by the existing `/custom` StaticFiles mount).
- **Verified end-to-end via curl** against the rebuilt `app-custom` container: `/api/gender-check` for "pomme" → `Fem`/`la`/`une` (correct) and "arbre" → `Masc`/`l'`/`un` (correct vowel elision); `/api/translate` both directions return the new `example_fr`/`example_en` shape correctly; `/api/summary` returns `daily_stats` + `concepts` with `covered_count`/`total_count`; `/custom/favicon.svg` returns `200`.
- **`API_CONTRACT.md`** updated: new `/api/gender-check`/`/api/translate` sections, `/api/summary` response shape, and the Tools screen's endpoint map.

---

## Notion-style block editor — 2026-06-11 — A real notebook editor, not a textarea

### What changed (plain English)

The Notebook's plain text box is now a proper block-based note editor, like Notion. Type `# ` for a heading, `- ` or `1. ` for a list, `> ` for a highlighted note/quote, and `---` for a divider — each converts as you type. Select any text to get a small floating toolbar for **bold**, *italic*, and ~~strikethrough~~. Typing `/` on an empty line opens a menu to insert any block type. Everything you already use — gender colors, the word card, Save/Update/Delete, Chat, Exercises, Tools — keeps working exactly as before, and old lessons saved before this change open up just fine.

### What changed (technical)

- **`frontend/src/blocks.js`** (new) — pure helpers, no React. `markdownToBlocks`/`blocksToMarkdown` round-trip a small internal Markdown-ish dialect (`# /## /### ` headings, `- `/`* `/`1. ` lists, `> ` quotes, `---` dividers, `**bold**`/`*italic*`/`~~strike~~` inline) to/from `{id, type, html}` block objects. `blocksToPlainText`/`stripMarkdown` strip all markers for spaCy/LLM context.
- **`frontend/src/components/BlockEditor.jsx`** (new) — renders one `contentEditable` element per block (grouped `<ul>`/`<ol>` for consecutive list items). Uncontrolled-DOM pattern with ref callbacks + a `pendingFocus` state to restore caret position after structural edits (split on Enter, merge on Backspace, type-conversion via shortcuts or the `/` slash menu, exit-list on empty Enter). A `selectionchange` listener shows a floating Bold/Italic/Strikethrough toolbar using `document.execCommand`.
- **Storage stays a single string** — `raw_text`/`text` is now this Markdown dialect instead of plain prose, but it's still just a string: **no DB schema change, no API change, no new dependencies**. Old plain-prose lessons parse as one paragraph block automatically.
- **`frontend/src/screens/Notebook.jsx`** — swapped the `<textarea>` for `<BlockEditor key={lessonId ?? 'new'} value={text} onChange={setText} />`; `/api/annotate` calls and the `lessonText` sent to Chat/Exercises/Tools now use `stripMarkdown(text)` so spaCy/the LLM never see `#`/`-`/`**`/`>` markers.
- **`frontend/src/App.css`** — new block-editor styles: `.fc-block-editor` container, heading sizes, `.fc-block-quote` (reuses the `.fc-gender-pattern` accent look with a left border), `.fc-block-divider`, list spacing, `.fc-slash-menu`/`.fc-floating-toolbar` (absolute-positioned dropdown/pill).
- **Bug found and fixed during testing**: the `# `/`- `/`> `/etc. auto-format shortcuts changed a block's `type` (e.g. `<p>` → `<h1>`) but never restored focus to the new DOM element React creates for the new tag, so subsequent keystrokes went nowhere. Fixed by setting `pendingFocus({ id, position: 'start' })` after the type conversion in [BlockEditor.jsx](frontend/src/components/BlockEditor.jsx).
- **Verified via Playwright** against the rebuilt `app-custom` container: all block types + shortcuts + the `/` slash menu + floating toolbar work; an existing 55-block real lesson (with a Markdown table from the Notion import) loads with zero console errors; a new lesson with heading/bold/list/quote round-trips correctly through Save → Lessons search → reopen; gender-color annotation on the new content shows clean prose with no Markdown leakage.

---

## Exercises & Tools UX upgrades — 2026-06-11 — Practice on your own topic, with help nearby

### What changed (plain English)

Every exercise type — Coach, Dialogue, Visual, and Pronunciation — now has an optional "topic" box: leave it blank and the coach picks the topic for you (as before), or type something like "ordering food" or "le passé composé" to steer what gets generated. Visual (photo) exercises now generate at least 5 questions, and each one has its own answer box and a "Check answer" button with the same gentle, encouraging feedback as the other exercises — no more "show answer" only. While doing any exercise, a new **🔧 Tools** button opens the Gender Checker and Translator in a side panel, so you can look something up without losing your place. The Translator (in Tools and in this new side panel) can now show up to 3 translators side by side, each with its own direction (English→French or French→English) — handy for checking a few words or a sentence at once.

### What changed (technical)

- **`prompts.py`** — `coach_plan_user`, new `dialogue_user`, and `visual_topic_exercise_user` all gained an optional `topic: str = ""` that appends a "Focus topic requested by the learner" line to the prompt when non-blank. `coach_check_user`'s content fallback chain now also checks `exercise.get("content")`, needed because visual exercises store their prompt text under `content`. `VISUAL_TOPIC_EXERCISE_SYSTEM` now asks for "5-6" exercises (was "3-5") to guarantee the user's "at least 5" requirement.
- **`exercises.py`** — `generate_exercise_set`, `generate_dialogue`, `generate_visual_topic_exercise`, and `generate_pronunciation_target` all take an optional `topic: str = ""` and thread it into the prompts above (with sensible defaults preserving old behavior for `app.py`'s Gradio mockup, which is otherwise untouched).
- **`app_custom.py`** — `/api/exercises/coach`, `/api/exercises/dialogue`, `/api/exercises/visual/sample`, and `/api/exercises/pronunciation/target` all read an optional `topic` from the payload. For visual, if a topic is given, `nlp.detect_category(topic)` is tried first to pick the sample image (falling back to the lesson-based detection if the topic doesn't match a known category) — so e.g. typing "ordering food" can surface a Food & Dining photo even from an unrelated lesson. The visual endpoint no longer returns pre-rendered `html`; it returns `{image_url, topic, image_summary, exercises}` so the frontend can render interactive cards.
- **`llm.py`** — `chat_json` now takes an optional `max_tokens` (default 512, forwarded to `chat()`). **Gotcha hit during testing**: with the visual prompt now asking for 5-6 exercises, the JSON response was getting cut off at the default 512 tokens and silently falling back to `{"exercises": []}`. Fixed by calling `generate_visual_topic_exercise`'s `chat_json` with `max_tokens=1536`.
- **`frontend/src/components/QuickTools.jsx`** (new) — `GenderChecker` (moved verbatim from `Tools.jsx`), `TranslatorWidget` (the old `Translator`, now with an optional "✕ remove" button), and `TranslatorPanel` (manages 1-3 `TranslatorWidget`s in a responsive grid, "+ Add another translator" up to 3, hides remove buttons at 1). Shared by `Tools.jsx` and the new Exercises side panel.
- **`frontend/src/screens/Tools.jsx`** — now imports `GenderChecker`/`TranslatorPanel` from `QuickTools` instead of defining them locally; `TextChecker` and the screen wrapper are unchanged.
- **`frontend/src/screens/Exercises.jsx`** — `VisualExercise` rewritten: drops `dangerouslySetInnerHTML={{__html: data.html}}` for React-rendered cards (one per `data.exercises[i]`), each with its own `{answer, feedback, checking, error}` state, an `<input>` + "Check answer" calling the existing `checkCoachExercise` (same grading endpoint Coach exercises use), and feedback rendered with the same `.fc-coach-feedback*` classes. `data.image_summary` shows as an italic caption under the photo. All four exercise components gained a topic `<input>` next to their generate/start button. The top-level `Exercises` component gained a "🔧 Tools" toggle, a `.fc-exercises-layout` two-column layout when open, and a sticky `ToolsPanel` (mini Gender/Translate subtabs + "✕ Close") — this state lives above the per-subtab components, so it survives switching between Coach/Dialogue/Visual/Pronunciation.
- **`frontend/src/App.css`** — new `.fc-exercises-layout` (1fr/320px grid, collapses under 900px), `.fc-tools-panel` (sticky), `.fc-translator-grid` (responsive `auto-fit` grid for 1-3 translators), `.fc-translator-widget`/`.fc-translator-remove` (relative positioning for the "✕"), `.fc-visual-summary` (italic caption), and `.fc-translate-result` now gets its own `margin-top`/`border-top` separator since it's no longer nested inside a second `.fc-card`.
- **Verified via curl** against the rebuilt `app-custom` container: `/api/exercises/visual/sample` now returns 5 structured exercises (previously fell back to `exercises: []` until the `max_tokens` fix) with `image_summary`; `/api/exercises/coach/check` correctly grades a visual `vocabulary`-type exercise via its `content` field; `/api/exercises/pronunciation/target` with `topic: "ordering coffee at a café"` returns a phrase grounded in that topic. `npm run build` + `docker compose up -d --build app-custom` succeeded; served bundle hashes confirmed up to date.

---

## Day 10 — 2026-06-15 — Live on Hugging Face Spaces (hackathon deadline day)

### What changed (plain English)

French Coach is now live at **https://build-small-hackathon-french-coach.hf.space** under the `build-small-hackathon` org. Open it in any browser and you'll see the full themed Gradio UI — notebook sidebar, gender-coloured text, word cards, chat coach, all four exercise types, and the daily summary — all powered by MiniCPM4.1-8B via the OpenBMB API. This is the hackathon submission build.

### What changed (technical)

- **`README.md`** — `app_file: app_custom.py` → `app_file: app.py` (Gradio Blocks UI as entry point). The React / FastAPI custom UI (`app_custom.py`) is preserved in the repo for post-hackathon use, but the Gradio Blocks UI is the correct HF `sdk: gradio` entry point: the HF runner imports the module, finds the `demo` variable, and calls `demo.launch()` itself — no port conflict.
- **`app.py`** — Two HF Space compatibility fixes:
  - `gr.LoginButton` + `gr.LogoutButton` removed: in Gradio 6, having a `LoginButton` triggers OAuth setup, which requires `hf_oauth: true` in Space metadata and the `OAUTH_CLIENT_ID` secret — neither configured. Their removal lets the app start cleanly.
  - `css`, `theme`, `js` moved from `demo.launch()` args to the `gr.Blocks()` constructor: the HF SDK runner calls `demo.launch()` without our custom args, so the only way to guarantee the French-themed CSS and JS fire is to bake them into the `Blocks` object at definition time. Gradio 6 emits a `UserWarning` about this (they want them in `launch()`), but the warning does not prevent the app from loading.
- **`llm.py`** — Removed `import spaces` and `@spaces.GPU` entirely from `llm.py` (they belonged in the HF `app_file` per ZeroGPU static scan rules). Added `register_gpu_fn(fn)` injection point so `app_custom.py` can wire in the GPU function without a circular import — ready for when we re-enable ZeroGPU hardware.
- **`app_custom.py`** — Added `@spaces.GPU` function at the very top of the file (the correct location for ZeroGPU static scan), with a `try/except ImportError` so local dev works without the HF-pre-installed `spaces` package. Calls `llm.register_gpu_fn()` right after import to wire it in.
- **`requirements.txt`** — Added `transformers>=4.40`, `accelerate>=0.30` (needed for the ZeroGPU model-load path; harmless on cpu-basic). `spaces` intentionally NOT added — HF pre-installs the real ZeroGPU `spaces` package; `pip install spaces` installs a different PyPI package that breaks the GPU function registration.
- **Hardware / secrets** — Space changed from `zero-a10g` to `cpu-basic` (break-glass: avoids ZeroGPU startup check entirely). `LLM_BACKEND=openbmb` set as Space secret → text generation calls MiniCPM4.1-8B via the OpenBMB free API.
- **Gotchas hit during this session:**
  - ZeroGPU "No @spaces.GPU function detected during startup": fired even with `@spaces.GPU` in `llm.py`. Root cause: HF ZeroGPU static scan only inspects `app_file` (`app_custom.py`), not imported modules. Moving the decorator to `app_custom.py` was correct, but we still hit the port-conflict on `cpu-basic` (see below).
  - "Address already in use 7860": with `sdk: gradio`, the HF runner starts its own server; our `uvicorn.run()` in `__main__` clashed. Fix: switch to `app.py` (demo-variable pattern) where the HF runner owns the server startup.
  - `pip install spaces` installs a different PyPI `spaces` package that does not register functions with the real ZeroGPU system; removing it from `requirements.txt` unblocks ZeroGPU for future use.

