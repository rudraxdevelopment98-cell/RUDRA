"""
The orchestrator — RUDRA's decision loop.

One public method, `handle(text)`:
    user text  →  Claude (with tools)  →  dispatch tool calls to skills  →  reply

This is deliberately small: it coordinates, it does not implement device logic
(that lives in skills) or talk to hardware (that lives in agents).
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

    async def handle(self, text: str) -> str:
        """
        Process one user utterance and return the spoken reply.

        Phase 1 will: build the tool catalogue, ask Claude, dispatch each chosen
        tool to its Skill, feed results back to Claude, and return final words.
        """
        log.info("➡  user: %s", text)
        history = await self.memory.recent_turns()
        tools = build_tool_catalogue(self.skills)

        response: LLMResponse = await self.llm.think(text, tools, history)

        for call in response.tool_calls:
            await self._dispatch(call)

        await self.memory.add_turn(role="user", text=text)
        await self.memory.add_turn(role="rudra", text=response.text)
        log.info("⬅  rudra: %s", response.text)
        return response.text

    async def _dispatch(self, call: dict) -> None:
        """Route a single tool call (e.g. 'pc.open_app') to the owning skill."""
        name = call.get("name", "")
        domain = name.split(".", 1)[0] if "." in name else name
        skill = self.skills.get(domain)
        if not skill:
            log.warning("No skill owns tool %r", name)
            return
        # TODO(Phase 1): collect the Event the skill/agent returns and feed it
        #                back to the LLM so the reply reflects the real result.
        await skill.execute(name, call.get("args", {}))
