# RUDRA — Architecture

This is the blueprint. It explains *how* the parts fit so that, when we build
each module, we already know its inputs, outputs, and neighbours.

## 1. Mental model

RUDRA is built like a body:

- **Ears & mouth** → the **voice pipeline** (`core/voice/`).
- **Brain** → the **orchestrator** + **Claude LLM** (`core/brain/`).
- **Nervous system** → the **MQTT bus** (`core/bus/`), carrying signals to limbs.
- **Limbs** → **agents** running on the PC, phone, IoT hub, and ESP32 nodes.
- **Memory** → conversation history + a registry of known devices (`core/memory/`).
- **Skills** → the things RUDRA *knows how to do* (`core/skills/`).

The brain never talks to a light bulb directly. It emits a **command** onto the
bus; an **agent** that owns that device picks it up, does the work, and emits an
**event** back. This keeps the brain hardware-agnostic and lets us add new
devices without touching the brain.

## 2. The end-to-end flow

```
 1. WAKE      openWakeWord hears "Rudra"                       core/voice/wakeword.py
 2. LISTEN    record until you stop speaking                   core/voice/stt.py
 3. TRANSCRIBE  Whisper → text                                 core/voice/stt.py
 4. THINK     orchestrator asks Claude: what does the user     core/brain/orchestrator.py
              want? Claude returns an intent + tool call        core/brain/llm.py
 5. ROUTE     orchestrator maps the tool call to a Skill        core/skills/*
 6. ACT       Skill publishes a Command on MQTT                 core/bus/mqtt.py
 7. EXECUTE   the owning agent runs it, publishes an Event      agents/*
 8. REPLY     orchestrator turns the result into words          core/brain/llm.py
 9. SPEAK     cloud TTS → audio                                 core/voice/tts.py
```

## 3. Components

### 3.1 Voice pipeline (`core/voice/`)
Hybrid, as decided:
- **Wake word** — `openWakeWord` (local, free). Listens for "Rudra".
- **STT** — `faster-whisper` (local). Audio → text.
- **TTS** — cloud (ElevenLabs) for a natural voice; pluggable.
- **pipeline.py** — owns the microphone loop and chains wake → stt → brain → tts.

Each piece is behind an interface so any engine can be swapped (local↔cloud)
without changing the orchestrator.

### 3.2 The brain (`core/brain/`)
- **llm.py** — thin wrapper around the Claude API. One place to set the model,
  system prompt, and tool definitions.
- **intents.py** — the catalogue of **tools** Claude is allowed to call. Each
  tool maps 1:1 to a Skill (e.g. `pc.open_app`, `iot.set_light`).
- **orchestrator.py** — the loop. Takes user text + context, calls Claude with
  the tool catalogue, dispatches the chosen tool to a Skill, and composes a
  spoken reply.

> **Why an LLM for routing?** Natural commands ("dim the lights and open VS Code")
> map to *multiple* tool calls. Claude's tool-use does the parsing and planning;
> we just execute and confirm.

### 3.3 The bus (`core/bus/`)
- **MQTT** (broker: Mosquitto, in `docker-compose.yml`).
- **topics.py** — the single source of truth for topic names.
- Message contract lives in [`PROTOCOL.md`](PROTOCOL.md) and the JSON schemas in
  `shared/schema/`.

### 3.4 Skills (`core/skills/`)
A **Skill** is a class that (a) declares the tools it provides and (b) turns a
tool call into a bus **Command**. Skills are registered in a registry so adding
a capability = adding one file. v0 skills:
- `pc` — open apps, run scripts, volume, power, file search.
- `phone` — notify, locate, call, run a phone automation.
- `iot` — lights, plugs, sensors (via Home Assistant).
- `electronics` — GPIO / relays / sensors on ESP32 nodes.
- `system` — built-ins: time, status, "what can you do".

### 3.5 Agents (`agents/`)
Small programs that live **on the controlled thing** and own real hardware:
- **pc-agent** — Python; subscribes to `rudra/pc/#`, executes, reports back.
- **esp32** — Arduino firmware; subscribes to `rudra/node/<id>/#`, drives pins.
- **phone** — recipes for Tasker / Home Assistant Companion (Android) and
  Shortcuts (iOS); no custom app required to start.

### 3.6 Memory (`core/memory/`)
- **store.py** — SQLite to start. Holds: conversation turns (for context),
  a **device registry** (what's online, what it can do), and user preferences.

### 3.7 Dashboard (`dashboard/`)
A small web page to watch the bus live, see online devices, and read the log.
Later it can share the look of RD-Portal.

## 4. Security (designed in, not bolted on)
- **Dangerous commands require confirmation** (power off, delete, unlock).
- **Allow-list** of apps/scripts the PC agent may run.
- **Local-first**: audio is processed locally; only text/intents leave the box.
- **Per-device auth tokens** on the MQTT bus (no anonymous publishers in prod).
- Secrets only in `.env`, never committed.

## 5. Technology choices

| Layer        | Choice                          | Why                                   |
|--------------|---------------------------------|---------------------------------------|
| Core runtime | Python 3.11 + FastAPI           | Fast to build, great AI/audio libs    |
| LLM          | Claude (Anthropic)              | Strong tool-use / planning            |
| Bus          | MQTT (Mosquitto)                | Lightweight, perfect for IoT          |
| Wake word    | openWakeWord                    | Free, local, custom words             |
| STT          | faster-whisper                  | Accurate, runs local                  |
| TTS          | ElevenLabs (pluggable)          | Natural voice, light on hardware      |
| IoT hub      | Home Assistant                  | Speaks to 1000s of devices already    |
| Electronics  | ESP32 + Arduino                 | Cheap, Wi-Fi, MQTT-native             |
| Packaging    | Docker Compose                  | Runs anywhere (PC / server / Pi)      |

## 6. What is intentionally NOT decided yet
- Whether the dashboard becomes a full app or stays a status page.
- Final brain host (Docker keeps this open).
