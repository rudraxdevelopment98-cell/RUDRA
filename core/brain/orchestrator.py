"""
The orchestrator — RUDRA's decision loop.

One public method, `handle(text)`:
    user text  →  Claude (with tools)  →  skills execute tools  →  spoken reply

It coordinates only: device logic lives in skills, hardware lives in agents.
"""
from __future__ import annotations

from core.brain.intents import build_tool_catalogue
from core.brain.llm import LLM, LLMResponse
from core.bus.mqtt import Bus
from core.bus.topics import REGISTER_ALL, sub_all, EVENT
from core.config import Config
from core.log import get_logger
from core.memory.store import Memory

log = get_logger("rudra.brain.orchestrator")


class Orchestrator:
    def __init__(self, config: Config, bus: Bus, memory: Memory, skills: dict):
        self.config = config
        self.bus = bus
        self.memory = memory
        self.skills = skills
        self.llm = LLM(config)
        self._tools = build_tool_catalogue(skills)
        self._pending: dict | None = None  # a dangerous action awaiting "confirm"
        self._wire_bus()

    def _wire_bus(self) -> None:
        """Listen for agents announcing themselves and reporting results."""
        self.bus.subscribe(REGISTER_ALL, self._on_register)
        self.bus.subscribe(sub_all(EVENT), self._on_event)

    async def _on_register(self, topic: str, payload: dict) -> None:
        device = payload.get("device")
        if device:
            await self.memory.register_device(device, payload)

    async def _on_event(self, topic: str, payload: dict) -> None:
        ok = payload.get("ok")
        log.info("📨 event on %s: ok=%s %s", topic, ok, payload.get("result") or payload.get("error"))

    async def handle(self, text: str) -> str:
        """Process one user utterance and return the spoken reply."""
        text = text.strip()
        if not text:
            return ""
        log.info("➡  user: %s", text)

        history = await self.memory.recent_turns()
        history = await self._with_memory(history)
        response: LLMResponse = await self.llm.think(
            text, self._tools, history, self._execute_tool
        )

        await self.memory.add_turn("user", text)
        await self.memory.add_turn("assistant", response.text)
        log.info("⬅  rudra: %s", response.text)
        return response.text

    async def _with_memory(self, history: list[dict]) -> list[dict]:
        """Prepend remembered facts so RUDRA recalls them without being asked."""
        prefs = await self.memory.all_prefs()
        if not prefs:
            return history
        facts = "; ".join(f"{k} = {v}" for k, v in prefs.items())
        primer = [
            {"role": "user", "content": f"Things you remember about me: {facts}."},
            {"role": "assistant", "content": "Noted — I'll keep those in mind."},
        ]
        return primer + history

    async def _execute_tool(self, name: str, args: dict) -> dict:
        """Route one tool call (e.g. 'pc.open_app') to the owning skill."""
        # Confirmation is cross-cutting, so the orchestrator owns it.
        if name == "system.confirm":
            return await self._confirm_pending()
        if name == "system.cancel":
            return self._cancel_pending()

        domain = name.split(".", 1)[0] if "." in name else name
        skill = self.skills.get(domain)
        if not skill:
            return {"ok": False, "error": f"no skill owns tool '{name}'"}
        try:
            result = await skill.execute(name, args)
        except Exception as exc:  # noqa: BLE001 — surface any skill error to the brain
            log.exception("skill %s failed on %s", domain, name)
            return {"ok": False, "error": str(exc)}

        # A skill asked for confirmation → stash it and prompt the user.
        if result.get("status") == "needs_confirmation":
            self._pending = result["pending"]
            return {"ok": True, "result": {
                "needs_confirmation": True, "message": result["message"]}}
        return result

    async def _confirm_pending(self) -> dict:
        if not self._pending:
            return {"ok": True, "result": {"message": "There's nothing waiting for confirmation."}}
        pending, self._pending = self._pending, None
        skill = self.skills.get(pending["domain"])
        if not skill:
            return {"ok": False, "error": f"no skill owns '{pending['domain']}'"}
        log.info("✅ confirmed: %s on %s", pending["action"], pending["device"])
        return await skill.dispatch(
            pending["device"], pending["action"], pending["args"], confirmed=True)

    def _cancel_pending(self) -> dict:
        had = self._pending is not None
        self._pending = None
        msg = "Cancelled." if had else "There was nothing to cancel."
        return {"ok": True, "result": {"message": msg}}
