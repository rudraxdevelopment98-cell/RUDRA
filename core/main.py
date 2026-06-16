"""
RUDRA entry point.

Boots every subsystem and wires them together. In Phase 0 this only proves the
skeleton holds: it connects the bus, constructs the brain, registers skills, and
prepares the voice pipeline — then idles. Real behaviour arrives in later phases.

Run:
    python -m core.main
"""
from __future__ import annotations

import asyncio

from core import __version__
from core.brain.orchestrator import Orchestrator
from core.bus.mqtt import Bus
from core.config import config
from core.log import get_logger
from core.memory.store import Memory
from core.skills import load_skills
from core.voice.pipeline import VoicePipeline

log = get_logger("rudra.main")

BANNER = r"""
   ____  _   _ ____  ____      _
  |  _ \| | | |  _ \|  _ \    / \      voice-driven AI command center
  | |_) | | | | | | | |_) |  / _ \     "your own JARVIS"
  |  _ <| |_| | |_| |  _ <  / ___ \    v{ver}
  |_| \_\\___/|____/|_| \_\/_/   \_\
"""


async def main() -> None:
    print(BANNER.format(ver=__version__))

    for warning in config.validate():
        log.warning("⚠ %s", warning)

    # 1. Memory — conversation history + device registry.
    memory = Memory(config.db_path)
    await memory.init()

    # 2. Bus — the nervous system.
    bus = Bus(config)
    await bus.connect()

    # 3. Skills — what RUDRA can do.
    skills = load_skills(bus, memory)
    log.info("Loaded %d skills: %s", len(skills), ", ".join(skills))

    # 4. Brain — the orchestrator that ties text → Claude → skills → reply.
    brain = Orchestrator(config, bus, memory, skills)

    # 5. Voice — wake word → STT → brain → TTS.
    voice = VoicePipeline(config, brain)

    log.info("✅ RUDRA skeleton is wired. Subsystems: memory, bus, skills, brain, voice.")
    log.info("   (Phase 0 — no real actions yet. See docs/ROADMAP.md.)")

    try:
        await voice.run()  # in Phase 0 this just idles.
    except (KeyboardInterrupt, asyncio.CancelledError):
        log.info("Shutting down…")
    finally:
        await bus.disconnect()
        await memory.close()


if __name__ == "__main__":
    asyncio.run(main())
