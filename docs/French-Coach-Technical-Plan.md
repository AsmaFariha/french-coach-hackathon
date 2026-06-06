# French Coach — Technical Plan & Design Rationale

> The companion to `CLAUDE.md`. CLAUDE.md says *what to build and how*; this document explains *why* — the reasoning behind each decision, the alternatives considered and rejected, and the architecture in depth. It is also raw material for the Field Notes blog post (📓 badge): the narrative of how the project was reasoned through.

Version 1.0 · Living document.

---

## Table of contents

1. The problem and why it's worth solving
2. Competitive landscape — where existing tools fall short
3. Product concept — the "living notebook"
4. Core architectural decisions (with rationale)
5. Model selection — the journey and the eval
6. The two-deployment model
7. Database architecture
8. Public vs private — the scope split and the moat
9. Exercise design
10. Gamification design
11. Hackathon strategy — tracks, badges, prizes
12. Build methodology
13. Risks and mitigations
14. Beyond the hackathon — the commercial roadmap

---

## 1. The problem and why it's worth solving

The user is an adult learning French on a compressed timeline (~4 months) for Canadian permanent residency, where French proficiency on the TEF/TCF exams converts directly into immigration points (target ≈ CLB/NCLC 7). They are A1 moving to A2, taking a tutor-led course, and motivated by a concrete, high-stakes deadline.

The pain is not a lack of learning material — they have a tutor and structured lessons. The pain is **everything that happens between classes**:

- Class notes live in Notion as **static text** — written once, rarely revisited, impossible to practice against.
- Producing written French means juggling **3–4 browser tabs**: one to translate English→French, one or two to hear pronunciation, one to check noun gender (le/la).
- There is **no way to practice a specific topic on demand** and get it checked — no tutor available at 11pm when reviewing *connecteurs de cause*.
- There is **no feedback loop** showing where they're strong versus where they need work.

This is a real person with a real, specific, time-bound problem — exactly what the hackathon's Backyard AI track asks for. And because the user *is* the builder, the app can be dogfooded daily, which is both the best possible product test and direct evidence for the "the person actually used it" judging criterion.

---

## 2. Competitive landscape — where existing tools fall short

We researched the market before designing, to ensure we'd fill a genuine gap rather than rebuild what exists. The market splits into four camps, and crucially **no single tool combines them**:

**Habit-builders (Duolingo).** Excellent for starting from zero, but plateau around B1, teach grammar through pattern-matching rather than explanation, and offer no exam-specific preparation. The streak mechanic creates an illusion of progress that doesn't map to real-world ability — dangerous for someone on an exam clock.

**Structured courses (Babbel, Busuu).** Teach grammar far better, with explanations written by linguists. But explanations are situational — they tell you the rule for the sentence in front of you, not whether it generalizes — so pattern-thinkers plateau. Neither adapts to *your* specific recurring mistakes.

**Exam-prep platforms (PrepMyFrench, PrepMyFuture).** Closest to the goal — they mirror the official TEF/TCF format with AI-graded feedback and target-score dashboards. But they are drill-and-test machines that assume you already know French; they don't *teach* a beginner, and they don't solve the daily writing-workflow friction.

**Readers (Readlang, LingQ).** Solve exactly one pain beautifully — click any word to translate, auto-create flashcards. But they're read-only: no gender-on-demand, no grammar explanation, no writing help, no exam alignment.

**The gap, stated plainly:** the user's "Notion + 3 Chrome tabs" workflow exists precisely because they are manually stitching together four product categories. No app unifies *learning*, *contextual reference*, *writing assistance*, and *practice-with-feedback* grounded in the learner's own curriculum. That unification is the product.

---

## 3. Product concept — the "living notebook"

The reframe that made the concept click: this is **not a curriculum**. The user already has lessons and a tutor. It is the **practice-and-feedback layer** that sits on top of the learning they're already doing.

The concept in one sentence: *a single home base that replaces Notion and the cluster of Chrome tabs — where class notes live, every word is interactive, and a tutor-agent generates practice from those exact notes, gives encouraging feedback, and keeps motivation high.*

Each notebook page is a class lecture. From that lecture's content, the app generates practice the user can't otherwise get between classes. The unifying insight: because the user's notes and history live in one place, the agent always knows what's been covered, so practice is always on-scope and grounded — never quizzing on something not yet learned.

---

## 4. Core architectural decisions (with rationale)

### 4.1 Grounding, not fine-tuning

**Decision:** feed the model context at request time (the syllabus scope, the current lesson). Do not fine-tune a custom model for the core product.

**Why.** Everything that makes the app valuable is *dynamic, per-user data* — the notes written today, the concepts covered this week, the mistakes made this session. Fine-tuning bakes knowledge into model weights at training time and freezes it; a fine-tuned model fundamentally cannot know what the user learned yesterday. Grounding (retrieval-augmented generation) gives everything fine-tuning would — domain-appropriate behavior — plus the thing fine-tuning can't: daily adaptation to a learner whose knowledge grows. It is also dramatically faster to build and debug on a 1-hour-a-day budget.

**What we rejected.** Full fine-tuning (days of compute, curated datasets, ML expertise — out of scope). LoRA/QLoRA (2–3 hours minimum setup, high risk of consuming the whole sprint). The honest framing for judges is stronger than "I fine-tuned a model": *we evaluated fine-tuned French models and chose grounding because the app's value is adapting to live student data, which fine-tuning can't do.*

**Note:** a small fine-tune remains a Day-10 *stretch* purely to earn the 🎯 Well-Tuned badge — not because the product needs it.

### 4.2 Split deterministic work from intelligent work

**Decision:** gender, part-of-speech, and lemma come from spaCy (a deterministic NLP library, offline, free, instant). Only meaning-in-context, grammar explanation, titles, exercises, dialogue, and chat go to the LLM, and only on demand.

**Why.** This removes the single biggest reliability risk. Asking a 7–8B model to reliably return structured gender/POS for *every word on every click* is fragile and slow; spaCy does it deterministically in one pass with zero network calls. It also collapses cost to near zero — the headline interaction (gender-colored reading, clicking words) never touches a paid or rate-limited endpoint. The model is reserved for what genuinely needs intelligence.

**The pattern in practice:** annotate the whole text once with spaCy, cache the result in the page's `annotations` JSONB column, and clicks are instant forever after. The model is called only when the user explicitly asks for meaning or a grammar note.

---

## 5. Model selection — the journey and the eval

The model choice evolved as we learned more, which is itself worth documenting honestly.

**First candidate: Lucie-7B-Instruct (OpenLLM-France).** Attractive because it's French-first, Apache-2.0 (commercial use allowed), and already a published fine-tune — it tells a "sovereign French AI" story. Risk: it's less mainstream, so more prone to cold starts and patchy availability on free inference tiers.

**Reliability fallback: Mistral-7B-Instruct.** Not French-specific but very strong on French and instruction-following, far more mainstream, so more reliable for day-to-day development. Apache-2.0.

**The decisive find: OpenBMB's free hackathon API.** The hackathon AMA revealed OpenBMB (an anchor sponsor with a dedicated $2500/track prize) providing **free, OpenAI-compatible, hosted access** to MiniCPM4.1-8B (text) and MiniCPM-V 4.6 (vision) — no HF quota, no cold starts. This reshaped the plan:
- **MiniCPM4.1-8B becomes the dev backend** — fast iteration, no quota anxiety, and using it targets the OpenBMB prize. It's an 8B hybrid-reasoning model whose "study tutor" use case fits exactly.
- **MiniCPM-V 4.6 unlocks the signature feature** — photo→exercise (read a café menu, generate French exercises from it).

**Why not Cohere.** Command R+ (104B) and Command A (111B) exceed the 32B hackathon limit. Command R7B (7B) fits but is CC-BY-NC, which blocks the eventual commercial product. Cohere's API is a cloud dependency. It remains a *post-hackathon* commercial option (their French is genuinely top-tier, and they're Toronto-based — a nice Canadian-PR narrative), but not for the core.

**The eval (Day 7).** Rather than asserting a winner, we run a one-off Modal batch comparing **MiniCPM4.1-8B vs Lucie-7B vs Mistral-7B (and optionally Luth-1.7B)** on the user's *real* A1/A2 grammar tasks — correction, translation, dialogue naturalness, explanation clarity. The winner becomes the demo-deploy model on ZeroGPU. This produces genuine comparison numbers for the Field Notes post and a principled "here's why we chose X" story. Because all model calls go through `llm.py`, swapping the chosen model is a one-line change.

---

## 6. The two-deployment model

**Decision:** one codebase, two live deployments — Option B (reliable, always-on) and Option C (the demo showcase) — selected by an `LLM_BACKEND` env var.

- **Option B — model via API.** During development, the free OpenBMB API; as a fallback, HF `InferenceClient`. No GPU to manage, trivial to code against. This is the development workhorse and a reliability backstop.
- **Option C — model on ZeroGPU, in-Space.** The model runs inside the Space on a GPU that ZeroGPU lends only while a function executes. Free GPU minutes, no external rate limits, and it earns the "self-hosted" story. This is the **demo and submission** surface.

**The hard constraint that shaped this.** ZeroGPU is **exclusively compatible with the Gradio SDK** — Docker Spaces cannot schedule onto ZeroGPU. Therefore: local dev and Option B can be Docker; **Option C must be a Gradio-SDK Space, not Docker**. The resolution is elegant — the `@spaces.GPU` decorator is a no-op in non-ZeroGPU environments, so identical code runs locally (decorator does nothing) and on ZeroGPU (decorator requests a GPU). A tiny import shim keeps the code safe when the `spaces` package isn't installed.

**Operational notes.** Both API cold starts and ZeroGPU first-calls have a startup delay (10–60s); for the *recorded* demo, pre-warm with one throwaway call and keep a couple of cached example outputs. ZeroGPU as a standalone product needs HF PRO (~$9/mo); it's free via the hackathon org during the event.

---

## 7. Database architecture

**Decision:** Postgres from day one — a separate container locally via Docker Compose, Supabase (hosted Postgres) on the Space. No SQLite ladder.

**Why Postgres, not SQLite.** The product's analytics — "how many gender mistakes," "which concepts haven't been practiced recently," the daily summary aggregations — are one-line SQL queries in Postgres but fiddly hand-written loops over JSON otherwise. Starting on Postgres avoids a later migration. And Postgres handles document-style data natively via **JSONB**, so we get relational structure (typed columns for IDs, dates, categories) *and* flexible document storage (per-word annotations, exercise content) in one system — no separate NoSQL database needed.

**Why a separate db container.** If the app and database shared one container, rebuilding the app (which happens constantly) would also restart the database. Two containers isolate them: the frequently-rebuilt app never disturbs the database.

**Why a named volume.** Docker containers are disposable — their internal filesystem resets on rebuild. A named volume lives on the host disk; even if the db container is destroyed and recreated, Postgres reattaches and data survives. This directly answers "if the container fails, is my data gone?" — no.

**Why Supabase on the Space.** HF Spaces wipe non-persistent storage on restart, so a Space needs external persistence to keep notes and points. Supabase is hosted Postgres — the *same* database engine and schema as local, so the only thing that changes between environments is the `DATABASE_URL`. Free tier (500MB) is ample. On the Space, use Supabase's **connection pooler (port 6543)**, not the direct connection, so Gradio's concurrent requests don't exhaust Postgres connections.

**Hackathon-rules check.** Using Supabase does **not** violate any rule. The three rules are: model ≤32B, Gradio app, Space under the org. The only relevant *optional* badge (🔌 Off the Grid) refers to cloud *model* APIs, not databases. Persistence via Supabase is fully compatible.

---

## 8. Public vs private — the scope split and the moat

**Decision.** The public Space exposes its files (it's a public HF Space), so it ships only **non-novel, safe-to-expose features**. The novel adaptive engine stays **private** for the commercial build. Critically: **the moat is the intelligence, not the storage** — notes, exercises, and points *are* persisted in the public Space; what's withheld is the cross-lesson adaptive algorithm.

**Public (ships):** the notebook, the smart workspace (gender map + word cards), the chat coach, and practice generated **from the current lesson only** — text, dialogue, visual, pronunciation — plus the encouraging daily summary and points.

**Private (the moat, commercial only):** profile-wide weakness detection, a mastery map over time, an adaptive practice loop that recycles past mistakes across all lessons, full TEF/TCF exam simulation, CLB/NCLC tracking, a structured A1→B2 pathway, spaced repetition, and multi-user accounts.

**The line:** the public app generates practice from the lesson in front of you; *profile-wide adaptive customization* is the moat. The schema even defines the private tables (e.g., `mistakes`) but the public Space never writes to them.

---

## 9. Exercise design

Five exercise types, all generated from the current lesson, each chosen to be demoable and to lean on the deterministic/intelligent split:

1. **Text exercise** — the LLM generates one item (fill-in-the-blank, translation) from the lesson, with a model answer and explanation.
2. **Dialogue exercise** — the LLM writes a short scene dialogue using the lesson's vocab/grammar; the agent takes one role and *speaks* its lines via browser TTS; the user types or speaks their lines; the LLM gives encouraging feedback.
3. **A2 one-liner response** — the agent speaks a prompt line; the user composes a contextually appropriate one-liner reply; the LLM evaluates naturalness. This trains spontaneous production, not just recognition.
4. **Visual exercise (signature feature)** — the user uploads a real photo (café menu, street sign, recipe); MiniCPM-V 4.6 reads it; the LLM generates French exercises grounded in what's actually in the image. Nobody else will have this; "snap a photo of a Parisian menu, get instant French practice" is the standout demo moment and directly targets the OpenBMB prize.
5. **Pronunciation check** — TTS speaks a target line; the browser's Web Speech API captures the user's spoken answer (no ASR model needed); the transcription is shown; the LLM compares to the target and gives gentle correction.

**Audio strategy.** Browser-native `speechSynthesis` (TTS) and Web Speech API (ASR) keep the MVP free and dependency-light. Post-MVP upgrades are noted: VoxCPM2 or Nemotron TTS for higher-quality French audio, and Cohere Transcribe (runs on Apple Silicon via mlx-audio) or Nemotron ASR for accurate transcription.

---

## 10. Gamification design

**Decision.** A motivation layer that is **encouraging by design — never critical**. This is a hard product constraint, not a stylistic preference, because the user's context (solo, hard deadline, high stakes) makes anxiety the enemy of consistency.

**The daily summary** (LLM-generated from the database, shown on open) leads with gains ("you've covered 6 concepts and 48 words; you're solid on gender agreement and café vocabulary"), frames gaps as opportunities ("ready to practice next: passé composé"), and is warm, brief, and specific — one encouraging line, two or three concrete wins, one gentle "next." It never says "you're weak at," "you failed," or "you keep getting X wrong."

**Points are additive only.** The user earns points for *doing* — saving a lesson, completing an exercise, a dialogue turn, a pronunciation attempt, opening the app on a new day. Points are **never deducted**, and a wrong answer still earns participation points. Small named milestones ("First Dialogue," "Photo Explorer," "Week One") are framed as celebrations.

**Hard prohibitions** (enforced in both prompts and UI): no streak-loss guilt, no red error counters, no "you missed yesterday," no leaderboards-versus-others, no shaming copy. If the user is struggling, the tone softens further.

**Enforcement, not hope.** Encouraging tone is centralized in `prompts.py` so every feedback and summary prompt instructs constructive, forward-looking, one-fix-at-a-time language. The `points` table is append-only with a `CHECK (amount > 0)` constraint, making "never deduct" impossible to violate even by accident at the database level.

**Why it matters for the hackathon, too.** Beyond being humane, the daily summary and accumulating points are concrete evidence for the Backyard AI "the person actually used it" criterion — screenshots of summaries and point totals over the build week are proof of real, sustained use.

---

## 11. Hackathon strategy — tracks, badges, prizes

**Hard rules (all must hold):** model ≤32B; a Gradio app; hosted as a Space **under the `build-small-hackathon` org**; a demo video and social post at submission.

**Primary track: Backyard AI.** A real person (the user) with a real, specific problem, dogfooding daily.

**Badges targeted, by natural fit:**
- 🎨 **Off-Brand** — a custom French-themed Gradio frontend, not the default look (Day 8).
- 📓 **Field Notes** — a blog post on the model eval and what was learned (Day 9); this document is its seed.
- 🎯 **Well-Tuned** — *stretch*, only if Day-10 buffer allows: publish a small fine-tune to HF.
- 🔌 **Off the Grid** — *stretch*, post-submission: a fully-local variant running MiniCPM5-1B via MLX on the Mac (it has an Apple-Silicon build), no cloud calls.

**OpenBMB special prize ($2500/track).** "Built around MiniCPM" is a stated strength; using MiniCPM4.1-8B (text) and MiniCPM-V 4.6 (vision) as the core puts the project squarely in contention. Lead the demo and write-up with this.

**"More than a chatbot wrapper."** The gender map, photo→exercise, and spoken dialogue make it self-evidently not a chat wrapper — and the submission should say so explicitly, since the AMA flagged this as a strong-project signal.

---

## 12. Build methodology

**Iterative, one capability per day, on top of a working MVP.** Each day's session adds exactly one new runnable feature and keeps the app working. Two risks are de-risked early and deliberately: the **clickable interaction** is prototyped Day 1 in a clean environment before being ported into Gradio (it's the most likely thing to silently break), and **deployment** is proven Day 2 with mock data rather than left to the final day (the classic hackathon killer).

**Degrade gracefully.** The cut order if days slip is explicit: pronunciation → visual → dialogue → chat, with the gender-mapped notebook plus one text exercise as a complete Backyard-AI submission on its own. The daily summary is cheap and high-value, so it's kept if at all possible. Moat features are never built.

**Working rhythm.** One session equals one day's row in the build plan. The user tells Claude Code the day number; Claude Code implements that row only, keeps the app runnable, and commits with a message explaining the non-obvious "why" (the user is still learning the toolchain). Each day is verified against an explicit "expected outcome" before moving on. The user keeps a running note of surprises and decisions — which becomes the Field Notes post with no extra work.

---

## 13. Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| `gr.HTML` re-render breaks clickable words / injected JS | High | Prototype the interaction in a clean environment first (Day 1); use event delegation on a stable container; use Gradio 6's `js=` parameter pattern |
| LLM cold start ruins the live demo | Medium | Demo on ZeroGPU; pre-warm with a throwaway call before recording; cache a couple of example outputs |
| Small model gives flaky structured output per word | Medium | Keep gender/POS/lemma on deterministic spaCy; the model only does meaning/grammar |
| Scope creep eats the 1-hr/day budget | High | One feature per day; everything profile-wide is explicitly out of scope; plan degrades gracefully |
| Free OpenBMB endpoint changes or goes down | Medium | It's the dev backend; fall back to HF `InferenceClient`; final demo runs the eval-winner on ZeroGPU anyway |
| Data lost on container/Space restart | Medium | Named Docker volume locally; Supabase (with the pooler) on the Space |
| Encouraging-tone constraint violated by the model | Low–Medium | Tone enforced centrally in `prompts.py`; points ledger append-only with a positive-amount DB constraint |

---

## 14. Beyond the hackathon — the commercial roadmap

The public Space is a deliberately scoped slice of a larger product. Post-hackathon, on the user's own cloud (not the public Space), the commercial build adds the moat: profile-wide weakness detection and a mastery map that tracks strong/weak areas over time; an adaptive practice loop that recycles past mistakes across all lessons; full TEF/TCF exam simulation in the official timed format; CLB/NCLC progress tracking against a target; a structured A1→B2 pathway with daily targets calibrated to an exam date; spaced repetition; higher-quality audio (VoxCPM2/Nemotron TTS, Cohere/Nemotron ASR); and multi-user accounts. The same Postgres schema and `llm.py` abstraction carry forward — the commercial product is an expansion of this architecture, not a rewrite. For a commercial model, Cohere's Command R+/A (with a paid license) becomes a viable French-strong option.

---

*End of document. This plan and `CLAUDE.md` together constitute the project's full design record.*
