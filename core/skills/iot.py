"""
IoT skill — smart-home devices.

Bridges to Home Assistant, which already speaks to thousands of devices
(lights, plugs, sensors, locks). The brain stays vendor-neutral.
"""
from __future__ import annotations

from core.log import get_logger
from core.skills.base import Skill, tool

log = get_logger("rudra.skill.iot")

DEFAULT_DEVICE = "home-assistant"


class IoTSkill(Skill):
    domain = "iot"

    def tools(self) -> list[dict]:
        return [
            tool("iot.set_light", "Turn a light on/off or set brightness/colour.",
                 {"area": {"type": "string", "description": "Room or light name"},
                  "on": {"type": "boolean"},
                  "brightness": {"type": "integer", "description": "0-100, optional"}},
                 ["area", "on"]),
            tool("iot.set_switch", "Turn a smart plug/switch on or off.",
                 {"name": {"type": "string"}, "on": {"type": "boolean"}},
                 ["name", "on"]),
            tool("iot.read_sensor", "Read a sensor value (temp, humidity, motion…).",
                 {"name": {"type": "string"}}, ["name"]),
            tool("iot.run_scene", "Activate a Home Assistant scene.",
                 {"name": {"type": "string"}}, ["name"]),
        ]

    async def execute(self, name: str, args: dict) -> dict:
        # IoT calls are quick and we want the result (sensor value / confirmation),
        # so use request/reply rather than fire-and-forget.
        result = await self.request(DEFAULT_DEVICE, name, args)
        log.info("→ IoT command %s (%s) → ok=%s", name, args, result.get("ok"))
        return result
