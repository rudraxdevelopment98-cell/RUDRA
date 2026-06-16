"""
Phone skill — reach your phone.

Talks to a phone agent: Home Assistant Companion / Tasker on Android, or
Shortcuts on iOS (see agents/phone/). No custom app required to start.
"""
from __future__ import annotations

from core.log import get_logger
from core.skills.base import Skill, tool

log = get_logger("rudra.skill.phone")

DEFAULT_DEVICE = "my-phone"


class PhoneSkill(Skill):
    domain = "phone"

    def tools(self) -> list[dict]:
        return [
            tool("phone.notify", "Send a notification to the phone.",
                 {"title": {"type": "string"}, "body": {"type": "string"}},
                 ["body"]),
            tool("phone.find", "Make the phone ring loudly to find it.", {}),
            tool("phone.locate", "Get the phone's current location.", {}),
            tool("phone.run_automation", "Trigger a named phone automation/shortcut.",
                 {"name": {"type": "string"}}, ["name"]),
        ]

    async def execute(self, name: str, args: dict) -> None:
        cmd_id = await self.send_command(DEFAULT_DEVICE, name, args)
        log.info("→ phone command %s (%s) sent as %s", name, args, cmd_id)
