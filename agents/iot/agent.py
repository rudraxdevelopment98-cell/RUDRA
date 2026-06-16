"""
RUDRA IoT Agent — bridges the bus to Home Assistant.

Home Assistant already speaks to thousands of devices (lights, plugs, sensors,
locks, scenes). This agent turns RUDRA bus Commands into Home Assistant REST API
calls and reports the result back as Events, so the brain stays vendor-neutral.

It:
  1. connects to the MQTT bus,
  2. registers itself as `home-assistant`,
  3. listens on  rudra/iot/home-assistant/cmd,
  4. calls the HA REST API,
  5. replies on the command's reply_to topic (an Event).

Run:
    pip install -r requirements.txt
    export MQTT_HOST=...                       # the broker
    export HA_URL=http://homeassistant.local:8123
    export HA_TOKEN=<long-lived access token>  # HA → profile → Long-Lived Tokens
    python agent.py
"""
from __future__ import annotations

import asyncio
import json
import os
import time
import urllib.error
import urllib.request
import uuid

DEVICE_ID = "home-assistant"
MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_USERNAME = os.environ.get("MQTT_USERNAME") or None
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD") or None

HA_URL = os.environ.get("HA_URL", "http://localhost:8123").rstrip("/")
HA_TOKEN = os.environ.get("HA_TOKEN", "")

CMD_TOPIC = f"rudra/iot/{DEVICE_ID}/cmd"
REGISTER_TOPIC = "rudra/system/all/register"

CAPABILITIES = ["iot.set_light", "iot.set_switch", "iot.read_sensor", "iot.run_scene"]


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:6]}"


def register_payload() -> dict:
    return {
        "device": DEVICE_ID,
        "domain": "iot",
        "capabilities": CAPABILITIES,
        "meta": {"bridge": "home-assistant", "agent": "0.1.0"},
    }


def ok(result: dict) -> dict:
    return {"ok": True, "result": result, "error": None}


def err(message: str) -> dict:
    return {"ok": False, "result": None, "error": message}


def slug(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


# --- Home Assistant REST client ----------------------------------------------

class HomeAssistant:
    def __init__(self, url: str = HA_URL, token: str = HA_TOKEN):
        self.url = url.rstrip("/")
        self.token = token

    def _request(self, method: str, path: str, data: dict | None = None):
        body = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(f"{self.url}{path}", data=body, method=method)
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}

    def call_service(self, domain: str, service: str, data: dict) -> list:
        return self._request("POST", f"/api/services/{domain}/{service}", data)

    def get_state(self, entity_id: str) -> dict:
        return self._request("GET", f"/api/states/{entity_id}")

    def list_states(self) -> list:
        return self._request("GET", "/api/states")

    def resolve(self, domain: str, name: str) -> str:
        """Best-effort map a spoken name/area to a `<domain>.<entity>` id."""
        if "." in name:
            return name
        target = slug(name)
        try:
            for st in self.list_states():
                eid = st.get("entity_id", "")
                if not eid.startswith(f"{domain}."):
                    continue
                friendly = slug(st.get("attributes", {}).get("friendly_name", ""))
                if target == friendly or target in eid:
                    return eid
        except (urllib.error.URLError, OSError, ValueError):
            pass  # fall through to a constructed id
        return f"{domain}.{target}"


# --- action handlers ----------------------------------------------------------

def do_set_light(args: dict, ha: HomeAssistant) -> dict:
    entity = ha.resolve("light", args.get("area", ""))
    if args.get("on"):
        data = {"entity_id": entity}
        if "brightness" in args and args["brightness"] is not None:
            data["brightness_pct"] = max(0, min(100, int(args["brightness"])))
        ha.call_service("light", "turn_on", data)
        return ok({"entity_id": entity, "on": True, "brightness": args.get("brightness")})
    ha.call_service("light", "turn_off", {"entity_id": entity})
    return ok({"entity_id": entity, "on": False})


def do_set_switch(args: dict, ha: HomeAssistant) -> dict:
    entity = ha.resolve("switch", args.get("name", ""))
    service = "turn_on" if args.get("on") else "turn_off"
    ha.call_service("switch", service, {"entity_id": entity})
    return ok({"entity_id": entity, "on": bool(args.get("on"))})


def do_read_sensor(args: dict, ha: HomeAssistant) -> dict:
    entity = ha.resolve("sensor", args.get("name", ""))
    state = ha.get_state(entity)
    attrs = state.get("attributes", {})
    return ok({
        "entity_id": entity,
        "state": state.get("state"),
        "unit": attrs.get("unit_of_measurement"),
        "name": attrs.get("friendly_name", entity),
    })


def do_run_scene(args: dict, ha: HomeAssistant) -> dict:
    entity = ha.resolve("scene", args.get("name", ""))
    ha.call_service("scene", "turn_on", {"entity_id": entity})
    return ok({"scene": entity})


HANDLERS = {
    "iot.set_light": do_set_light,
    "iot.set_switch": do_set_switch,
    "iot.read_sensor": do_read_sensor,
    "iot.run_scene": do_run_scene,
}


def handle_command(cmd: dict, ha: HomeAssistant) -> dict:
    """Execute one command against Home Assistant, return an Event dict."""
    action = cmd.get("action")
    args = cmd.get("args") or {}
    handler = HANDLERS.get(action)
    if not handler:
        event = err(f"unknown action: {action}")
    else:
        try:
            event = handler(args, ha)
        except urllib.error.HTTPError as exc:
            event = err(f"Home Assistant rejected {action}: HTTP {exc.code}")
        except (urllib.error.URLError, OSError) as exc:
            event = err(f"cannot reach Home Assistant: {exc}")
        except Exception as exc:  # noqa: BLE001
            event = err(f"{action} failed: {exc}")
    event.update({"id": new_id("evt"), "ts": int(time.time()), "in_reply_to": cmd.get("id")})
    return event


async def main() -> None:
    import aiomqtt

    if not HA_TOKEN:
        print("[iot-agent] WARNING: HA_TOKEN is not set — calls will be rejected.")
    ha = HomeAssistant()
    print(f"[iot-agent] bridging {HA_URL} via {MQTT_HOST}:{MQTT_PORT}")
    async with aiomqtt.Client(
        hostname=MQTT_HOST, port=MQTT_PORT,
        username=MQTT_USERNAME, password=MQTT_PASSWORD,
    ) as client:
        await client.publish(REGISTER_TOPIC, json.dumps(register_payload()))
        await client.subscribe(CMD_TOPIC)
        print(f"[iot-agent] online. capabilities: {', '.join(CAPABILITIES)}")
        async for message in client.messages:
            try:
                cmd = json.loads(message.payload)
            except (json.JSONDecodeError, TypeError):
                continue
            # Run the blocking HTTP call off the event loop.
            event = await asyncio.to_thread(handle_command, cmd, ha)
            reply_to = cmd.get("reply_to") or f"rudra/iot/{DEVICE_ID}/event"
            await client.publish(reply_to, json.dumps(event))
            print(f"[iot-agent] {cmd.get('action')} → ok={event['ok']}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[iot-agent] shutting down")
