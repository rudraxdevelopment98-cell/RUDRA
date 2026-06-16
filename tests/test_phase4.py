"""
Phase 4 tests — smart-home / IoT, no broker or Home Assistant needed.

Covers the bus request/reply correlation, the IoT skill's request path (graceful
when no broker), and the IoT agent's handlers driven by a fake Home Assistant
client (entity resolution, light/switch/sensor/scene, unknown action).

Run:
    python -m tests.test_phase4
"""
from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
import tempfile

from core.bus.mqtt import Bus
from core.config import Config
from core.memory.store import Memory
from core.skills import load_skills

PASS, FAIL = "✅", "❌"
_failures = 0


def check(name: str, cond: bool) -> None:
    global _failures
    print(f"  {PASS if cond else FAIL} {name}")
    if not cond:
        _failures += 1


def _load_iot_agent():
    here = os.path.dirname(__file__)
    path = os.path.join(here, "..", "agents", "iot", "agent.py")
    spec = importlib.util.spec_from_file_location("iot_agent", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["iot_agent"] = module
    spec.loader.exec_module(module)
    return module


class FakeHA:
    """Stands in for Home Assistant — records calls, returns canned states."""

    def __init__(self):
        self.calls: list[tuple] = []
        self._states = {
            "sensor.living_room_temperature": {
                "entity_id": "sensor.living_room_temperature",
                "state": "21.5",
                "attributes": {"unit_of_measurement": "°C",
                               "friendly_name": "Living Room Temperature"},
            },
            "light.bedroom": {
                "entity_id": "light.bedroom",
                "state": "off",
                "attributes": {"friendly_name": "Bedroom"},
            },
        }

    def call_service(self, domain, service, data):
        self.calls.append((domain, service, data))
        return []

    def get_state(self, entity_id):
        return self._states.get(entity_id, {"entity_id": entity_id, "state": "unknown", "attributes": {}})

    def list_states(self):
        return list(self._states.values())

    # reuse the real resolver by binding it later
    resolve = None


async def run() -> None:
    print("bus request/reply (stub mode):")
    cfg = Config()
    cfg.db_path = os.path.join(tempfile.mkdtemp(), "test.db")
    mem = Memory(cfg.db_path)
    await mem.init()
    bus = Bus(cfg)
    await bus.connect()  # stub — no broker

    reply = await bus.request("rudra/iot/home-assistant/cmd",
                              {"action": "iot.read_sensor", "args": {}}, timeout=0.2)
    check("request returns None in stub mode (no broker)", reply is None)

    skills = load_skills(bus, mem)
    r = await skills["iot"].execute("iot.set_light", {"area": "bedroom", "on": True})
    check("iot skill degrades to 'dispatched' with no agent",
          r["ok"] and r["status"] == "dispatched")

    print("iot agent handlers (fake Home Assistant):")
    agent = _load_iot_agent()
    ha = FakeHA()
    ha.resolve = lambda domain, name: agent.HomeAssistant.resolve(ha, domain, name)

    e = agent.handle_command(
        {"id": "c1", "action": "iot.set_light", "args": {"area": "bedroom", "on": True, "brightness": 40}}, ha)
    check("set_light resolves friendly name → light.bedroom",
          e["ok"] and e["result"]["entity_id"] == "light.bedroom")
    check("set_light on calls light.turn_on with brightness_pct",
          ("light", "turn_on", {"entity_id": "light.bedroom", "brightness_pct": 40}) in ha.calls)
    check("event echoes the command id", e["in_reply_to"] == "c1")

    e = agent.handle_command({"id": "c2", "action": "iot.set_light", "args": {"area": "bedroom", "on": False}}, ha)
    check("set_light off calls light.turn_off",
          ("light", "turn_off", {"entity_id": "light.bedroom"}) in ha.calls)

    e = agent.handle_command(
        {"id": "c3", "action": "iot.read_sensor", "args": {"name": "living room temperature"}}, ha)
    check("read_sensor returns the value + unit",
          e["ok"] and e["result"]["state"] == "21.5" and e["result"]["unit"] == "°C")

    e = agent.handle_command({"id": "c4", "action": "iot.set_switch", "args": {"name": "fan", "on": True}}, ha)
    check("set_switch builds switch.fan and turns it on",
          e["ok"] and ("switch", "turn_on", {"entity_id": "switch.fan"}) in ha.calls)

    e = agent.handle_command({"id": "c5", "action": "iot.run_scene", "args": {"name": "movie night"}}, ha)
    check("run_scene activates scene.movie_night",
          e["ok"] and ("scene", "turn_on", {"entity_id": "scene.movie_night"}) in ha.calls)

    e = agent.handle_command({"id": "c6", "action": "iot.bogus", "args": {}}, ha)
    check("unknown action returns an error event", e["ok"] is False and "unknown" in e["error"])

    await bus.disconnect()
    await mem.close()

    print()
    if _failures:
        print(f"{FAIL} {_failures} check(s) failed")
        raise SystemExit(1)
    print(f"{PASS} all Phase 4 checks passed")


if __name__ == "__main__":
    asyncio.run(run())
