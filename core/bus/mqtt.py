"""
MQTT bus wrapper.

Every command and event flows through here. The rest of RUDRA uses three calls:
    await bus.connect()
    await bus.publish(topic, payload_dict)
    bus.subscribe(topic, handler)

Phase 0: stubbed (logs instead of connecting). Phase 1+: wire a real async MQTT
client (e.g. aiomqtt / asyncio-paho).
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Awaitable, Callable

from core.config import Config
from core.log import get_logger

log = get_logger("rudra.bus")

Handler = Callable[[str, dict], Awaitable[None]]


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:6]}"


class Bus:
    def __init__(self, config: Config):
        self.config = config
        self._client = None
        self._handlers: dict[str, Handler] = {}
        self._connected = False

    async def connect(self) -> None:
        # TODO(Phase 1): real connection —
        #   import aiomqtt
        #   self._client = aiomqtt.Client(self.config.mqtt_host, self.config.mqtt_port,
        #       username=self.config.mqtt_username or None,
        #       password=self.config.mqtt_password or None)
        #   await self._client.__aenter__(); start a task to dispatch messages.
        log.info("🔌 (stub) bus connect → mqtt://%s:%d", self.config.mqtt_host, self.config.mqtt_port)
        self._connected = True

    async def disconnect(self) -> None:
        log.info("🔌 bus disconnect")
        self._connected = False

    def subscribe(self, topic: str, handler: Handler) -> None:
        """Register an async handler for a topic (or wildcard)."""
        self._handlers[topic] = handler
        log.info("📥 subscribe %s", topic)
        # TODO(Phase 1): await self._client.subscribe(topic)

    async def publish(self, topic: str, payload: dict) -> None:
        """Publish a JSON message. Adds id+ts if missing."""
        payload.setdefault("ts", int(time.time()))
        body = json.dumps(payload)
        log.info("📤 publish %s  %s", topic, body)
        # TODO(Phase 1): await self._client.publish(topic, body)

    async def _on_message(self, topic: str, body: bytes) -> None:
        """Internal: route an incoming message to the right handler."""
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            log.warning("Bad JSON on %s", topic)
            return
        handler = self._handlers.get(topic)
        if handler:
            await handler(topic, payload)
