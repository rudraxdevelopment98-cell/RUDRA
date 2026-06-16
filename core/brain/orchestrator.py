"""
The orchestrator — RUDRA's decision loop.

One public method, `handle(text)`:
    user text  →  Claude (with tools)  →  skills execute tools  →  spoken reply

It coordinates only: device logic lives in skills, hardware lives in agents.
"""
from __future__ import annotations

from core.brain.intents import build_tool_catalogue
from core.brain.llm import LLM, LLMResponse
from core.bus.mqtt import Bus
from core.config import Config
from core.log import get_logger
from core.memory.store import Memory

log = get_logger("rudra.brain.orchestrator")


class Orchestrator:
    def __init__(self, config: Config, bus: Bus, memory: Memory, skills: dict):
        self.config = config
        self.bus = bus
        self.memory = memory
        self.skills = skills
        self.llm = LLM(config)
        self._tools = build_tool_catalogue(skills)

    async def handle(self, text: str) -> str:
        """Process one user utterance and return the spoken reply."""
        text = text.strip()
        if not text:
            return ""
        log.info("➡  user: %s", text)

        history = await self.memory.recent_turns()
        response: LLMResponse = await self.llm.think(
            text, self._tools, history, self._execute_tool
        )

        await self.memory.add_turn("user", text)
        await self.memory.add_turn("assistant", response.text)
        log.info("⬅  rudra: %s", response.text)
        return response.text

    async def _execute_tool(self, name: str, args: dict) -> dict:
        """Route one tool call (e.g. 'pc.open_app') to the owning skill."""
        domain = name.split(".", 1)[0] if "." in name else name
        skill = self.skills.get(domain)
        if not skill:
            return {"ok": False, "error": f"no skill owns tool '{name}'"}
        try:
            return await skill.execute(name, args)
        except Exception as exc:  # noqa: BLE001 — surface any skill error to the brain
            log.exception("skill %s failed on %s", domain, name)
            return {"ok": False, "error": str(exc)}
