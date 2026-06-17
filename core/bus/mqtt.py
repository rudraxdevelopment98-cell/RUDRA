"""
MQTT bus wrapper.

Every command and event flows through here. The rest of RUDRA uses four calls:
    await bus.connect()
    await bus.publish(topic, payload_dict)
    bus.subscribe(topic_pattern, handler)   # pattern may use + and # wildcards
    await bus.disconnect()

Backed by aiomqtt. If a broker isn't reachable (or aiomqtt isn't installed) the
bus falls back to a local **stub** that just logs — so the brain, REPL, and CI
keep working headless without a broker. Set RUDRA_BUS_REQUIRED=true to make a
missing broker a hard error instead.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from typing import Awaitable, Callable

from core.config import Config
from core.bus.topics import ROOT
from core.log import get_logger

log = get_logger("rudra.bus")

Handler = Callable[[str, dict], Awaitable[None]]


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:6]}"


def topic_matches(pattern: str, topic: str) -> bool:
    """MQTT topic match: '+' = one level, '#' = the rest (must be last)."""
    p, t = pattern.split("/"), topic.split("/")
    for i, seg in enumerate(p):
        if seg == "#":
            return True
        if i >= len(t):
            return False
        if seg != "+" and seg != t[i]:
            return False
    return len(p) == len(t)


class Bus:
    def __init__(self, config: Config):
        self.config = config
        self._client = None
        self._handlers: dict[str, Handler] = {}
        self._connected = False
        self._stub = True               # flips to False once a real client connects
        self._listen_task: asyncio.Task | None = None
        self._pending: dict[str, asyncio.Future] = {}  # cmd_id → event future

    async def connect(self) -> None:
        try:
            import aiomqtt
        except ImportError:
            log.warning("🔌 aiomqtt not installed — bus runs in stub mode (logs only).")
            self._connected = True
            return

        tls_params = None
        if self.config.mqtt_tls:
            tls_params = aiomqtt.TLSParameters()

        client = aiomqtt.Client(
            hostname=self.config.mqtt_host,
            port=self.config.mqtt_port,
            username=self.config.mqtt_username or None,
            password=self.config.mqtt_password or None,
            tls_params=tls_params,
        )
        try:
            await client.__aenter__()
            await client.subscribe(f"{ROOT}/#")
        except Exception as exc:  # noqa: BLE001 — broker may simply be down in dev
            if os.environ.get("RUDRA_BUS_REQUIRED", "").lower() == "true":
                raise
            log.warning("🔌 MQTT broker unreachable (%s) — bus runs in stub mode.", exc)
            self._connected = True
            return

        self._client = client
        self._stub = False
        self._connected = True
        self._listen_task = asyncio.create_task(self._listen())
        log.info("🔌 bus connected → mqtt://%s:%d", self.config.mqtt_host, self.config.mqtt_port)

    async def disconnect(self) -> None:
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            self._listen_task = None
        if self._client is not None:
            try:
                await self._client.__aexit__(None, None, None)
            except Exception:  # noqa: BLE001
                pass
            self._client = None
        self._connected = False
        log.info("🔌 bus disconnect")

    def subscribe(self, topic: str, handler: Handler) -> None:
        """Register an async handler for a topic pattern (may use + / # wildcards)."""
        self._handlers[topic] = handler
        log.info("📥 subscribe %s", topic)

    async def publish(self, topic: str, payload: dict) -> None:
        """Publish a JSON message. Adds id+ts if missing."""
        payload.setdefault("ts", int(time.time()))
        body = json.dumps(payload)
        if self._stub or self._client is None:
            log.info("📤 (stub) publish %s  %s", topic, body)
            return
        await self._client.publish(topic, body)
        log.info("📤 publish %s  %s", topic, body)

    async def request(self, topic: str, payload: dict, timeout: float = 5.0) -> dict | None:
        """
        Publish a Command and await the correlated Event (matched by command id).

        Returns the Event dict, or None if no reply arrives in `timeout` seconds
        or the bus is in stub mode (no broker to carry the reply).
        """
        cmd_id = payload.setdefault("id", new_id("cmd"))
        if self._stub or self._client is None:
            await self.publish(topic, payload)
            return None
        fut: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[cmd_id] = fut
        try:
            await self.publish(topic, payload)
            return await asyncio.wait_for(fut, timeout)
        except asyncio.TimeoutError:
            log.warning("⏱ no reply to %s within %.1fs", cmd_id, timeout)
            return None
        finally:
            self._pending.pop(cmd_id, None)

    async def _listen(self) -> None:
        """Background task: route each incoming message to matching handlers."""
        assert self._client is not None
        async for message in self._client.messages:
            await self._dispatch(str(message.topic), message.payload)

    async def _dispatch(self, topic: str, body) -> None:
        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, TypeError):
            log.warning("Bad JSON on %s", topic)
            return
        # Resolve any pending request waiting on this event.
        in_reply_to = payload.get("in_reply_to")
        if in_reply_to and in_reply_to in self._pending:
            fut = self._pending.get(in_reply_to)
            if fut and not fut.done():
                fut.set_result(payload)
        for pattern, handler in list(self._handlers.items()):
            if topic_matches(pattern, topic):
                try:
                    await handler(topic, payload)
                except Exception:  # noqa: BLE001 — one bad handler shouldn't kill the loop
                    log.exception("handler for %s failed", pattern)
