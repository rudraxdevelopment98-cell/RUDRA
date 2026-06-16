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

## Quick start (skeleton)

> The scaffold runs but does not yet do real work — it boots the brain, the MQTT
> bus, and prints that each subsystem is wired.

```bash
cp .env.example .env          # add your ANTHROPIC_API_KEY etc.
docker compose up             # starts MQTT broker + the brain
# or, without Docker:
pip install -r requirements.txt
python -m core.main
```

## Status

🟡 **Phase 0 — Skeleton.** Architecture + stubs in place. See the roadmap.
