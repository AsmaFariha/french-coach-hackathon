---
title: French Coach
emoji: 🇫🇷
colorFrom: blue
colorTo: red
sdk: gradio
sdk_version: 6.17.3
app_file: app_custom.py
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

This Space runs `app_custom.py` (custom React UI, served at `/`, with
`/api/...` JSON endpoints — see `frontend/API_CONTRACT.md`). It's still a
Gradio-SDK app: a `gr.Blocks` object backs the `gr.Server` that the React
build and API routes are mounted onto (see `UI_UPGRADE_PLAN.md` Phase 5).

The React build (`frontend/dist/`) is committed to the repo, since a
Gradio-SDK Space build does not run `npm`. Rebuild and re-commit it whenever
`frontend/src/` changes (`cd frontend && npm run build`).

### Reverting to the themed Blocks fallback

If the custom UI ever fails on the Space, change `app_file` above from
`app_custom.py` to `app.py` and redeploy — `app.py` (themed Gradio Blocks UI)
is kept in the repo as a fully working fallback.

## Local development

```
docker compose up -d --build
```

- `app` (port 7860) — themed Blocks UI (`app.py`)
- `app-custom` (port 7861) — custom React UI (`app_custom.py`), same as the
  Space entrypoint
- `db` (port 5432) — Postgres

Copy `.env.example` to `.env` and fill in credentials first.
