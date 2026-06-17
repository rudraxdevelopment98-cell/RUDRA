"""
Recall skill — RUDRA's long-term memory of facts and preferences.

Runs inside the brain (no device needed), backed by the prefs table in the
memory store. This is what lets RUDRA accumulate context about you over time —
your name, where things are, how you like things done — instead of starting
fresh every conversation. The brain can write a fact when you tell it something
worth keeping, and read it back later.
"""
from __future__ import annotations

from core.log import get_logger
from core.skills.base import Skill, tool

log = get_logger("rudra.skill.recall")


class RecallSkill(Skill):
    domain = "recall"

    def tools(self) -> list[dict]:
        return [
            tool("recall.remember",
                 "Store a fact or preference to remember long-term (e.g. the "
                 "user's name, home city, a default, where something is). Use a "
                 "short snake_case key and a concise value.",
                 {
                     "key": {"type": "string",
                             "description": "Short identifier, e.g. 'user_name' or 'home_city'."},
                     "value": {"type": "string", "description": "The fact to remember."},
                 },
                 ["key", "value"]),
            tool("recall.get",
                 "Look up a single remembered fact by its key.",
                 {"key": {"type": "string", "description": "The key to look up."}},
                 ["key"]),
            tool("recall.list",
                 "List everything RUDRA currently remembers about the user.", {}),
            tool("recall.forget",
                 "Delete a remembered fact by its key.",
                 {"key": {"type": "string", "description": "The key to forget."}},
                 ["key"]),
        ]

    async def execute(self, name: str, args: dict) -> dict:
        if name == "recall.remember":
            key = (args.get("key") or "").strip()
            value = (args.get("value") or "").strip()
            if not key or not value:
                return {"ok": False, "error": "both key and value are required"}
            await self.memory.set_pref(key, value)
            log.info("📝 remembered %s = %s", key, value)
            return {"ok": True, "result": {"remembered": {key: value}}}

        if name == "recall.get":
            key = (args.get("key") or "").strip()
            value = await self.memory.get_pref(key)
            if value is None:
                return {"ok": True, "result": {"found": False, "key": key}}
            return {"ok": True, "result": {"found": True, "key": key, "value": value}}

        if name == "recall.list":
            prefs = await self.memory.all_prefs()
            return {"ok": True, "result": {"count": len(prefs), "facts": prefs}}

        if name == "recall.forget":
            key = (args.get("key") or "").strip()
            deleted = await self.memory.delete_pref(key)
            return {"ok": True, "result": {"forgotten": deleted, "key": key}}

        return {"ok": False, "error": f"unknown recall action: {name}"}
