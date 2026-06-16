"""
System skill — RUDRA's built-in answers (no external device needed).

These run inside the brain itself: time, status, and "what can you do".
This is the first skill that works fully end-to-end (Phase 1).
"""
from __future__ import annotations

from datetime import datetime

from core.log import get_logger
from core.skills.base import Skill, tool

log = get_logger("rudra.skill.system")


class SystemSkill(Skill):
    domain = "system"

    # Set by the registry so 'capabilities' can describe every skill.
    all_skills: dict | None = None

    def tools(self) -> list[dict]:
        return [
            tool("system.time", "Tell the current date and time.", {}),
            tool("system.status", "Report which devices are online and RUDRA's health.", {}),
            tool("system.capabilities", "List what RUDRA can currently do.", {}),
        ]

    async def execute(self, name: str, args: dict) -> dict:
        if name == "system.time":
            now = datetime.now()
            return {"ok": True, "result": {
                "iso": now.isoformat(timespec="seconds"),
                "spoken": now.strftime("%A %d %B %Y, %I:%M %p"),
            }}

        if name == "system.status":
            devices = await self.memory.online_devices()
            return {"ok": True, "result": {
                "online_devices": len(devices),
                "devices": list(devices.keys()),
                "brain": "online",
            }}

        if name == "system.capabilities":
            caps: list[str] = []
            for skill in (self.all_skills or {}).values():
                for t in skill.tools():
                    caps.append(f"{t['name']} — {t['description']}")
            return {"ok": True, "result": {"capabilities": caps}}

        return {"ok": False, "error": f"unknown system action: {name}"}
