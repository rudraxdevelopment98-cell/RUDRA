"""
Phase 1 tests — the deterministic parts that don't need the Claude API.

Covers: SQLite memory, the system skill (real results), tool-call routing
through the orchestrator's executor, and the tool catalogue. We stub the LLM so
no API key is required.

Run:
    python -m tests.test_phase1
"""
from __future__ import annotations

import asyncio
import os
import tempfile

from core.brain.intents import build_tool_catalogue
from core.brain.orchestrator import Orchestrator
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


async def run() -> None:
    cfg = Config()
    cfg.db_path = os.path.join(tempfile.mkdtemp(), "test.db")

    # --- memory ---
    print("memory:")
    mem = Memory(cfg.db_path)
    await mem.init()
    await mem.add_turn("user", "hello")
    await mem.add_turn("assistant", "hi")
    turns = await mem.recent_turns()
    check("stores and returns turns oldest→newest",
          [t["content"] for t in turns] == ["hello", "hi"])
    check("turn shape is {role, content}", turns[0] == {"role": "user", "content": "hello"})
    await mem.register_device("esp32-desk", {"domain": "node", "capabilities": ["node.set_pin"]})
    devs = await mem.online_devices()
    check("registers a device", "esp32-desk" in devs and devs["esp32-desk"]["domain"] == "node")

    # --- skills + routing ---
    print("skills:")
    bus = Bus(cfg)
    await bus.connect()
    skills = load_skills(bus, mem)
    check("five skills load", set(skills) == {"system", "pc", "phone", "iot", "node"})

    orch = Orchestrator(cfg, bus, mem, skills)

    r = await orch._execute_tool("system.time", {})
    check("system.time returns a spoken time", r["ok"] and "spoken" in r["result"])

    r = await orch._execute_tool("system.status", {})
    check("system.status sees the registered device", r["ok"] and r["result"]["online_devices"] == 1)

    r = await orch._execute_tool("system.capabilities", {})
    check("system.capabilities lists all tools", r["ok"] and len(r["result"]["capabilities"]) >= 15)

    r = await orch._execute_tool("pc.open_app", {"app": "code"})
    check("pc.open_app dispatches to the bus", r["ok"] and r["status"] == "dispatched")

    r = await orch._execute_tool("nope.bad", {})
    check("unknown tool is handled gracefully", r["ok"] is False and "error" in r)

    # --- tool catalogue ---
    print("catalogue:")
    cat = build_tool_catalogue(skills)
    names = {t["name"] for t in cat}
    check("catalogue has system + device tools",
          {"system.time", "pc.open_app", "iot.set_light", "node.set_pin"} <= names)
    check("every tool has an input_schema", all("input_schema" in t for t in cat))

    await bus.disconnect()
    await mem.close()

    print()
    if _failures:
        print(f"{FAIL} {_failures} check(s) failed")
        raise SystemExit(1)
    print(f"{PASS} all Phase 1 checks passed")


if __name__ == "__main__":
    asyncio.run(run())
