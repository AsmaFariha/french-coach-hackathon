# The Coach Agent: architecture overview

> Implemented Sprint Day 3 (2026-06-10). See [DEVLOG.md](../DEVLOG.md#sprint-day-3--2026-06-10--coach-agent-generates-self-checked-mixed-exercises) for the build log.

The core idea is a single function, [`generate_exercise_set()`](../exercises.py#L112-146), that turns the *current lesson's text* into a validated set of 5-7 mixed exercises. It runs a **plan → generate → critique → revise → return** loop — a small multi-step agent rather than one big LLM call.

## Why this shape?

A single "give me 5 exercises" prompt tends to produce repetitive types, exercises with no exact answer, or multiple-choice options where two answers could both be "correct." Splitting into stages lets each stage do one job well, and lets a later stage catch the earlier stage's mistakes.

## The four stages

**1. PLAN** — [`COACH_PLAN_SYSTEM`](../prompts.py#L80-106)
The LLM reads the lesson text plus a "menu" of A1/A2 CEFR concepts (from `syllabus_full_a1_c2.json`, loaded via [`_load_a1_a2_concepts()`](../exercises.py#L98-109)). It returns:
- `concepts`: 1-4 concept IDs from that menu that this lesson teaches/reinforces (must be real IDs — never invented)
- `plan`: 5-7 items, each `{type, focus}` — a mix of `fill_blank`, `multiple_choice`, `error_detection`, `reorder`, `translation`, varied so the same type doesn't repeat back-to-back

This is the "grounding" step — it ties the exercise set to both *this specific lesson* and the *official syllabus*, without ever inventing concepts that don't exist.

**2. GENERATE** — [`COACH_EXERCISE_SYSTEM`](../prompts.py#L109-137)
For each planned item, a separate LLM call produces the actual exercise — full JSON shape per type (e.g. multiple_choice needs exactly 4 options with the answer matching one verbatim).

**3. CRITIQUE** — [`COACH_CRITIQUE_SYSTEM`](../prompts.py#L140-156)
A second LLM call acts as a reviewer on the just-generated item: is the answer actually correct, is there exactly one unambiguous answer, are MC distractors plausible-but-wrong, does reorder's `answer` use exactly the given `words`, is it A1-A2 level? Returns `{valid, issue}`.

**4. REVISE** — [`_generate_and_critique()`](../exercises.py#L149-168)
If `valid: false`, the `issue` text is fed back into a second GENERATE attempt as a `revise_note` ("a reviewer flagged... please fix this"). **Bounded to 2 attempts max** — after that, whatever was last generated is accepted as-is. This guarantees the loop always terminates (degrade gracefully).

## Putting it together

```
generate_exercise_set(lesson_text)
  ├─ PLAN (1 LLM call) ──────► concepts[], plan[7 items]
  ├─ for each planned item:
  │    └─ _generate_and_critique() ─► up to 2× (GENERATE + CRITIQUE)
  ├─ _mark_concepts_covered(concepts) ──► UPSERT into `concepts` table, covered_on=today
  └─ return {concepts, exercises}
```

So worst case ~15 LLM calls (1 plan + 7×2), but in practice most items pass critique on the first try (~18s for the whole set in testing).

## Grading (the "Check" step)

[`check_coach_exercise()`](../exercises.py#L186-208) splits into two strategies:
- `fill_blank` / `multiple_choice` — deterministic case-insensitive exact match (cheap, and the critique step already guaranteed a single unambiguous answer)
- `error_detection` / `reorder` / `translation` — free-text, so a lenient LLM grader ([`COACH_CHECK_SYSTEM`](../prompts.py#L159-187)) accepts spelling/accent/punctuation variation and gives 2-3 sentences of feedback that never uses shaming words

Either way, `gamify.add_points(user_id, "exercise_done")` always fires — points are participation signals, never tied to correctness.

## Feedback loop into the Summary tab

`_mark_concepts_covered()` writes to the `concepts` table, and [`gamify.get_concepts_progress()`](../gamify.py#L108-120) reads it back: "covered" (concept names already marked) and "next" (first A1/A2 concept in syllabus order not yet covered). The daily summary prompt then names covered concepts as strengths and suggests the "next" one — closing the loop from "what did the coach just teach you" to "here's your daily encouragement."

## Frontend

The `🧠 Coach` subtab (`CoachExercises` in [Exercises.jsx](../frontend/src/screens/Exercises.jsx)) calls `/api/exercises/coach` once, then walks through `exercises[]` one item at a time — type-specific UI (option buttons for MC, draggable word-chips for reorder, text input otherwise), immediate blue/green feedback card, and a "Next" button. No red states anywhere.

## API

See [API_CONTRACT.md](../frontend/API_CONTRACT.md) for the full request/response shapes of `POST /api/exercises/coach` and `POST /api/exercises/coach/check`.
