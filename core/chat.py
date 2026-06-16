"""
RUDRA text chat — talk to the brain by typing (Phase 1, before voice).

Boots the same subsystems as the full system (memory, bus, skills, brain) but
reads commands from the keyboard instead of the microphone. The fastest way to
test that Claude understands and routes your commands.

Run:
    export ANTHROPIC_API_KEY=sk-...
    python -m core.chat
"""
from __future__ import annotations

import asyncio

from core.brain.orchestrator import Orchestrator
from core.bus.mqtt import Bus
from core.config import config
from core.log import get_logger
from core.memory.store import Memory
from core.skills import load_skills

log = get_logger("rudra.chat")


async def main() -> None:
    for warning in config.validate():
        log.warning("⚠ %s", warning)

    memory = Memory(config.db_path)
    await memory.init()
    bus = Bus(config)
    await bus.connect()
    skills = load_skills(bus, memory)
    brain = Orchestrator(config, bus, memory, skills)

    print(f"\n🔱 {config.name} is listening. Type a command (or 'quit').\n")
    loop = asyncio.get_event_loop()
    try:
        while True:
            try:
                text = await loop.run_in_executor(None, input, "you ▸ ")
            except (EOFError, KeyboardInterrupt):
                break
            if text.strip().lower() in {"quit", "exit", "bye"}:
                break
            reply = await brain.handle(text)
            print(f"{config.name} ▸ {reply}\n")
    finally:
        await bus.disconnect()
        await memory.close()
        print("\nGoodbye.")


if __name__ == "__main__":
    asyncio.run(main())
