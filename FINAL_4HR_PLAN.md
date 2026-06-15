# French Coach — Final 4-Hour Deploy + Submit Plan (SELF-HOST primary)

> Deadline June 15 23:59 UTC (= 19:59 America/Toronto). ~4 hours left.
> Decisions locked by user: SELF-HOST the LLM in-Space (non-negotiable);
> HF auth gets a 15-MINUTE timebox then revert. Get a LIVE, ELIGIBLE submission.

Time budget (hard caps):
  Block 0  ZeroGPU gate check ....................... 5 min   (DECIDES EVERYTHING)
  Block A  Self-host models live on org Space ....... 110 min
  Block B  README tags + demo video + social post ... 55 min
  Block C  HF auth (15-min timebox) + seed lessons .. 25 min
  Block D  Eligibility sweep + SUBMIT ............... 25 min
  If Block A overruns: flip text to API (break-glass), keep moving. Never skip D.

---

## BLOCK 0 — ZeroGPU gate (do this FIRST, 5 min)

Self-hosting MiniCPM4.1-8B needs a real GPU = ZeroGPU = requires PRO or Enterprise.
Action: start creating a Space under build-small-hackathon, SDK = Gradio, look at the
Hardware dropdown.
  - ZeroGPU PRESENT  -> proceed to Block A self-host path.
  - ZeroGPU ABSENT   -> enable personal PRO now (only way to self-host the 8B), OR if
    you will not enable PRO, you CANNOT self-host the 8B in time -> use break-glass
    (text via Qwen HF Inference API) and treat self-host as post-hackathon. Tell user.
Vision (MiniCPM-V 4.6, 1.3B) can also run on this ZeroGPU Space, OR via its free
OpenBMB API — either keeps the MiniCPM story.

---

## Secrets (Space Settings -> Secrets only; never in code)

HF_TOKEN; DATABASE_URL (Supabase pooler 6543); LLM_BACKEND=zerogpu;
USE_FINETUNED_EXERCISES=false; (vision API base/key if vision via API).
.env stays gitignored. Public users see only the running app.

---

## What to push to the Space (KEEP IT CLEAN — user requirement)

Push ONLY what the app needs to run. Do NOT upload internal planning/strategy docs.

EXCLUDE from the Space (add to a Space-specific .gitignore or simply do not commit them):
  CLAUDE.md, DEVLOG.md, LLM_USAGE.md, COACH_AGENT.md, API_CONTRACT.md (if internal),
  and ALL *_PLAN.md files: FIVE_DAY_PLAN.md, ENHANCED_DEVELOPMENT_PLAN*.md,
  UI_UPGRADE_PLAN.md, FINETUNE_PLAN.md, DEPLOY_PLAN.md, SUBMISSION_DEPLOY_PLAN.md,
  FINAL_4HR_PLAN.md, BASH_COMMANDS.md, docs/ , and the .env file.
  Reason: these expose internal strategy + the private/commercial-moat plans and are
  clutter on a public Space. They must NOT be publicly visible.

KEEP (must ship, app needs them):
  app_custom.py (+ app.py if used), llm.py, exercises.py, nlp.py, db.py, notebook.py,
  curator.py, gamify.py, prompts.py, models.py, syllabus_full_a1_c2.json,
  seed_texts/ (only the lesson text actually used to seed), the built frontend assets,
  requirements.txt, packages.txt (if needed), and README.md.
  README.md MUST ship — it carries the REQ-06 YAML tags + write-up.

Push method (repo is code-only; weights are NOT pushed — transformers fetches them on
the Space at runtime):
  - Plain git is sufficient: add the Space as a remote and push the cleaned tree.
    e.g. `git remote add space https://huggingface.co/spaces/build-small-hackathon/<name>`
         `git push space <branch>:main`
  - HF CLI is optional (only helpful for auth convenience / git-lfs). If model or asset
    files ever exceed git limits, use git-lfs. For this code-only push, not required.
  - Easiest clean approach: keep the Space as its OWN repo/remote and commit only the
    KEEP list to it, so the planning docs never enter the Space history at all.

## BLOCK A — Self-host live (110 min)  [feature/deploy; main untouched]

A1. Create the public Gradio Space under build-small-hackathon, SDK = Gradio,
    hardware = ZeroGPU. Set sdk_version in README metadata.
A2. Push the real app (gr.Server entrypoint serving the React build + llm.py /
    exercises.py / db.py / gamify.py / syllabus json + built frontend).
A3. llm.py zerogpu path — SELF-HOST MiniCPM4.1-8B via transformers:
    - load model on cuda at MODULE level (root), even though GPU is only live inside
      the decorated fn (ZeroGPU requirement).
    - wrap generate in @spaces.GPU(duration=120) (lower if you can for queue priority).
    - bound max_new_tokens; keep generations short so cold calls finish in budget.
    - VISION: MiniCPM-V 4.6 — self-host on the same Space if memory allows, else its
      free OpenBMB API (faster to ship). Either is fine.
A4. Secrets set; DATABASE_URL -> Supabase pooler 6543; connection-per-request.
    If Supabase empty, run the existing lesson import once so there's real content.
A5. PRE-WARM (critical for self-host): after build, fire one text + one vision call so
    weights load before any judge visits (first call is the slow one).
A6. Verify the full journey LIVE: notebook -> lessons -> gender colors -> word card ->
    save (curator title) -> chat -> Coach Agent set -> visual exercise -> summary.
    Fix only what breaks; add nothing.
Commit: "Deploy: self-hosted MiniCPM4.1-8B (+MiniCPM-V) live on org ZeroGPU Space".
CHECKPOINT: cold visitor can use every feature; first-call latency acceptable after prewarm.

BREAK-GLASS (only if self-host is still failing with < ~70 min left): set
LLM_BACKEND so text calls Qwen2.5-7B via HF Inference API; keep MiniCPM-V for vision.
App goes live immediately. Note honestly in README. A live API app beats a broken
self-host. Self-host remains the goal; the deadline is the hard constraint.

---

## BLOCK B — Submission artifacts (55 min; overlap A5/A6)

B1. README YAML tags + write-up (REQ-06) FIRST — gating + cheap:
    - tags block at TOP: track + badges (Backyard AI; Best MiniCPM Build; Off-Brand;
      Best Agent; Best Demo; Bonus Quest). EXACT strings from the field guide's
      "Validate README" tool — do not guess. RUN Validate README; fix flags.
    - write-up: idea (living French notebook + Coach Agent for a real TEF/TCF learner);
      tech (Coach Agent plan->generate->critique->revise; SELF-HOSTED MiniCPM4.1-8B
      text + MiniCPM-V vision on ZeroGPU; Gradio Server custom UI; Supabase).
      [If break-glass was used, say text = Qwen API instead — be accurate.]
B2. Demo video (REQ-03) ~2 min, show it WORKING (judges use it if a live run rate-
    limits): lead with the Coach Agent loop + a visual exercise; name the models out
    loud; show points/summary as Backyard-AI real-use evidence. Upload public; link it.
B3. Social post (REQ-04): one public post; link the Space; put the post link in README.
Commit: "Submission: README tags+writeup, demo + post linked".

---

## BLOCK C — HF auth (15-MIN TIMEBOX) + seed 5 lessons (25 min total; CUTTABLE)

> Only if Block A live + Block B done. HF auth is NOT an eligibility rule.
C1. HF OAuth login (TRY THIS — user wants per-user login): add Gradio's HF Sign-In /
    HF OAuth so visitors log in with their Hugging Face account; on login use the HF
    username as user_id (replace
    dev_user) so each visitor gets their own notebook/points.
    *** 15-MINUTE TIMEBOX: if not working cleanly in 15 min, REVERT to shared user_id
    and move on. Do not risk the submission for login. ***
C2. Seed 5 starter lessons for a new user on first visit (idempotent: only if they have
    0 pages): Pronunciation, Articles, Months & Seasons, Adjectives, Present-simple
    verbs. REUSE existing lesson text (Notion/seed_texts) — write no new content.
Commit: "Add HF login (timeboxed) + seed 5 starter lessons per new user".

---

## BLOCK D — Eligibility sweep + SUBMIT (25 min; NEVER skip)

PASS/FAIL each; fix FAILs:
  REQ-01 models <=32B (MiniCPM4.1-8B, MiniCPM-V 1.3B) ......
  REQ-02 Gradio Space under build-small-hackathon, public ..
  REQ-03 demo video linked .................................
  REQ-04 social post linked ................................
  REQ-05 <=10 ZeroGPU spaces ...............................
  REQ-06 README tags + writeup; Validate README passes .....
  secrets only in Space settings ...........................
Complete the field-guide submission step (tags are the mechanism; confirm the Space is
registered/visible). DONE.

---

## Triage if time collapses
1. Always finish Block A (live, self-host OR break-glass) + Block D (tags+submit).
2. Block B: if no 2-min video, record 60 sec of the Coach Agent working.
3. Block C: skip without guilt.

## Hand to Claude Code
"Read CLAUDE.md, LLM_USAGE.md, COACH_AGENT.md, FINAL_4HR_PLAN.md. Do BLOCK 0 first and
report whether ZeroGPU is selectable. Then BLOCK A: self-host MiniCPM4.1-8B in-Space
(module-level cuda, @spaces.GPU, prewarm); vision via MiniCPM-V (self-host or its API);
secrets only in Space settings; change no features. If self-host is still failing with
under ~70 min left, use the documented break-glass (Qwen text API) so the app goes live.
Stop at the Block A checkpoint and report the full-journey result. For HF auth (Block C), TRY HF OAuth / HF Sign-In so each user logs in with their
Hugging Face account; hard-stop at 15 minutes and revert to shared user_id if it is
not working cleanly. Also: push ONLY the KEEP list to the Space — never the planning
.md files, docs/, or .env (see 'What to push to the Space')."
