---
title: French Coach
emoji: 📓
colorFrom: blue
colorTo: red
sdk: docker
pinned: false
---

# French Coach

A living French notebook for an adult learner on a ~4-month timeline for
Canadian immigration (TEF/TCF). Write or paste class notes, see noun gender
at a glance, click any word for meaning/grammar/pronunciation, ask the chat
coach, and practice with text, spoken-dialogue, photo-based, and
pronunciation exercises generated from the current lesson — with an
encouraging daily summary and additive points.

Built around **MiniCPM4.1-8B** (text) and **MiniCPM-V 4.6** (vision), both
≤ 32B and Apache-2.0 / free-API.

## Entrypoint

Runs `app_custom.py` via Docker (`CMD ["python", "app_custom.py"]`):
- `/` — React frontend (custom-built UI)
- `/api/*` — FastAPI JSON endpoints
- `/gradio/` — Gradio Blocks UI (mounted for SDK eligibility)

The React build (`frontend/dist/`) is committed to the repo. Rebuild it
whenever `frontend/src/` changes: `cd frontend && npm run build`.

## Local development

```
docker compose up -d --build
```

- `app` (port 7860) — themed Gradio Blocks UI (`app.py`)
- `app-custom` (port 7861) — React UI (`app_custom.py`), same as the Space
- `db` (port 5432) — Postgres

Copy `.env.example` to `.env` and fill in credentials first.
