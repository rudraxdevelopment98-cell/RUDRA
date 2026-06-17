"""
RUDRA Node Simulator — a software stand-in for `rudra_node.ino`.

Speaks the exact same bus protocol as the real ESP32 firmware (same topics,
same actions, same event shape) but keeps "pin state" in memory instead of on
real GPIO. Useful for:
  - developing the `node`/`electronics` skill before you have hardware,
  - integration testing the full bus round-trip,
  - a software-only node (e.g. a virtual relay) if you never wire up a board.

Run:
    pip install -r requirements.txt   # (shared with agents/pc-agent: aiomqtt)
    export MQTT_HOST=...
    export RUDRA_NODE_ID=esp32-desk
    python node_sim.py
"""
from __future__ import annotations

import asyncio
import json
import os
import time
import uuid

NODE_ID = os.environ.get("RUDRA_NODE_ID", "esp32-desk")
MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_USERNAME = os.environ.get("MQTT_USERNAME") or None
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD") or None

CMD_TOPIC = f"rudra/node/{NODE_ID}/cmd"
EVENT_TOPIC = f"rudra/node/{NODE_ID}/event"
STATE_TOPIC = f"rudra/node/{NODE_ID}/state"
REGISTER_TOPIC = "rudra/system/all/register"

CAPABILITIES = ["node.set_pin", "node.set_relay", "node.read_sensor"]

# Named relays this simulated node "has". Matches config.example.h's RELAYS.
RELAYS = {"desk": 26, "lamp": 27}
# Named sensors and a function returning a (fake) reading.
SENSORS = {"temp": lambda: 512}


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:6]}"


def register_payload() -> dict:
    return {
        "device": NODE_ID,
        "domain": "node",
        "capabilities": CAPABILITIES,
        "meta": {"relays": len(RELAYS), "sensors": len(SENSORS), "agent": "0.1.0-sim"},
    }


class Node:
    """Holds pin/relay state. Pure logic, no I/O — easy to unit test."""

    def __init__(self):
        self.pins: dict[int, int] = {}
        self.relays: dict[str, bool] = {name: False for name in RELAYS}

    def ok(self, result: dict) -> dict:
        return {"ok": True, "result": result, "error": None}

    def err(self, message: str) -> dict:
        return {"ok": False, "result": None, "error": message}

    def handle(self, cmd: dict) -> dict:
        action = cmd.get("action")
        args = cmd.get("args") or {}

        if action == "node.set_pin":
            pin, value = int(args["pin"]), int(args["value"])
            self.pins[pin] = value
            event = self.ok({"pin": pin, "value": value})

        elif action == "node.set_relay":
            relay, on = args.get("relay"), bool(args.get("on"))
            if relay not in RELAYS:
                event = self.err("unknown relay")
            else:
                self.relays[relay] = on
                event = self.ok({"relay": relay, "on": on})

        elif action == "node.read_sensor":
            sensor = args.get("sensor")
            if sensor not in SENSORS:
                event = self.err("unknown sensor")
            else:
                event = self.ok({"sensor": sensor, "value": SENSORS[sensor]()})

        else:
            event = self.err("unknown action")

        event.update({"id": new_id("evt"), "ts": int(time.time()), "in_reply_to": cmd.get("id")})
        return event

    def state(self) -> dict:
        return {"relays": dict(self.relays)}


async def main() -> None:
    import aiomqtt

    node = Node()
    print(f"[node-sim] {NODE_ID} — connecting to {MQTT_HOST}:{MQTT_PORT}")
    async with aiomqtt.Client(
        hostname=MQTT_HOST, port=MQTT_PORT,
        username=MQTT_USERNAME, password=MQTT_PASSWORD,
    ) as client:
        await client.publish(REGISTER_TOPIC, json.dumps(register_payload()))
        await client.publish(STATE_TOPIC, json.dumps(node.state()), retain=True)
        await client.subscribe(CMD_TOPIC)
        print(f"[node-sim] online. relays: {list(RELAYS)}  sensors: {list(SENSORS)}")
        async for message in client.messages:
            try:
                cmd = json.loads(message.payload)
            except (json.JSONDecodeError, TypeError):
                continue
            event = node.handle(cmd)
            reply_to = cmd.get("reply_to") or EVENT_TOPIC
            await client.publish(reply_to, json.dumps(event))
            await client.publish(STATE_TOPIC, json.dumps(node.state()), retain=True)
            print(f"[node-sim] {cmd.get('action')} → ok={event['ok']}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[node-sim] shutting down")
