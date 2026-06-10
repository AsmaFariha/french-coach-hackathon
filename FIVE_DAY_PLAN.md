# French Coach — 5-Day Final Sprint (June 9–13, submit by June 15)

> Reality check: 6 days remain. This plan uses 5 build days (Jun 9–13) and leaves
> Jun 14–15 for buffer, demo recording, and submission. One genuine agent (the
> Coach Agent) is the brain that makes the whole app feel smart. Everything else
> is scoped to be low-risk and always-runnable.

---

## The hero agent: Coach Agent (plan → generate → critique → revise)

A real agent, not a chatbot wrapper. Given the current lesson, it:

1. PLAN — reads the lesson, identifies the CEFR concepts it teaches (grounded
   against syllabus.json), and decides a balanced mix of exercise types +
   difficulty appropriate to the content.
2. GENERATE — produces each exercise in the planned set.
3. CRITIQUE — a verification pass checks each item: is the answer correct? is
   there exactly one unambiguous answer? are MC distractors plausible-but-wrong?
   right level?
4. REVISE — regenerates any item that fails (bounded retries; never loops forever).
5. RETURN — a validated set of 5–10 mixed exercises.

Cohesion: the concepts it identifies are written to the DB and power the Summary
tab's "strengths" + "next focus." One brain, felt across Exercises, Summary, and
the lesson browser.

Why it's defensible to judges: self-critique + revise loop, grounded in the
learner's own notes + CEFR scope = "more than a chatbot wrapper."

---

## Day 1 (Jun 9) — Foundation: make what already exists actually work

Nothing LLM-powered works right now because the OpenBMB key is dead. Fix that first.

Tasks:
1. Wire llm.py to HF Inference API via huggingface_hub InferenceClient.
   - Model via env var (try openbmb/MiniCPM4.1-8B-Instruct; if it is not warm on
     the free tier, fall back to an available served instruct model so dev is
     unblocked). Keep a graceful mock fallback so the UI degrades, never crashes.
   - Keep a zerogpu code path (the @spaces.GPU shim) for the deploy target so
     MiniCPM runs in-Space later (preserves the OpenBMB-prize story + Off the Grid).
2. Fix the broken core wiring:
   - Word card: clicking a word fetches LLM meaning + grammar note (cache per lemma).
   - Load saved page: selecting a lesson in the sidebar loads it into the editor.
   - Chat coach: returns a real streamed answer instead of "Error".
3. Verify end-to-end, commit.

Outcome: every currently-visible feature works. App is a credible base again.
Commit: "Day 1: HF Inference backend + fix word card, page load, chat"

---

## Day 2 (Jun 2) — Smart lesson organization + browsing

Tasks:
1. Curator pass (one LLM call per lesson, cached in pages.metadata JSONB):
   auto-title, category (map to a CEFR family), and a 1-line summary.
   Backfill the existing 15+ lessons once.
2. Notebook left sidebar: browse by Date and by Topic (collapsible), search box,
   click a lesson to load it into the editor.
3. New "Lessons" tab: card grid (title, date, category badge, 1-line summary);
   click a card to open that lesson in the Notebook tab.

Outcome: your saved notes are browsable, named, categorized, and summarized.
Commit: "Day 2: lesson curator (title/category/summary) + sidebar + Lessons tab"

---

## Day 3 (Jun 11) — The Coach Agent + Exercises tab

Tasks:
1. Implement the Coach Agent in exercises.py as the plan→generate→critique→revise
   loop described above. Bounded retries (e.g., max 2 per item).
2. Exercise types in the mix: fill-in-the-blank, multiple choice, error detection,
   reordering, short translation. 5–10 per lesson.
3. Write identified concepts to the DB (link lesson -> concepts) for the Summary tab.
4. Exercises tab UI: show the set one at a time, immediate ENCOURAGING feedback,
   award additive points. No red error states, no shaming copy.

Outcome: the smart centerpiece. Finish a lesson, get a validated, balanced set.
Commit: "Day 3: Coach Agent generates self-checked 5–10 mixed exercises"

---

## Day 4 (Jun 12) — Visual exercises + pronunciation playback

Tasks:
1. Visual exercises (pragmatic scope):
   - Ship a pre-generated image set (~15–20 images) keyed by topic as static assets.
     (Generated once via an HF Inference text-to-image model in a one-off script;
     no image model runs on the laptop or in the app at request time.)
   - Match an image to the current lesson's topic; track which images a user has
     seen (user_image_usage) so they are not repeated.
   - Coach Agent builds 3–5 French questions + hints grounded in the chosen image.
2. Pronunciation: make TTS playback reliable for word cards and selected text
   (browser speechSynthesis). Mic capture (Web Speech API) is best-effort; if it
   fails, fall back to "type what you heard" + LLM gentle feedback.

Outcome: a visually compelling, demoable exercise type + working "hear it" audio.
Commit: "Day 4: matched-image visual exercises + reliable TTS playback"

Stretch (only if ahead): background top-up generation for brand-new topics.

---

## Day 5 (Jun 13) — Tools, Summary dashboard, polish, deploy

Tasks:
1. Gender Checker tab: type a noun -> gender, le/la, un/une, example, pattern note.
2. Translator tab: EN<->FR with optional context, alternatives, a usage example.
3. Summary dashboard: today's lessons/exercises/points, strengths + next-focus
   (driven by the concepts the Coach Agent recorded), a simple progress chart,
   encouraging LLM-written recap. Additive points only; no streak guilt.
4. Custom French-themed UI polish (colors, type, spacing).
5. Deploy to a Gradio-SDK Space under build-small-hackathon with LLM_BACKEND=zerogpu
   so MiniCPM runs in-Space (Off the Grid). Pre-warm. Confirm it loads.

Outcome: cohesive, smart, polished, deployed. Ready to record + submit.
Commit: "Day 5: Gender + Translator tabs, Summary dashboard, polish, ZeroGPU deploy"

Jun 14–15: record 2-min demo (lead with the Coach Agent + visual exercises +
built-around-MiniCPM), write the social post + Field Notes draft, submit.

---

## Cut to stretch (do NOT block the sprint on these)
- Full Notion-grade rich-text editor + inline floating toolbar (Gender/Translator
  tabs cover the need at far lower risk).
- Continuous auto image-generation agent (ship the pre-generated set instead).
- Microphone ASR (TTS playback + type-what-you-heard is the reliable path).

## If a day slips, cut in this order
pronunciation mic -> visual auto-topup -> Translator tab -> rich editor.
Never cut: Day 1 foundation, the Coach Agent (Day 3), the Summary cohesion.

---

## How to drive Claude Code (one session per day)

Open Claude Code in the repo, then paste the day's prompt:

"Read CLAUDE.md and FIVE_DAY_PLAN.md fully. We are on Day N. Implement Day N
exactly as written there: [paste that day's Tasks]. Keep the app runnable, test
each task before moving on, explain non-obvious choices, and commit with the
message given for that day. If something in the plan is not feasible, stop and
flag it rather than silently changing scope."
