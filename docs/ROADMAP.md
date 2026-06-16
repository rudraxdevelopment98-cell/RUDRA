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

## Phase 1 — Brain online (text)
*Goal: type a command, RUDRA understands and routes it (no voice yet).*
- [ ] Wire the real Claude API in `brain/llm.py`.
- [ ] Define the v0 tool catalogue in `brain/intents.py`.
- [ ] Orchestrator: text in → Claude tool call → Skill → reply.
- [ ] `system` skill working end-to-end (time, status, "what can you do").
- [ ] Memory: store conversation turns in SQLite.

**Done when:** a chat box (or curl) → "what time is it?" → correct spoken-style reply.

## Phase 2 — Voice
*Goal: talk to RUDRA hands-free.*
- [ ] Local wake word ("Rudra") via openWakeWord.
- [ ] Local STT via faster-whisper.
- [ ] Cloud TTS (pick provider) behind the `tts` interface.
- [ ] Full loop: wake → listen → think → speak.

**Done when:** say "Rudra, what time is it?" and hear the answer.

## Phase 3 — Control the PC
*Goal: first real device.*
- [ ] PC agent connects to the bus, registers itself.
- [ ] Skills: open app, run allow-listed script, volume, lock/sleep, file search.
- [ ] Confirmation flow for dangerous actions.

**Done when:** "Rudra, open VS Code and mute the volume" works.

## Phase 4 — Smart home / IoT
*Goal: the classic JARVIS moment.*
- [ ] Home Assistant integration in the `iot` skill.
- [ ] Lights, plugs, sensors readable + controllable.

**Done when:** "Rudra, turn off the bedroom lights" works.

## Phase 5 — Custom electronics
*Goal: control hardware you wired yourself.*
- [ ] Flash an ESP32 node from `agents/esp32/`.
- [ ] Node auto-registers on the bus; `electronics` skill drives its pins.

**Done when:** "Rudra, turn on the desk relay" flips a real relay.

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
