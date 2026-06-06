# CLAUDE.md — French Coach

> Project brief and source of truth for build decisions. Read fully before writing code. Supersedes earlier docs for *how to build*; longer rationale in `docs/French-Coach-Technical-Plan.md` (optional).

---

## 1. What we're building

A **living French notebook** for an adult learning French on a ~4-month timeline for Canadian immigration (TEF/TCF, target ≈ CLB/NCLC 7). The user is A1 going to A2, takes a tutor-led course, and today juggles Notion (class notes) + 3–4 Chrome tabs (translate / pronounce / gender-check). This app collapses that into one surface and adds practice the user can't get between classes.

Hackathon entry: **Build Small Hackathon** (Gradio + Hugging Face), models **≤ 32B**, **Gradio app hosted as a Space under the `build-small-hackathon` org**, deadline **June 15 2026**. Track: **Backyard AI** (build for a real person — the user). Also the seed of a real commercial product, so architecture matters, but the public Space ships a deliberately scoped subset (§3).

**Guiding principles**
1. **Grounding, not fine-tuning.** Value is dynamic per-user data (notes, covered concepts). Feed the model context at request time. Model choice settled by eval, not training.
2. **Split deterministic from intelligent.** Gender/POS/lemma → spaCy (instant, offline, free). Meaning / grammar / titles / exercises / dialogue / chat → LLM, on demand.
3. **Postgres from day one.** Separate Docker container locally (Compose); Supabase (hosted Postgres) on the Space. Same schema, one env var switches. Data persists from day one.
4. **Encouraging by design.** All feedback is constructive and forward-looking. Never critical, never guilt-based. (See §5 gamification rules — this is a hard constraint, not a style preference.)
5. **Degrade gracefully.** Each day ships something runnable; a lost day still leaves a working app one notch back.

---

## 2. User, constraints, credentials (do not re-ask)

- macOS Apple Silicon (M4 Pro). Claude Code installed. HF account joined to the `build-small-hackathon` org.
- Budget ~1 hr/day. Optimize for low friction and fast iteration. User is newer to tooling — explain non-obvious "why" in commits.
- Docker Desktop installed and running. Local stack = Docker Compose (app + Postgres).
- Credits: $250 Modal (eval only), $20 HF (buffer).

### Free OpenBMB inference API (hackathon-provided — use as the dev backend)
OpenAI-compatible. No HF quota, no cold starts. Put in `.env`, never commit.
```
MINICPM_API_BASE=http://35.203.155.71:8001/v1     # MiniCPM4.1-8B (text)
MINICPM_VISION_BASE=http://35.203.155.71:8003/v1  # MiniCPM-V-4.6 (vision)
MINICPM_API_KEY=sk-minicpm-V8bcD-YTAMxECagaKOnbwTCN69IIN2LhSezGOgq2Ues
```
Use the `openai` Python client pointed at these base URLs. (Endpoint may change — if calls fail, check the hackathon Discord and fall back to HF `InferenceClient`.)

---

## 3. Scope split — PUBLIC vs PRIVATE (critical)

The Space is **public and exposes its files**, so it ships only **non-novel, safe-to-expose features**. The novel adaptive engine stays **private** for the commercial build. Data (notes, exercises, points) IS persisted via Supabase — the moat is the *intelligence*, not the storage.

### PUBLIC Space — the hackathon submission (BUILD THIS)
A French **notebook** app where each page is a class lecture, plus practice generated *from that lecture*:

1. **Notebook.** Sidebar of saved pages (LLM-titled + dated), persisted to Supabase. Main area = editor or saved page.
2. **Smart workspace.** Write/paste notes; gender-coloring toggle (nouns colored masc/fem); click any word → card (gender, meaning, grammar note, pronunciation via browser TTS).
3. **Chat coach.** Expandable panel for free-form French questions.
4. **Text exercise.** One exercise generated from the current lesson + model answer/explanation.
5. **Dialogue exercise.** LLM writes a short scene dialogue from the lesson's vocab/grammar; agent takes one role and *speaks* its lines (browser TTS); user types/says their lines; LLM gives encouraging feedback. A2 variant: agent speaks a prompt line, user composes a contextual one-liner reply.
6. **Visual exercise.** User uploads a real photo (café menu, street sign, recipe); **MiniCPM-V 4.6** reads it; LLM generates French exercises grounded in what's in the image. (Signature feature — uniquely demoable.)
7. **Pronunciation check.** TTS speaks a line; browser Web Speech API captures the user's spoken answer; transcription shown; LLM compares to target and gives gentle correction. (No ASR model — browser-native.)
8. **Encouraging daily summary + points** (see §5).

One-liner: *"A French notebook that turns your class notes into practice — see gender at a glance, hear and speak dialogues, snap a photo for instant exercises, and get a daily boost."*

### PRIVATE — commercial moat (DO NOT build into the public Space)
- Personalized assessment & weakness detection **across all lessons / profile-wide**.
- Mastery map over time; adaptive practice loop that recycles past mistakes profile-wide.
- Full TEF/TCF exam simulation, CLB/NCLC tracking, structured A1→B2 pathway, spaced repetition.
- Multi-user accounts.

> The public Space generates practice from the *current lesson only*. Profile-wide adaptive customization is the moat — keep it out. If a task crosses that line, stop and flag it.

---

## 4. Hackathon eligibility strategy (maximize tracks + badges)

Hard rules (must satisfy all): model **≤ 32B**; **Gradio app**; **Space under the org**; **demo video + social post** at submission.

Target every badge that's a natural fit:

| Badge | How we earn it | Build day |
|---|---|---|
| 🎨 Off-Brand (custom UI) | French-themed custom Gradio frontend, not default look | Day 8 polish |
| 📓 Field Notes | Blog post: model eval + what we learned building it | Day 9 |
| 🎯 Well-Tuned | *Stretch* — publish a small fine-tune to HF if Day-10 buffer allows; otherwise skip | Day 10 (optional) |
| 🔌 Off the Grid | *Stretch* — a fully-local variant running MiniCPM5-1B via MLX on the Mac, no cloud calls | post-submission optional |

**OpenBMB special prize ($2500/track):** "built around MiniCPM" is a stated strength. We use **MiniCPM4.1-8B** (text) + **MiniCPM-V 4.6** (vision) as the core. Lead the demo and write-up with this.

**"More than a chatbot wrapper":** the gender-map, photo→exercise, and spoken dialogue features make this clearly not a chat wrapper — call that out explicitly in the submission.

Primary track = **Backyard AI** (real person, real use, the user dogfoods it daily). The encouraging daily summary directly supports the "the person actually used it" judging criterion — screenshots of accumulated points/summaries are evidence of real use.

---

## 5. Gamification — encouraging, never critical (hard rules)

Purpose: sustain motivation for a solo learner on a hard timeline. It must **inspire**, never shame.

**Daily summary** (generated by the LLM from the DB, shown on open):
- Leads with gains: "You've covered 6 concepts and 48 words. You're solid on gender agreement and café vocabulary."
- Frames gaps as opportunities: "Ready to practice next: passé composé." NEVER "you're weak at / you failed / you keep getting X wrong."
- Warm, brief, specific. One encouraging line + 2–3 concrete wins + 1 gentle "next."

**Points (additive only):**
- Earn points for *doing*: saving a lesson, completing an exercise, a dialogue turn, a pronunciation attempt, opening the app a new day.
- **Never deduct points. Never penalize mistakes.** A wrong answer still earns participation points.
- Small named milestones ("First Dialogue", "Photo Explorer", "Week One"), framed as celebrations.

**Hard prohibitions (enforce in prompts and UI):**
- No streak-loss guilt, no red error counters, no "you missed yesterday", no leaderboards-vs-others, no shaming copy.
- LLM feedback prompts must instruct: encouraging, constructive, forward-looking; name one fix at a time; affirm effort.
- If the user is struggling, the tone softens further — never piles on.

DB: a `points` ledger (append-only) + a computed daily summary. Points are participation signals, not scores.

---

## 6. Tech stack (decided)

| Layer | Choice | Notes |
|---|---|---|
| Language | Python 3.12 | ZeroGPU-compatible |
| UI | Gradio (pin v6.x) | hackathon framework; only SDK ZeroGPU supports |
| Clickable reader | `gr.HTML` + JS (event delegation, `js=`) | see §11 gotchas |
| Deterministic NLP | spaCy `fr_core_news_sm` + gender lexicon | gender/POS/lemma; instant, offline |
| LLM text (dev) | **MiniCPM4.1-8B** via free OpenBMB API (`openai` client) | no quota/cold start; OpenBMB prize |
| LLM vision | **MiniCPM-V 4.6** via free OpenBMB API | photo → exercise |
| LLM (demo deploy) | eval winner on ZeroGPU (MiniCPM4.1-8B vs Lucie-7B vs Mistral-7B) | Option C |
| TTS (speak) | browser `speechSynthesis` | free; upgrade to VoxCPM2/Nemotron TTS post-MVP |
| ASR (listen) | browser Web Speech API | free; upgrade to Cohere Transcribe/Nemotron ASR post-MVP |
| Containers | Docker Compose | app + Postgres |
| DB (local) | Postgres 16 (separate container, named volume) | data survives restarts |
| DB (Space) | Supabase free tier | same schema; `DATABASE_URL` switch; use pooler port 6543 |
| Eval | Modal (one-off) | MiniCPM4.1-8B vs Lucie vs Mistral vs Luth |

All candidate text models ≤ 32B and Apache-2.0 (or free-API). **Not Cohere/Command R+** (104B, CC-BY-NC) for the core — post-hackathon only.

---

## 7. Repository layout

```
french-coach/
├── app.py            # Gradio notebook UI + event wiring
├── llm.py            # text + vision LLM calls (OpenBMB API / ZeroGPU), backend switch
├── nlp.py            # spaCy annotation (gender/POS/lemma) + gender lexicon
├── db.py             # Postgres connection + query helpers
├── notebook.py       # page CRUD
├── exercises.py      # text / dialogue / visual / pronunciation generators + graders
├── gamify.py         # points ledger + encouraging daily-summary builder
├── prompts.py        # all prompt templates (encouraging tone enforced here)
├── models.py         # dataclasses matching the schema
├── syllabus.json     # CEFR/TCF scope map (from one-time Notion export)
├── seed_texts/       # sample lecture notes for cold start / demo
├── db/init.sql       # schema (runs on first Postgres start)
├── requirements.txt  # + openai, psycopg2-binary
├── docker-compose.yml
├── Dockerfile
├── .dockerignore .gitignore .env.example
├── README.md         # HF Space metadata (sdk/hardware)
├── CLAUDE.md
└── docs/French-Coach-Technical-Plan.md
```

---

## 8. Database schema (db/init.sql)

```sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    raw_text TEXT NOT NULL,
    annotations JSONB DEFAULT '{}'::jsonb,   -- cached gender/POS/lemma per token
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS concepts (
    id TEXT PRIMARY KEY, name TEXT NOT NULL,
    cefr_level TEXT NOT NULL, family TEXT NOT NULL, covered_on DATE
);

CREATE TABLE IF NOT EXISTS exercises (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    page_id UUID REFERENCES pages(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,            -- 'text' | 'dialogue' | 'visual' | 'pronunciation'
    prompt TEXT, model_answer TEXT,
    content JSONB DEFAULT '{}'::jsonb,   -- dialogue lines, image refs, etc.
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Gamification: append-only participation ledger (NEVER deduct)
CREATE TABLE IF NOT EXISTS points (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reason TEXT NOT NULL,          -- 'saved_lesson'|'exercise_done'|'dialogue_turn'|'daily_open'|...
    amount INT NOT NULL CHECK (amount > 0),
    earned_at TIMESTAMPTZ DEFAULT NOW()
);

-- PRIVATE (commercial only — defined, never written by the public Space)
CREATE TABLE IF NOT EXISTS mistakes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    concept_id TEXT REFERENCES concepts(id), category TEXT NOT NULL,
    user_answer TEXT, correct_answer TEXT, explanation TEXT, made_on TIMESTAMPTZ DEFAULT NOW()
);
```

JSONB for `annotations` and exercise `content` (flexible document data); typed columns for everything queried.

---

## 9. Environment variables

`.env` (local, git-ignored) / `.env.example` (committed, empty values):
```
# OpenBMB free API (dev)
MINICPM_API_BASE=http://35.203.155.71:8001/v1
MINICPM_VISION_BASE=http://35.203.155.71:8003/v1
MINICPM_API_KEY=sk-...
LLM_BACKEND=openbmb            # 'openbmb' | 'zerogpu'
# HF
HF_TOKEN=hf_...
# DB — local Compose ('db' = service name)
POSTGRES_PASSWORD=localdevpassword
DATABASE_URL=postgresql://postgres:localdevpassword@db:5432/frenchcoach
```
On the Space (Settings → Secrets): `LLM_BACKEND=zerogpu`, `DATABASE_URL` = Supabase pooler URL (port 6543), `HF_TOKEN`. requirements add: `openai`, `psycopg2-binary`.

---

## 10. Build order — iterative, one feature per day on top of a working MVP

Each day = a new runnable capability layered on the last. Deploy is de-risked Day 2; the hero interaction is proven Day 1.

| Day | New capability added | Expected outcome (how you verify) |
|---|---|---|
| 0 | Infra + content prep | `docker compose up` runs app + Postgres; schema applied; Supabase project created; Notion A1/A2 export → `syllabus.json` + `seed_texts/` committed |
| 1 | Clickable gender-colored editor **prototype** (mock data) | In a clean prototype: toggle colors nouns, clicking a word shows a card, TTS speaks it. Annotation JSON schema locked |
| 2 | Live empty Space + prototype ported into `gr.HTML` | Public Space under the org loads the editor with mock data — deployment proven early |
| 3 | Real spaCy annotation + TTS | Gender colors + POS are real and instant; word card shows gender/lemma; speaker button works |
| 4 | LLM word card (meaning + grammar) via OpenBMB API | Clicking a word fetches a clear English meaning + one-line grammar note; cached in `annotations` |
| 5 | Notebook persistence | Save editor → LLM auto-title + date → row in `pages` (Supabase) → appears in sidebar; reopen shows it (survives refresh) |
| 6 | Chat coach + **text exercise** | Ask a question and get an answer; "generate exercise" produces one item from the lesson + model answer; saved to `exercises` |
| 7 | **Dialogue exercise** (+ A2 one-liner) | LLM builds a scene dialogue from the lesson; agent speaks its line (TTS); user replies; gets encouraging feedback |
| 8 | **Visual exercise** (MiniCPM-V) + **gamification** + custom UI | Upload a photo → French exercise generated from it; points accrue; encouraging daily summary shows; French-themed look (🎨 badge) |
| 9 | **Pronunciation check** + Modal **eval** + Field Notes draft | Speak an answer → transcription + gentle correction; eval picks the demo model; blog draft started (📓 badge) |
| 10 | ZeroGPU deploy + record demo + submit | Space runs the chosen model on ZeroGPU; pre-warmed; 2-min video + social post; submitted before Jun 15 |

**If a day slips:** the gender-mapped notebook + one text exercise is already a complete Backyard-AI submission. Cut order: pronunciation → visual → dialogue → chat. Gamification's daily summary is cheap and high-value for the "actually used it" criterion — keep it if at all possible. Never build moat features.

---

## 11. How the user should work this plan

- **One session = one day's row.** Start each session by telling Claude Code the day number; it implements that row only, keeps the app runnable, and commits.
- **Verify against the "expected outcome" column** before moving on. If it doesn't do that thing, it's not done.
- **Dogfood daily.** Use it on real class notes — this is both the product test and the Backyard-AI evidence (screenshots of summaries/points).
- **Keep a running note** of surprises/decisions — that becomes the Field Notes post (📓 badge) with no extra work.
- **Pre-warm before recording** the demo.

---

## 12. Conventions & gotchas

- `gr.HTML` re-renders kill inline `onclick`/`<script>` — use **event delegation** on a stable container + Gradio 6 `js=`. Prove in the Day-1 prototype.
- **Pre-process once, clicks instant** — annotate text in one spaCy pass, cache in `annotations`; clicks never hit the network for gender/POS.
- **DB connection per request** (psycopg2 isn't thread-safe across Gradio workers). Supabase: use the **pooler** (port 6543) on the Space.
- **Encouraging tone is enforced in `prompts.py`** — every feedback/summary prompt instructs constructive, forward-looking, one-fix-at-a-time language. No shaming, ever (§5).
- Pin `gradio>=6,<7`. Apple Silicon: all deps have arm64 wheels; the 7B never runs locally (API/ZeroGPU).
- **Never:** secrets in code; Notion connector in-app; profile-wide adaptive features in the public Space; writing to `mistakes` from the public Space; deducting points.
- Commits: small, runnable, per-day; explain non-obvious "why".

---

## 13. Definition of done (hackathon)

A public Gradio Space **under the build-small-hackathon org** where the user opens a notebook (persisted to Supabase), writes class notes, sees gender at a glance, clicks words for meaning/grammar/pronunciation, asks the coach, and practices via text + spoken dialogue + photo-based + pronunciation exercises — all generated from the current lesson — with an encouraging daily summary and additive points, running the eval-chosen MiniCPM model on ZeroGPU, custom French-themed UI (🎨), plus a 2-min demo video, social post, and Field Notes write-up (📓). Built around MiniCPM (OpenBMB prize). GitHub private; Space public; secrets in Space settings.
