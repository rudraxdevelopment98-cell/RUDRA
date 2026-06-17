# RUDRA — Roadmap

The build order. Each phase ends with something you can actually *use*, so
RUDRA gets more capable every step instead of being "done" only at the end.

These phases mirror the project's phases in **RD-Portal**.

---

## Phase 0 — Skeleton  🟡 (current)
*Goal: every part exists as a stub with a defined contract.*
- [x] Architecture, roadmap, and MQTT protocol documented.
- [x] Repo layout: `core/`, `agents/`, `dashboard/`, `shared/`.
- [x] Brain orchestrator + Claude client stubs.
- [x] MQTT bus wrapper + topic contract.
- [x] Voice pipeline stubs (wake word, STT, TTS).
- [x] Skill base class + registry + 5 skill stubs.
- [x] PC agent + ESP32 firmware skeletons.
- [x] Docker Compose (MQTT broker + brain).

**Done when:** `docker compose up` boots the brain and broker and logs that
every subsystem is wired (no real actions yet).

## Phase 1 — Brain online (text)  🟢 (built)
*Goal: type a command, RUDRA understands and routes it (no voice yet).*
- [x] Wire the real Claude API in `brain/llm.py` (full tool-use loop).
- [x] Build the v0 tool catalogue from every skill (`brain/intents.py`).
- [x] Orchestrator: text in → Claude tool call → Skill → reply.
- [x] `system` skill working end-to-end (time, status, capabilities).
- [x] Memory: store conversation turns in SQLite.
- [x] `python -m core.chat` REPL to talk by typing.
- [x] `tests/test_phase1.py` covers memory, skills, routing, catalogue.

**Done when:** `python -m core.chat` → "what time is it?" → correct spoken-style reply.
*(Code complete + unit-tested. Final live check needs your `ANTHROPIC_API_KEY`.)*

## Phase 2 — Voice  🟢 (built)
*Goal: talk to RUDRA hands-free.*
- [x] Local wake word via openWakeWord (bring your own "rudra" model — see below).
- [x] Local STT via faster-whisper, with energy-based silence detection.
- [x] Cloud TTS via ElevenLabs behind the `tts` interface.
- [x] Full loop: wake → listen → think → speak (`core/voice/pipeline.py`).
- [x] `tests/test_phase2.py` covers config, class wiring, and idle behaviour.

**Done when:** say "Rudra, what time is it?" and hear the answer.
*(Code complete + unit-tested. Set `RUDRA_VOICE_ENABLED=true`, `TTS_API_KEY`, and
train/point `RUDRA_WAKE_MODEL_PATH` at an openWakeWord model for "rudra" — final
live check needs a microphone, speakers, and those keys/model.)*

## Phase 3 — Control the PC  🟢 (built)
*Goal: first real device.*
- [x] Real MQTT bus (aiomqtt) with wildcard routing; stub fallback when no broker.
- [x] PC agent connects to the bus, registers itself, reports events.
- [x] Skills: open app, run allow-listed script, volume, lock/sleep/shutdown, file search.
- [x] Confirmation flow for dangerous actions (`system.confirm` / `system.cancel`).
- [x] Brain learns online devices from `register` events (device registry).
- [x] `tests/test_phase3.py` covers topic matching, confirmation, registry, agent.

**Done when:** "Rudra, open VS Code and mute the volume" works.
*(Code complete + unit-tested. A live run needs an MQTT broker — `docker compose
up` starts Mosquitto — plus `python agents/pc-agent/agent.py` on the target PC.)*

## Phase 4 — Smart home / IoT  🟢 (built)
*Goal: the classic JARVIS moment.*
- [x] Home Assistant bridge agent (`agents/iot/`) drives the `iot` skill.
- [x] Lights, plugs, scenes controllable; sensors readable (with values).
- [x] Bus request/reply so reads return the actual value (not just "sent").
- [x] Spoken names resolve to HA entity ids (friendly-name / id matching).
- [x] `tests/test_phase4.py` covers request/reply, the skill, and the agent.

**Done when:** "Rudra, turn off the bedroom lights" works.
*(Code complete + unit-tested. A live run needs an MQTT broker plus a running
Home Assistant — set `HA_URL`/`HA_TOKEN` and start `python agents/iot/agent.py`.)*

## Phase 5 — Custom electronics  🟢 (built)
*Goal: control hardware you wired yourself.*
- [x] ESP32 firmware (`rudra_node.ino`) parses commands, drives named relays/pins,
      reads sensors, publishes retained state, and replies with Events.
- [x] Node auto-registers on the bus; `electronics`/`node` skill drives its pins.
- [x] `node_sim.py` — a software stand-in for the firmware (same protocol) so
      the skill can be developed/tested without a physical board.
- [x] `tests/test_phase5.py` covers the simulator's command logic and the skill.

**Done when:** "Rudra, turn on the desk relay" flips a real relay.
*(Code complete + unit-tested via the simulator. A live flip needs real
hardware — flash `rudra_node.ino` per `agents/esp32/README.md`.)*

## Phase 6 — Phone
*Goal: reach your phone.*
- [ ] Android via Home Assistant Companion / Tasker recipes.
- [ ] iOS via Shortcuts.
- [ ] Skills: notify, find phone, location, run automation.

**Done when:** "Rudra, find my phone" makes it ring.

## Phase 7 — Polish & dashboard
- [ ] Live dashboard: online devices, bus activity, logs.
- [ ] Voice identity / auth.
- [ ] Proactive routines ("good morning" scene).
- [ ] Harden security (tokens, allow-lists, audit log).

---

### How we work
Build one phase at a time, top to bottom. Don't start a phase until the one
before it actually works. Tick boxes here as we go; the same milestones are
tracked as tasks in **RD-Portal**.
