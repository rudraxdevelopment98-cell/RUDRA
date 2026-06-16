"""
Memory store — RUDRA's short- and long-term memory.

Holds three things:
  1. Conversation turns  — recent context for the brain.
  2. Device registry     — which agents are online and what they can do.
  3. Preferences         — user settings RUDRA should remember.

Phase 0: in-memory stub. Phase 1: back it with SQLite at config.db_path.
"""
from __future__ import annotations

import time

from core.log import get_logger

log = get_logger("rudra.memory")


class Memory:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._turns: list[dict] = []       # TODO(Phase 1): persist to SQLite
        self._devices: dict[str, dict] = {}

    async def init(self) -> None:
        # TODO(Phase 1): open SQLite, create tables (turns, devices, prefs).
        log.info("🧠 (stub) memory ready (db=%s)", self.db_path)

    async def close(self) -> None:
        log.info("🧠 memory closed")

    # --- conversation ---
    async def add_turn(self, role: str, text: str) -> None:
        self._turns.append({"role": role, "text": text, "ts": int(time.time())})

    async def recent_turns(self, limit: int = 10) -> list[dict]:
        return self._turns[-limit:]

    # --- device registry ---
    async def register_device(self, device: str, info: dict) -> None:
        self._devices[device] = {**info, "seen": int(time.time())}
        log.info("📟 registered device %s (%s)", device, info.get("domain", "?"))

    async def online_devices(self) -> dict[str, dict]:
        return dict(self._devices)
