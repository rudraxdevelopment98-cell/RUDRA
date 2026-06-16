# RUDRA

> A personal, voice-driven AI command center — your own JARVIS.
> Named after **Rudra**, a form of Lord Shiva.

RUDRA listens for a wake word, understands what you say, and acts — controlling
your **PC**, **phone**, **smart-home / IoT** devices, and **custom electronics**
(ESP32 / Arduino) from one always-on brain.

This repository is the **scaffold (skeleton)** for that system. Nothing here is
finished yet — every module is a clearly-marked stub with a `TODO` and a
defined contract, so we can build it piece by piece without ever guessing how
the pieces fit together.

---

## The idea in one picture

```
        you ──speak──▶  🎤 wake word ──▶ speech-to-text ──▶ text
                                                            │
                                                            ▼
                                                    ┌───────────────┐
                                                    │   THE BRAIN   │  (core/)
                                                    │  Claude LLM   │
                                                    │  + router     │
                                                    └───────┬───────┘
                                                            │ commands
                                                            ▼
                                                ┌──────── MQTT bus ────────┐
                                                │   (the nervous system)    │
                                                └──┬──────┬───────┬─────┬───┘
                                                   ▼      ▼       ▼     ▼
                                                  PC    phone   IoT   ESP32
                                               agent   agent  (Home  nodes
                                                              Assistant)
                                                            │
        you ◀──speak──  🔊 text-to-speech  ◀── reply ◀──────┘
```

## Design decisions (locked for v0)

| Decision        | Choice                                                              |
|-----------------|--------------------------------------------------------------------|
| **Brain host**  | Portable — runs in **Docker**, so it works on a PC, server, or Pi. |
| **Voice**       | **Hybrid** — local wake word + local STT, cloud TTS + cloud LLM.   |
| **Brain (LLM)** | **Claude** (Anthropic) for understanding and tool routing.         |
| **Nervous system** | **MQTT** — every device speaks to the brain over one bus.       |
| **Targets v0**  | PC · Phone · Smart-home/IoT · Custom electronics.                  |

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full design and
[`docs/ROADMAP.md`](docs/ROADMAP.md) for the build order.

## Repository layout

```
core/         the brain — FastAPI orchestrator, LLM router, voice pipeline, skills
  brain/        LLM client + intent routing
  bus/          MQTT client + topic contract
  voice/        wake word · speech-to-text · text-to-speech · pipeline
  memory/       conversation history + device registry
  skills/       what RUDRA can DO (pc, phone, iot, electronics, system)
agents/       code that runs ON the things being controlled
  pc-agent/     Python agent for your PC
  esp32/        Arduino/ESP32 firmware for custom electronics
  phone/        how to wire up Android/iOS
dashboard/    a small web UI to watch & configure RUDRA
shared/       message schemas shared by brain and agents
docs/         architecture, roadmap, protocol
```

## Quick start

```bash
cp .env.example .env          # add your ANTHROPIC_API_KEY
pip install -r requirements.txt

# Phase 1 — talk to the brain by typing:
python -m core.chat
#   you ▸ what time is it?
#   Rudra ▸ It's Tuesday 16 June 2026, 9:12 PM.

# Run the tests (no API key needed):
python -m tests.test_phase1

# Boot the whole system (idles until voice lands in Phase 2):
docker compose up             # MQTT broker + brain
# or:  python -m core.main
```

## Status

🟢 **Phase 1 — Brain online (text).** Claude understands typed commands, routes
them to skills, and replies; the `system` skill works end-to-end and
conversations persist to SQLite. Voice is next (Phase 2). See the roadmap.
