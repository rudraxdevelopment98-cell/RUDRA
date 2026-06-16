"""
Skill base class.

A Skill is one capability area (pc, phone, iot, electronics, system). Each Skill:
  1. declares its tools()  → specs Claude can call
  2. implements execute()  → returns a result the brain feeds back to Claude

Most skills publish a Command to the bus; the owning *agent* does the real work
and replies with an Event. Until an agent exists, the skill returns a
"dispatched" result so the brain can still answer sensibly. Skills stay thin.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from core.bus.mqtt import Bus, new_id
from core.bus.topics import topic, CMD, EVENT
from core.log import get_logger
from core.memory.store import Memory

log = get_logger("rudra.skill")


class Skill(ABC):
    #: short domain key, e.g. "pc". Tool names are "<domain>.<verb>".
    domain: str = "base"

    def __init__(self, bus: Bus, memory: Memory):
        self.bus = bus
        self.memory = memory

    @abstractmethod
    def tools(self) -> list[dict]:
        """Return the Anthropic tool specs this skill provides."""
        raise NotImplementedError

    @abstractmethod
    async def execute(self, name: str, args: dict) -> dict:
        """
        Carry out a tool call and return a JSON-able result dict.

        Convention:
          {"ok": True, "result": {...}}            success
          {"ok": False, "error": "..."}            failure
          {"ok": True, "status": "dispatched", ...} command sent to an agent
        """
        raise NotImplementedError

    # --- helper every device-backed skill uses ---
    async def dispatch(self, device: str, action: str, args: dict,
                       needs_confirm: bool = False, confirmed: bool = False) -> dict:
        """Publish a Command to a device and return a 'dispatched' result."""
        cmd_id = new_id("cmd")
        await self.bus.publish(
            topic(self.domain, device, CMD),
            {
                "id": cmd_id,
                "action": action,
                "args": args,
                "reply_to": topic(self.domain, device, EVENT),
                "needs_confirm": needs_confirm,
                "confirmed": confirmed,
            },
        )
        return {
            "ok": True,
            "status": "dispatched",
            "command_id": cmd_id,
            "device": device,
            "note": f"Command '{action}' sent to {device}.",
        }

    def needs_confirmation(self, device: str, action: str, args: dict, message: str) -> dict:
        """
        Return a result telling the brain to ask the user before acting.

        The orchestrator stashes `pending` and, once the user confirms (via the
        `system.confirm` tool), re-issues it as a single `confirmed` command.
        """
        return {
            "ok": True,
            "status": "needs_confirmation",
            "message": message,
            "pending": {"domain": self.domain, "device": device, "action": action, "args": args},
        }


def tool(name: str, description: str, properties: dict, required: list[str] | None = None) -> dict:
    """Small helper to build an Anthropic tool spec."""
    return {
        "name": name,
        "description": description,
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": required or [],
        },
    }
