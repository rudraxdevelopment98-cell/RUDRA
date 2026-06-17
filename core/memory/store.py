"""
Memory store — RUDRA's short- and long-term memory.

Holds three things:
  1. Conversation turns  — recent context for the brain.
  2. Device registry     — which agents are online and what they can do.
  3. Preferences         — user settings RUDRA should remember.

Backed by SQLite via the stdlib (no extra dependency). All blocking DB calls run
in a thread so they never stall the async event loop.
"""
from __future__ import annotations

import asyncio
import sqlite3
import time

from core.log import get_logger

log = get_logger("rudra.memory")


class Memory:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._db: sqlite3.Connection | None = None

    async def init(self) -> None:
        self._db = await asyncio.to_thread(self._connect)
        await asyncio.to_thread(self._create_tables)
        log.info("🧠 memory ready (db=%s)", self.db_path)

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.db_path, check_same_thread=False)
        db.row_factory = sqlite3.Row
        return db

    def _create_tables(self) -> None:
        assert self._db is not None
        self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS turns (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                role  TEXT NOT NULL,      -- 'user' | 'assistant'
                text  TEXT NOT NULL,
                ts    INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS devices (
                device   TEXT PRIMARY KEY,
                domain   TEXT,
                caps     TEXT,            -- JSON list of capabilities
                seen     INTEGER
            );
            CREATE TABLE IF NOT EXISTS prefs (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
            """
        )
        self._db.commit()

    async def close(self) -> None:
        if self._db is not None:
            await asyncio.to_thread(self._db.close)
        log.info("🧠 memory closed")

    # --- conversation ---
    async def add_turn(self, role: str, text: str) -> None:
        await asyncio.to_thread(self._insert_turn, role, text)

    def _insert_turn(self, role: str, text: str) -> None:
        assert self._db is not None
        self._db.execute(
            "INSERT INTO turns (role, text, ts) VALUES (?, ?, ?)",
            (role, text, int(time.time())),
        )
        self._db.commit()

    async def recent_turns(self, limit: int = 10) -> list[dict]:
        """Return the last `limit` turns oldest→newest as {role, content} dicts."""
        rows = await asyncio.to_thread(self._fetch_turns, limit)
        return [{"role": r["role"], "content": r["text"]} for r in rows]

    def _fetch_turns(self, limit: int) -> list[sqlite3.Row]:
        assert self._db is not None
        cur = self._db.execute(
            "SELECT role, text FROM turns ORDER BY id DESC LIMIT ?", (limit,)
        )
        return list(reversed(cur.fetchall()))

    # --- device registry ---
    async def register_device(self, device: str, info: dict) -> None:
        import json

        await asyncio.to_thread(
            self._upsert_device,
            device,
            info.get("domain", ""),
            json.dumps(info.get("capabilities", [])),
        )
        log.info("📟 registered device %s (%s)", device, info.get("domain", "?"))

    def _upsert_device(self, device: str, domain: str, caps: str) -> None:
        assert self._db is not None
        self._db.execute(
            "INSERT INTO devices (device, domain, caps, seen) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(device) DO UPDATE SET domain=?, caps=?, seen=?",
            (device, domain, caps, int(time.time()), domain, caps, int(time.time())),
        )
        self._db.commit()

    async def online_devices(self) -> dict[str, dict]:
        import json

        rows = await asyncio.to_thread(self._fetch_devices)
        return {
            r["device"]: {
                "domain": r["domain"],
                "capabilities": json.loads(r["caps"] or "[]"),
                "seen": r["seen"],
            }
            for r in rows
        }

    def _fetch_devices(self) -> list[sqlite3.Row]:
        assert self._db is not None
        return list(self._db.execute("SELECT * FROM devices").fetchall())

    # --- preferences / long-term facts ---
    async def set_pref(self, key: str, value: str) -> None:
        await asyncio.to_thread(self._set_pref, key, value)

    def _set_pref(self, key: str, value: str) -> None:
        assert self._db is not None
        self._db.execute(
            "INSERT INTO prefs (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=?",
            (key, value, value),
        )
        self._db.commit()

    async def get_pref(self, key: str) -> str | None:
        return await asyncio.to_thread(self._get_pref, key)

    def _get_pref(self, key: str) -> str | None:
        assert self._db is not None
        row = self._db.execute("SELECT value FROM prefs WHERE key=?", (key,)).fetchone()
        return row["value"] if row else None

    async def all_prefs(self) -> dict[str, str]:
        return await asyncio.to_thread(self._all_prefs)

    def _all_prefs(self) -> dict[str, str]:
        assert self._db is not None
        rows = self._db.execute("SELECT key, value FROM prefs ORDER BY key").fetchall()
        return {r["key"]: r["value"] for r in rows}

    async def delete_pref(self, key: str) -> bool:
        return await asyncio.to_thread(self._delete_pref, key)

    def _delete_pref(self, key: str) -> bool:
        assert self._db is not None
        cur = self._db.execute("DELETE FROM prefs WHERE key=?", (key,))
        self._db.commit()
        return cur.rowcount > 0
