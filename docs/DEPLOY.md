# Deploying RUDRA's web dashboard

`server/app.py` serves the dashboard (chat UI, device status, capabilities,
live log) over HTTP/WebSocket on `$PORT` (default `8080`). The repo's
`Dockerfile` builds and runs it, so any container host works. **Railway** is
the easiest path — free tier, deploys straight from GitHub, no CLI required.

## Railway (recommended)

1. Go to [railway.app](https://railway.app) and sign in with GitHub.
2. **New Project → Deploy from GitHub repo** → pick `rudraxdevelopment98-cell/rudra`.
3. Set the branch to deploy (e.g. `claude/vigilant-euler-o3s70q`, or `main` once merged).
4. Railway detects the `Dockerfile` automatically — no build config needed.
5. Add environment variables (**Variables** tab):
   - `GEMINI_API_KEY` — required (default provider, free tier). Get one at
     [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey).
     Without it chat replies with a warning instead of thinking.
   - `RUDRA_NAME` — optional, default is fine.
   - To switch back to Claude later: set `RUDRA_LLM_PROVIDER=anthropic` and
     `ANTHROPIC_API_KEY` instead (`RUDRA_MODEL` picks the Claude model).
   - Leave `MQTT_HOST` unset — with no broker reachable the bus runs in stub
     mode automatically, so PC/IoT/electronics commands log "dispatched"
     instead of crashing. (Those need a broker + agent reachable from the
     container, which is a separate, optional step — see below.)
6. **Settings → Networking → Generate Domain** to get your public URL
   (`https://<your-app>.up.railway.app`). Open it — that's the dashboard.
7. Every push to the deployed branch redeploys automatically.

### Wiring up real devices (optional, later)
The PC agent / IoT bridge / ESP32 nodes need to reach the same MQTT broker as
the deployed brain. The simplest setup is a small always-on broker (e.g. a
$5 VPS or a Pi at home running `eclipse-mosquitto`, port 1883 open), with
`MQTT_HOST` on Railway pointed at its public address, and the agents
(`agents/pc-agent`, `agents/iot`, `agents/esp32`) on your machines pointed at
the same host. Until then, the dashboard's chat and "what can you do" work
fully online; device commands stay in stub mode.

## Render (alternative)
1. [render.com](https://render.com) → **New → Web Service** → connect the repo.
2. Render also auto-detects the `Dockerfile`.
3. Same environment variables as above.
4. Render assigns a public `onrender.com` URL automatically.

## Fly.io (alternative, CLI-based)
```bash
flyctl launch        # detects the Dockerfile, asks app name + region
flyctl secrets set ANTHROPIC_API_KEY=sk-...
flyctl deploy
```

## Running it yourself, no host needed
```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-...
uvicorn server.app:app --host 0.0.0.0 --port 8080
# open http://localhost:8080
```
Or with Docker Compose (also starts the MQTT broker for device commands):
```bash
docker compose up
# web dashboard: http://localhost:8080
```

## Connecting real devices (shared MQTT broker)

The brain (deployed on Railway) and your device agents (PC agent, IoT bridge,
ESP32 nodes) only talk to each other if they're all pointed at the **same**
MQTT broker. Without one, the bus runs in stub mode — chat works, but device
commands just get logged as "dispatched" and nothing happens.

**Recommended: HiveMQ Cloud (free tier, no server to run)**

1. Go to [hivemq.com/mqtt-cloud-broker](https://www.hivemq.com/mqtt-cloud-broker/)
   and create a free **Serverless** cluster.
2. In the cluster's **Access Management**, create credentials (username + password).
3. Copy the cluster's hostname (looks like `xxxxx.s1.eu.hivemq.cloud`) — TLS
   port is always **8883**.
4. On Railway (the brain), set these variables:
   ```
   MQTT_HOST=xxxxx.s1.eu.hivemq.cloud
   MQTT_PORT=8883
   MQTT_TLS=true
   MQTT_USERNAME=<your username>
   MQTT_PASSWORD=<your password>
   ```
5. Redeploy. The log should show `🔌 bus connected → mqtt://...` instead of
   "stub mode".
6. On each machine running a device agent (your PC, an IoT bridge, etc.), set
   the same four `MQTT_*` variables (e.g. in a local `.env`) and start the
   agent — see `agents/pc-agent/README.md`, `agents/iot/README.md`,
   `agents/esp32/README.md`.

Once the brain and an agent share a broker, the agent's `register` message
makes the device show up in the dashboard's "Connected devices" list, and
commands like "open Chrome" or "turn off the bedroom lights" actually reach
it instead of just logging.
