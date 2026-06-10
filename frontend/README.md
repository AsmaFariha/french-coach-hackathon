# French Coach — custom UI frontend

React + Vite app served by `app_custom.py` at `/custom/` (see
`API_CONTRACT.md` for the backend contract and
`../UI_UPGRADE_PLAN.md` for the overall plan).

## Dev

```
npm install
npm run dev
```

`/api/...` calls are proxied to `http://localhost:7861` (run
`python app_custom.py` or `docker compose up app-custom` for the backend).

## Build

```
npm run build
```

Outputs to `dist/`, which **is committed** — `app_custom.py` serves it as
static files, and a Gradio-SDK Space build does not run `npm`. Rebuild and
re-commit `dist/` whenever frontend source changes.
