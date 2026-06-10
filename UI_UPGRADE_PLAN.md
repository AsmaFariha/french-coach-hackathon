# French Coach — UI Upgrade via gr.Server (Fail-Safe Plan for Claude Code)

> Goal: replace the default Gradio look with a polished custom React frontend,
> served through Gradio's gr.Server, WITHOUT losing the working app and WITHOUT
> breaking hackathon eligibility. Every phase ends with a runnable app and a
> committed checkpoint, so any failure rolls back in under 3 minutes.

---

## CONSTRAINT: keep hackathon eligibility (read first, do not skip)

The hackathon requires: a Gradio app, model <= 32B, hosted as a Gradio-SDK Space
under the build-small-hackathon org. Therefore:

- The submitted Space MUST run on the Gradio SDK (NOT a Docker Space). gr.Server /
  a custom frontend is allowed AS LONG AS it is launched from a Gradio app object
  (the Space entrypoint is still `app.py` running Gradio).
- Do NOT split this into a separately-hosted React site + a headless API. The
  React build must be SERVED BY the Gradio app (mounted as static assets / custom
  frontend on the same Gradio server), so the Space remains a Gradio app.
- If at any point the only way to ship the custom UI is a non-Gradio host, STOP
  and flag it — we fall back to the themed Blocks UI (Phase 0) instead. The badge
  is "best custom UI pushing past the default Gradio look" — themed Blocks still
  qualifies; losing Gradio-SDK hosting does not.

Net rule: custom UI = yes; leaving the Gradio SDK = no.

---

## Branching & rollback model (the fail-safe spine)

- `main` = the current working Blocks app. It is never edited during this work.
- `feature/custom-ui` = all UI-upgrade work happens here.
- Every phase = one commit on the branch. If a phase fails, reset to the last
  good commit; the app from the previous phase still runs.
- The old Blocks app (`app.py`) is NOT deleted at any point. The new frontend is
  additive. Only in the final phase, after the new UI is verified, do we switch
  the Space entrypoint — and even then `app.py` stays in the repo as fallback.

Rollback command (memorize):
```
git checkout main && docker compose down && docker compose up -d
```
That restores the working app on the original port within minutes.

---

## PHASE 0 — Safety net + cheap win (do this before any gr.Server work)

Purpose: guarantee a rollback point AND bank a "looks custom" result even if every
later phase fails.

Tasks:
1. Commit any uncommitted work on `main`. Confirm `git status` is clean.
2. Create and push the work branch:
   `git checkout -b feature/custom-ui && git push -u origin feature/custom-ui`
3. On the branch, apply a custom theme + CSS to the EXISTING Blocks app (custom
   French palette, header, fonts, card spacing). This alone can earn the Off-Brand
   badge and is the fallback if gr.Server work is abandoned.
4. Verify app still runs on the normal port. Commit:
   "Phase 0: branch + themed Blocks UI (fallback that already beats default look)"

Checkpoint test: app loads, all existing tabs work, looks visibly custom.
DO NOT PROCEED until this passes.

---

## PHASE 1 — Prove gr.Server can mount a custom page (smallest slice)

Purpose: de-risk the whole approach with the smallest possible custom-frontend
test before investing in a full React build.

Tasks:
1. Read the gr.Server / custom-frontend docs referenced for this hackathon and
   confirm the supported way to serve custom static frontend assets from a Gradio
   app object (so the Space stays a Gradio app). If the exact API differs from
   assumptions here, follow the docs and note the difference in the commit msg.
2. Create a NEW entrypoint `app_custom.py` (do NOT touch `app.py`). It should:
   - import the existing backend functions (LLM, db, exercises, gamify) unchanged
   - expose them as callable endpoints via the Gradio app object
   - serve ONE minimal custom HTML page (a hello-world that calls ONE backend
     function, e.g. "generate one exercise", and renders the result)
3. Run it on a SEPARATE port (e.g. 7861) so the old app on its original port is
   untouched and still usable side by side.
4. Verify the custom page calls the backend and shows a real result.
5. Commit: "Phase 1: gr.Server custom entrypoint (app_custom.py) on port 7861,
   one endpoint proven"

Checkpoint test: old app still runs on its port; new custom page on 7861 returns
a real exercise from the backend. If you cannot serve a custom frontend from the
Gradio app object per the docs, STOP and flag — we stay on Phase 0.

---

## PHASE 2 — Frontend skeleton + backend contract

Purpose: lock the data contract between frontend and backend before building all
screens, so screens can be added without rework.

Tasks:
1. Create `frontend/` (React + Vite, plain and minimal — no heavy UI kit).
2. Define a small, explicit API contract: list every backend call the UI needs
   (list lessons, load lesson, save lesson, annotate, word card, chat, generate
   exercises, summary, points) with input/output JSON shapes. Write it to
   `frontend/API_CONTRACT.md`.
3. Implement those endpoints on the Gradio app object in `app_custom.py` so each
   one returns the JSON shape in the contract.
4. Build the React shell only: header, tab/nav layout, routing between empty
   screens. No real screens yet. Wire ONE call (list lessons) end to end to prove
   the build pipeline (vite build -> served by Gradio) works.
5. Build the frontend to static assets and confirm Gradio serves the built assets
   (not the dev server) so this matches how the Space will run.
6. Commit: "Phase 2: React shell + API contract + lessons list wired through
   built assets"

Checkpoint test: visiting the custom entrypoint shows the React shell served by
Gradio (production build, not dev server), and the lessons list loads from the DB.

---

## PHASE 3 — Port screens one at a time (each is its own commit)

Purpose: migrate features incrementally; the app is always runnable, and any
single screen failing never blocks the others.

Order (each = test + commit before the next):
1. Notebook (load/edit/save lesson, gender coloring, word card, TTS)
2. Lessons browser (cards, categories, click-to-open)
3. Exercises (the Coach Agent set + answer feedback)
4. Chat coach
5. Summary dashboard (progress + points)
6. Gender Checker + Translator

For EACH screen:
- Build the React screen against the contracted endpoints.
- Verify it matches or beats the old Blocks version's behavior.
- Commit: "Phase 3.N: <screen> ported to custom UI".
- If a screen proves too costly, leave the user on the themed Blocks tab for that
  one feature and move on — do not sink the whole sprint into one screen.

Checkpoint test after each: that screen works end to end; previously-ported
screens still work.

---

## PHASE 4 — Polish pass

Tasks:
1. Visual polish: palette, typography, spacing, hover/transition states, loading
   states, empty states, mobile width.
2. Keep encouraging-tone rules intact (no red error states, additive points only).
3. Commit: "Phase 4: visual polish pass on custom UI".

Checkpoint test: full click-through of every screen feels cohesive and intentional.

---

## PHASE 5 — Make the custom UI the Space entrypoint (eligibility-safe switch)

Purpose: ship the custom UI as the Gradio Space WITHOUT losing the Gradio SDK
requirement or the fallback.

Tasks:
1. Ensure the Space entrypoint runs the Gradio app object that serves the built
   React assets (still a Gradio SDK Space). Confirm README Space metadata declares
   the Gradio SDK.
2. Keep `app.py` (themed Blocks) in the repo as the documented fallback. Add a
   one-line note in README on how to revert the entrypoint if the custom UI fails
   on the Space.
3. Set the frontend build to run as part of the Space build (so the Space serves
   the production assets, not a dev server).
4. Confirm model stays <= 32B and the deploy LLM path (ZeroGPU/MiniCPM) is intact.
5. Commit: "Phase 5: custom UI is the Gradio Space entrypoint; Blocks kept as
   fallback".

Checkpoint test: a fresh `docker compose up` (or the Space build steps) serves the
custom UI from the Gradio app, all screens work, eligibility constraints all hold.

---

## Merge / abandon decision

- If Phases 1–5 all pass: merge `feature/custom-ui` into `main`.
- If gr.Server is blocked at Phase 1, or screens stall in Phase 3 with the
  deadline close: ship Phase 0 (themed Blocks) from `main`. That already pushes
  past the default look and keeps full eligibility. Abandoning the branch costs
  nothing because `main` was never touched.

Hard deadline rule: stop new UI work with at least one full day of buffer before
June 15 for demo recording and submission, regardless of which phase you are in.

---

## What to hand Claude Code

One phase per session. Start each session with:

"Read CLAUDE.md and UI_UPGRADE_PLAN.md fully. Do PHASE N exactly as written,
including its checkpoint test. Do not edit app.py except where the plan explicitly
says so. Do not leave the Gradio SDK. End by committing with the message given for
that phase, and tell me the checkpoint test result. If anything in the plan is
blocked or would break hackathon eligibility, STOP and flag it instead of changing
scope."

Begin with: "Do PHASE 0."
