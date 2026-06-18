# Running RUDRA on your own machine (secure self-hosting)

This is the recommended setup for a personal command center: everything runs
locally on your Mac (code + data can live on an external SSD), and you reach it
remotely only through a private, encrypted tunnel — never an open port.

```
   your phone / laptop (anywhere)
            │   encrypted tunnel (Tailscale)
            ▼
   ┌───────────────────────────────┐
   │  MacBook (+ external SSD)      │
   │   ┌─────────┐   ┌───────────┐  │
   │   │ broker  │←→ │  brain +  │  │   bound to 127.0.0.1
   │   │(mosq.)  │   │ dashboard │  │   password-gated
   │   └─────────┘   └───────────┘  │
   └───────────────────────────────┘
```

## 1. Put the project on the external SSD

```bash
cd /Volumes/YOUR_SSD
git clone <your-private-repo> RUDRA
cd RUDRA
cp .env.example .env
```

Keep the repo **private** on GitHub. `.env`, `*.db`, and `infra/passwd` are
gitignored so secrets never leave the SSD.

## 2. Set the secrets in `.env`

```bash
# Brain
GEMINI_API_KEY=...            # or ANTHROPIC_API_KEY + RUDRA_LLM_PROVIDER=anthropic

# Dashboard login — REQUIRED before remote access. Generate one:
#   python3 -c "import secrets;print(secrets.token_urlsafe(24))"
RUDRA_AUTH_TOKEN=the-generated-password

# Local broker credentials (created in step 3)
MQTT_HOST=broker              # 'broker' inside docker-compose; 'localhost' if running bare
MQTT_PORT=1883
MQTT_USERNAME=rudra
MQTT_PASSWORD=a-broker-password
MQTT_TLS=false                # plain is fine on localhost; the tunnel encrypts remote traffic

# Stay local; the tunnel handles remote reach
RUDRA_HOST=127.0.0.1
```

## 3. Create the broker password file

The broker now refuses anonymous connections, so create one credential:

```bash
docker run --rm -v "$PWD/infra:/m" eclipse-mosquitto:2 \
  mosquitto_passwd -c -b /m/passwd rudra a-broker-password
```

Use the same username/password you put in `.env`.

## 4. Start everything

```bash
docker compose up -d        # broker + brain + web dashboard
```

Open http://localhost:8080 → you'll get the **login screen**. Enter your
`RUDRA_AUTH_TOKEN`.

## 5. Secure remote access (Tailscale)

Open ports are the usual way people get owned. Don't. Use a private tunnel:

1. Install Tailscale on the MacBook and on your phone/laptop, sign in to the
   same account on both.
2. From any of your devices, reach RUDRA at `http://<mac-tailscale-name>:8080`.
3. The login password still applies, and the traffic is end-to-end encrypted.
   Nothing is exposed to the public internet.

(Cloudflare Tunnel is a fine alternative if you want a real hostname.)

## Security model — why this is safe to give "full authority"

| Layer | Protection |
|-------|------------|
| Network | Bound to `127.0.0.1`; remote only via encrypted Tailscale tunnel. No open ports. |
| App | Every page, API call, and WebSocket requires a session from the login password (constant-time compare, HttpOnly cookie). |
| Broker | Anonymous MQTT disabled; username/password required. |
| Actions | Risky/destructive actions (delete, power off, unlock) require an explicit confirmation before RUDRA runs them. |
| Secrets | Live only in `.env` / `infra/passwd` on the SSD — gitignored, never committed. |
| Audit | Every action is logged to the live log feed and the in-memory ring buffer. |

## Good habits

- **Rotate any secret that has ever been pasted into a chat or screenshot** —
  treat it as already leaked.
- Restarting the server logs out all sessions (sessions are in-memory by design).
- Keep `RUDRA_HOST=127.0.0.1`. If you ever set it to `0.0.0.0`, RUDRA will warn
  you at startup that it's unauthenticated-on-the-network unless a token is set.
- Back up the SSD; `rudra.db` holds your conversation history and remembered facts.
