"""
Skill base class.

A Skill is one capability area (pc, phone, iot, electronics, system). Each Skill:
  1. declares its tools()  → specs Claude can call
  2. implements execute()  → turns a tool call into a bus Command (or local work)

Most skills just publish a Command to the bus; the owning *agent* does the real
work and replies with an Event. Skills stay thin and hardware-free.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from core.bus.mqtt import Bus, new_id
from core.bus.topics import topic, CMD
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
    async def execute(self, name: str, args: dict) -> None:
        """Carry out a tool call (usually by publishing a Command)."""
        raise NotImplementedError

    # --- helper every skill can use ---
    async def send_command(self, device: str, action: str, args: dict,
                           needs_confirm: bool = False) -> str:
        """Publish a Command to a device and return the command id."""
        cmd_id = new_id("cmd")
        await self.bus.publish(
            topic(self.domain, device, CMD),
            {
                "id": cmd_id,
                "action": action,
                "args": args,
                "reply_to": topic(self.domain, device, "event"),
                "needs_confirm": needs_confirm,
            },
        )
        return cmd_id


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
