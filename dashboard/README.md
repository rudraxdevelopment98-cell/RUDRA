# RUDRA — Dashboard

A web UI to talk to RUDRA and watch it work: a chat panel, online devices,
capabilities, and a live log feed.

It's a single static page (`index.html`, no build step) served by
`server/app.py`, which also exposes the API it talks to:
- `POST /api/chat`, `WS /ws/chat` — chat with the brain.
- `GET /api/status` — devices + capabilities.
- `WS /ws/logs` — live log stream.

## Run it
```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-...
uvicorn server.app:app --host 0.0.0.0 --port 8080
# open http://localhost:8080
```
To deploy it somewhere with a public URL, see [`docs/DEPLOY.md`](../docs/DEPLOY.md)
(Railway is the quickest path).

Later it can adopt the look of RD-Portal and grow into the full Phase 7
control surface (proactive routines, voice identity, etc).
