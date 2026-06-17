"""
Phase 5 tests — custom electronics, no real ESP32 needed.

Drives the `node` skill against `agents/esp32/node_sim.py`'s `Node` class,
which implements the exact same command/event contract as the real firmware
(rudra_node.ino) but keeps state in memory. Covers set_pin, set_relay (incl.
unknown relay), read_sensor (incl. unknown sensor + the request/reply skill
path), and unknown actions.

Run:
    python -m tests.test_phase5
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


def _load_node_sim():
    here = os.path.dirname(__file__)
    path = os.path.join(here, "..", "agents", "esp32", "node_sim.py")
    spec = importlib.util.spec_from_file_location("node_sim", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["node_sim"] = module
    spec.loader.exec_module(module)
    return module


async def run() -> None:
    print("node simulator (pure logic, mirrors the firmware contract):")
    sim = _load_node_sim()
    node = sim.Node()

    e = node.handle({"id": "c1", "action": "node.set_pin", "args": {"pin": 5, "value": 1}})
    check("set_pin succeeds and records state", e["ok"] and node.pins[5] == 1)
    check("event echoes the command id", e["in_reply_to"] == "c1")

    e = node.handle({"id": "c2", "action": "node.set_relay", "args": {"relay": "desk", "on": True}})
    check("set_relay turns on a configured relay", e["ok"] and node.relays["desk"] is True)
    check("state() reflects the relay", node.state()["relays"]["desk"] is True)

    e = node.handle({"id": "c3", "action": "node.set_relay", "args": {"relay": "nope", "on": True}})
    check("unknown relay is rejected", e["ok"] is False and "unknown relay" in e["error"])

    e = node.handle({"id": "c4", "action": "node.read_sensor", "args": {"sensor": "temp"}})
    check("read_sensor returns a value", e["ok"] and e["result"]["value"] == 512)

    e = node.handle({"id": "c5", "action": "node.read_sensor", "args": {"sensor": "nope"}})
    check("unknown sensor is rejected", e["ok"] is False and "unknown sensor" in e["error"])

    e = node.handle({"id": "c6", "action": "node.bogus", "args": {}})
    check("unknown action returns an error event", e["ok"] is False and "unknown action" in e["error"])

    print("node skill (bus stub mode — no broker/board):")
    cfg = Config()
    cfg.db_path = os.path.join(tempfile.mkdtemp(), "test.db")
    mem = Memory(cfg.db_path)
    await mem.init()
    bus = Bus(cfg)
    await bus.connect()
    skills = load_skills(bus, mem)

    r = await skills["node"].execute("node.set_relay", {"node": "esp32-desk", "relay": "desk", "on": True})
    check("set_relay dispatches without a confirmation prompt",
          r["ok"] and r["status"] == "dispatched")

    r = await skills["node"].execute("node.read_sensor", {"node": "esp32-desk", "sensor": "temp"})
    check("read_sensor uses request() and degrades gracefully with no agent",
          r["ok"] and r["status"] == "dispatched")

    await bus.disconnect()
    await mem.close()

    print()
    if _failures:
        print(f"{FAIL} {_failures} check(s) failed")
        raise SystemExit(1)
    print(f"{PASS} all Phase 5 checks passed")


if __name__ == "__main__":
    asyncio.run(run())
