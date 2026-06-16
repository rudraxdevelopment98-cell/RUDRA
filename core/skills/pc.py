"""
PC skill — control your computer.

Publishes Commands to the PC agent (agents/pc-agent/). The agent owns the
allow-list of what may actually run. Power/lock actions need confirmation.
"""
from __future__ import annotations

from core.log import get_logger
from core.skills.base import Skill, tool

log = get_logger("rudra.skill.pc")

DEFAULT_DEVICE = "main-pc"


class PCSkill(Skill):
    domain = "pc"

    def tools(self) -> list[dict]:
        return [
            tool("pc.open_app", "Open an application on the PC.",
                 {"app": {"type": "string", "description": "App name, e.g. 'code'"}},
                 ["app"]),
            tool("pc.run_script", "Run an allow-listed script on the PC.",
                 {"name": {"type": "string"}, "args": {"type": "array", "items": {"type": "string"}}},
                 ["name"]),
            tool("pc.volume", "Set or mute PC volume.",
                 {"level": {"type": "integer", "description": "0-100, or -1 to mute"}},
                 ["level"]),
            tool("pc.power", "Lock, sleep, or shut down the PC (needs confirmation).",
                 {"mode": {"type": "string", "enum": ["lock", "sleep", "shutdown"]}},
                 ["mode"]),
            tool("pc.search_files", "Search files on the PC.",
                 {"query": {"type": "string"}}, ["query"]),
        ]

    async def execute(self, name: str, args: dict) -> dict:
        # Power actions are dangerous → require confirmation per the protocol.
        needs_confirm = name == "pc.power"
        result = await self.dispatch(DEFAULT_DEVICE, name, args, needs_confirm)
        log.info("→ PC command %s (%s) → %s", name, args, result["command_id"])
        return result
