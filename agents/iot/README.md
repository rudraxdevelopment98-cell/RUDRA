# RUDRA — IoT Agent (Home Assistant bridge)

Turns RUDRA bus Commands into Home Assistant service calls, so RUDRA can control
anything Home Assistant already knows about — lights, plugs, sensors, scenes.

## What it does
Connects to the MQTT bus, registers as `home-assistant`, listens on
`rudra/iot/home-assistant/cmd`, calls the HA REST API, and reports results back.

| Tool             | Home Assistant call                          |
|------------------|----------------------------------------------|
| `iot.set_light`  | `light.turn_on` / `light.turn_off` (`brightness_pct`) |
| `iot.set_switch` | `switch.turn_on` / `switch.turn_off`         |
| `iot.read_sensor`| `GET /api/states/<sensor>` → value + unit    |
| `iot.run_scene`  | `scene.turn_on`                              |

## Entity resolution
You say "bedroom"; the agent maps it to an entity id (e.g. `light.bedroom`) by
matching the spoken name against each entity's `friendly_name` or id, falling
back to `<domain>.<slug>`. Pass a full entity id to be explicit.

## Setup
```bash
pip install -r requirements.txt
export MQTT_HOST=<broker-host>
export HA_URL=http://homeassistant.local:8123
export HA_TOKEN=<long-lived access token>   # HA → profile → Long-Lived Access Tokens
python agent.py
```

Status: 🟢 implemented (Phase 4).
