# French Coach — Custom UI API contract

All endpoints are mounted on the same Gradio app object (`gr.Server` /
FastAPI instance) returned by `demo.launch(prevent_thread_lock=True)` in
`app_custom.py`, under the `/api/...` prefix. The built React app
(`frontend/dist`) is served as static assets from the same server, so the
whole thing is one Gradio-SDK process (no separate API host).

User identity: single-user dev mode. Every endpoint operates on a fixed
`USER_ID = "dev_user"` (same default `app.py` uses when not running on a
Space). Hugging Face OAuth for the custom UI on the public Space is **not**
wired up yet — flagged as a follow-up, not a blocker (does not affect
Gradio-SDK / model-size eligibility).

All responses are JSON unless noted. Errors: `{"error": "<message>"}` with a
non-200 status code.

---

## Lessons (Notebook + Lessons browser)

### `GET /api/lessons`
List saved lesson pages (excludes `page_type == "resource"`), newest first.

Response:
```json
{
  "lessons": [
    {"id": "uuid", "title": "Class 4 — Le passé composé", "date": "2026-04-30",
     "category": "Grammar", "page_type": "lesson", "preview": "Aujourd'hui on a vu…"}
  ]
}
```

### `GET /api/lessons/{id}`
Load one page for editing.

Response:
```json
{"id": "uuid", "title": "Class 4", "raw_text": "Le petit chat...",
 "annotations": {"tokens": [...], "meanings": {...}}}
```
404 -> `{"error": "not found"}` if missing or not owned by user.

### `POST /api/lessons`
Save the current editor text as a **new** page (curator auto-titles it).
Awards `saved_lesson` points.

Body: `{"text": "...", "annotations": {...}}`
Response: `{"id": "uuid", "title": "Auto-generated title"}`

### `PUT /api/lessons/{id}`
Update an existing page's text/annotations in place (title unchanged).

Body: `{"text": "...", "annotations": {...}}`
Response: `{"title": "Existing title"}`

### `PATCH /api/lessons/{id}/title`
Rename a page (user override of the auto title).

Body: `{"title": "New title"}`
Response: `{"title": "New title"}`

### `DELETE /api/lessons/{id}`
Delete a page (exercises cascade).

Response: `{"deleted": true}`

---

## Resources tab

### `GET /api/resources`
Pages curated as `page_type == "resource"` that contain links and/or books.

Response:
```json
{
  "resources": [
    {"id": "uuid", "title": "Online Resources",
     "links": [{"url": "https://...", "label": "TV5 Monde", "domain": "tv5monde.com"}],
     "books": [{"title": "Le Petit Prince", "author": "Saint-Exupéry", "note": "easy reader"}]}
  ]
}
```

---

## Annotation / gender coloring / word card (Notebook + Tools screens)

### `POST /api/annotate`
Run spaCy annotation on arbitrary text (used by Notebook "Annotate" and the
Gender Checker tool).

Body: `{"text": "...", "colors_on": true}`
Response:
```json
{"html": "<span data-token=\"1\" data-gender=\"Masc\" ...>Le</span> ...",
 "tokens": [{"text": "Le", "lemma": "le", "pos": "DET", "gender": "Masc", "whitespace": " "}],
 "meanings": {}}
```
`html` is the same gender-colored markup `nlp.render_html` already produces
(with `data-token`/`data-text`/`data-gender`/`data-pos`/`data-lemma`
attributes) — the React Notebook/Tools screens render it with
`dangerouslySetInnerHTML` and use click-event delegation, exactly like the
existing Blocks `PAGE_JS`, so gender colors + click behavior stay identical.

### `POST /api/render`
Re-render cached annotations to gender-colored HTML without re-running
spaCy/LLM (used when loading a saved lesson, or toggling the gender-colors
checkbox, so cached `meanings` survive).

Body: `{"annotations": {"tokens": [...], "meanings": {...}}, "colors_on": true}`
Response: `{"html": "<span data-token=...>...</span> ..."}`

### `POST /api/word-card`
Get (and cache) the LLM meaning/grammar note for one clicked word. Awards
`word_explored` points the first time a given lemma is looked up.

Body:
```json
{"text": "femme", "lemma": "femme", "pos": "NOUN", "gender": "Fem",
 "meanings": {"...cached meanings dict from annotate/lessons..."}}
```
Response:
```json
{"text": "femme", "lemma": "femme", "pos": "NOUN", "gender": "Fem",
 "meaning": "woman", "grammar": "feminine noun",
 "meanings": {"femme": {"meaning": "woman", "grammar": "feminine noun"}, "...": "..."}}
```
The client merges the returned `meanings` dict back into its local
annotations object (so a later "Save"/"Update" persists the cache).

---

## Chat coach

### `POST /api/chat`
Non-streaming reply (the custom UI does one round trip per message instead
of token-streaming).

Body:
```json
{"message": "Comment dit-on 'thank you'?",
 "history": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}],
 "lesson_text": "...current notebook text, used as context, optional..."}
```
Response: `{"reply": "On dit « merci »..."}`

---

## Exercises

### `POST /api/exercises/text`
Generate one fill-in-the-blank exercise from the current lesson.

Body: `{"lesson_text": "..."}`
Response:
```json
{"exercise": {"instruction": "Fill in the blank:",
  "sentence_with_blank": "La ____ mange une pomme.",
  "answer": "femme", "hint": "...", "explanation": "..."},
 "html": "<div ...>...</div>"}
```
`html` = `exercises.render_text_exercise(exercise)` (existing styled markup).

### `POST /api/exercises/text/check`
Body: `{"exercise": {...}, "answer": "femme"}`
Awards `exercise_done` points (always — participation, not correctness).
Response: `{"correct": true, "html": "<div ...>...</div>"}`

### `POST /api/exercises/dialogue`
Start a new dialogue scene from the lesson.

Body: `{"lesson_text": "..."}`
Response:
```json
{"dialogue": {"scene": "...", "agent_role": "...", "user_role": "...", "turns": [...]},
 "replies": [], "hint": "Your turn: ...", "transcript_html": "<div ...>...</div>"}
```

### `POST /api/exercises/dialogue/reply`
Send the user's next line. Awards `dialogue_turn` points.

Body: `{"dialogue": {...}, "replies": ["..."], "reply": "Bonjour !"}`
Response:
```json
{"replies": ["Bonjour !"], "transcript_html": "<div ...>...</div>",
 "hint": "Your turn: ..." , "feedback_html": "<div ...>...</div>"}
```
(`hint` is `"🎉 Dialogue complete! Great work!"` once finished.)

### `POST /api/exercises/visual`
Multipart form upload. Awards `photo_exercise` points.

Form field: `image` (file, jpeg/png)
Response: `{"html": "<div ...>...</div>"}`
(`html` = `exercises.render_visual_exercises(result)`, includes an `error`
case if the image can't be read.)

### `POST /api/exercises/pronunciation/target`
Body: `{"lesson_text": "..."}`
Response:
```json
{"target": {"phrase": "...", "translation": "...", "tip": "..."}, "html": "<div ...>...</div>"}
```

### `POST /api/exercises/pronunciation/check`
Awards `pronunciation` points.

Body: `{"target": {"phrase": "..."}, "transcription": "..."}`
Response: `{"html": "<div ...>...</div>"}`

---

## Summary / gamification

### `GET /api/summary`
Calls `gamify.try_daily_open` (idempotent per day, awards `daily_open`
points once/day) then returns the encouraging daily summary + total points.

Response: `{"summary": "You've covered 6 concepts...", "total_points": 142}`

---

## Screens -> endpoints map (for Phase 3 ordering)

1. **Notebook** — `/api/lessons/{id}` (load), `/api/annotate`, `/api/word-card`,
   `/api/lessons` (save new), `/api/lessons/{id}` PUT (update),
   `/api/lessons/{id}/title` PATCH (rename), `/api/lessons/{id}` DELETE.
2. **Lessons browser** — `/api/lessons` (list, grouped client-side by date/category).
3. **Exercises** — the four `/api/exercises/...` groups.
4. **Chat coach** — `/api/chat`.
5. **Summary dashboard** — `/api/summary`.
6. **Gender Checker + Translator (Tools)** — `/api/annotate`, `/api/word-card`
   reused as a standalone "paste any text" utility, separate from the saved
   notebook.
