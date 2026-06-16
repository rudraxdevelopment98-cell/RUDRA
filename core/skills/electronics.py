"""
Electronics skill — custom hardware you wired yourself.

Drives ESP32/Arduino nodes (agents/esp32/) over MQTT: relays, LEDs, motors,
and reading sensors. Each node has an id like 'esp32-desk'.
"""
from __future__ import annotations

from core.log import get_logger
from core.skills.base import Skill, tool

log = get_logger("rudra.skill.electronics")


class ElectronicsSkill(Skill):
    domain = "node"  # matches the 'node' MQTT domain for custom hardware

    def tools(self) -> list[dict]:
        return [
            tool("node.set_pin", "Set a digital output pin on an ESP32 node.",
                 {"node": {"type": "string", "description": "Node id, e.g. 'esp32-desk'"},
                  "pin": {"type": "integer"},
                  "value": {"type": "integer", "enum": [0, 1]}},
                 ["node", "pin", "value"]),
            tool("node.set_relay", "Switch a named relay on a node on/off.",
                 {"node": {"type": "string"}, "relay": {"type": "string"}, "on": {"type": "boolean"}},
                 ["node", "relay", "on"]),
            tool("node.read_sensor", "Read a sensor connected to a node.",
                 {"node": {"type": "string"}, "sensor": {"type": "string"}},
                 ["node", "sensor"]),
        ]

    async def execute(self, name: str, args: dict) -> dict:
        node = args.get("node", "unknown")
        result = await self.dispatch(node, name, args)
        log.info("→ node command %s (%s) → %s", name, args, result["command_id"])
        return result
