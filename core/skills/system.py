"""
System skill — RUDRA's built-in answers (no external device needed).

These run inside the brain itself: time, status, and "what can you do".
This is the first skill we make fully real (Phase 1).
"""
from __future__ import annotations

from datetime import datetime

from core.log import get_logger
from core.skills.base import Skill, tool

log = get_logger("rudra.skill.system")


class SystemSkill(Skill):
    domain = "system"

    def tools(self) -> list[dict]:
        return [
            tool("system.time", "Tell the current date and time.", {}),
            tool("system.status", "Report which devices are online and RUDRA's health.", {}),
            tool("system.capabilities", "List what RUDRA can currently do.", {}),
        ]

    async def execute(self, name: str, args: dict) -> None:
        # System skills answer locally rather than via the bus.
        if name == "system.time":
            now = datetime.now().strftime("%A %d %B, %I:%M %p")
            log.info("🕐 %s", now)
        elif name == "system.status":
            devices = await self.memory.online_devices()
            log.info("📊 %d device(s) online", len(devices))
        elif name == "system.capabilities":
            log.info("🧩 capabilities requested")
        else:
            log.warning("Unknown system action %r", name)
