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
