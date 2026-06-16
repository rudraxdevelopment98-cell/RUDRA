"""
Phase 3 tests — PC control + confirmation flow, no broker or desktop needed.

The bus runs in stub mode (no aiomqtt connection), so publishes just log. We test
the deterministic logic: MQTT topic matching, the dangerous-action confirmation
handshake through the orchestrator, the device-registry wiring, and the PC
agent's command handler (allow-list + the "power needs confirmation" rule).

Run:
    python -m tests.test_phase3
"""
from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
import tempfile

from core.brain.orchestrator import Orchestrator
from core.bus.mqtt import Bus, topic_matches
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


def _load_pc_agent():
    """Import agents/pc-agent/agent.py by path (it's not a package)."""
    here = os.path.dirname(__file__)
    path = os.path.join(here, "..", "agents", "pc-agent", "agent.py")
    spec = importlib.util.spec_from_file_location("pc_agent", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["pc_agent"] = module
    spec.loader.exec_module(module)
    return module


async def run() -> None:
    print("topic matching:")
    check("exact match", topic_matches("rudra/pc/main-pc/cmd", "rudra/pc/main-pc/cmd"))
    check("+ wildcard one level", topic_matches("rudra/+/+/event", "rudra/pc/main-pc/event"))
    check("# wildcard tail", topic_matches("rudra/#", "rudra/pc/main-pc/cmd"))
    check("+ does not span levels", not topic_matches("rudra/+/event", "rudra/pc/main-pc/event"))
    check("non-match different channel",
          not topic_matches("rudra/+/+/cmd", "rudra/pc/main-pc/event"))

    cfg = Config()
    cfg.db_path = os.path.join(tempfile.mkdtemp(), "test.db")
    mem = Memory(cfg.db_path)
    await mem.init()
    bus = Bus(cfg)
    await bus.connect()  # stub mode — no broker in CI
    skills = load_skills(bus, mem)
    orch = Orchestrator(cfg, bus, mem, skills)

    print("confirmation flow:")
    r = await orch._execute_tool("pc.power", {"mode": "shutdown"})
    check("power asks for confirmation, doesn't act",
          r["ok"] and r["result"].get("needs_confirmation") is True)
    check("pending action is stashed",
          orch._pending is not None and orch._pending["action"] == "pc.power")

    r = await orch._execute_tool("system.confirm", {})
    check("confirm dispatches the held command",
          r["ok"] and r["status"] == "dispatched")
    check("pending is cleared after confirm", orch._pending is None)

    r = await orch._execute_tool("system.confirm", {})
    check("confirm with nothing pending is harmless",
          r["ok"] and "nothing" in r["result"]["message"].lower())

    await orch._execute_tool("pc.power", {"mode": "lock"})
    r = orch._cancel_pending()
    check("cancel clears a pending action", orch._pending is None and "Cancelled" in r["result"]["message"])

    print("safe actions still dispatch directly:")
    r = await orch._execute_tool("pc.open_app", {"app": "code"})
    check("pc.open_app dispatches without confirmation",
          r["ok"] and r["status"] == "dispatched" and orch._pending is None)

    print("device registry wiring:")
    await orch._on_register("rudra/system/all/register", {
        "device": "main-pc", "domain": "pc", "capabilities": ["pc.open_app"]})
    devs = await mem.online_devices()
    check("register event lands in the device registry", "main-pc" in devs)

    print("pc agent handlers:")
    agent = _load_pc_agent()
    e = agent.handle_command({"id": "cmd_1", "action": "pc.open_app", "args": {"app": "notavlirus"}})
    check("non-allow-listed app is refused", e["ok"] is False and "allow-listed" in e["error"])
    check("event echoes the command id", e["in_reply_to"] == "cmd_1")

    e = agent.handle_command({"id": "cmd_2", "action": "pc.power",
                              "args": {"mode": "shutdown"}, "confirmed": False})
    check("power without confirmed is refused", e["ok"] is False and "confirm" in e["error"].lower())

    e = agent.handle_command({"id": "cmd_3", "action": "pc.bogus", "args": {}})
    check("unknown action returns an error event", e["ok"] is False and "unknown" in e["error"])

    await bus.disconnect()
    await mem.close()

    print()
    if _failures:
        print(f"{FAIL} {_failures} check(s) failed")
        raise SystemExit(1)
    print(f"{PASS} all Phase 3 checks passed")


if __name__ == "__main__":
    asyncio.run(run())
