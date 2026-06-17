# RUDRA — ESP32 Node (custom electronics)

Firmware for an ESP32 board so RUDRA can drive your own hardware — relays,
LEDs, motors — and read sensors, all over the MQTT bus.

## Flash it
1. Arduino IDE → install board support for **ESP32**.
2. Install libraries: `PubSubClient`, `ArduinoJson` (v6+).
3. Copy `rudra_node/config.example.h` → `rudra_node/config.h`, fill in Wi-Fi +
   broker (`MQTT_HOST`) + a unique `NODE_ID`, and list your `RELAYS` /
   `SENSORS` (name → GPIO pin).
4. Open `rudra_node/rudra_node.ino`, select your board, **Upload**.

On boot the node announces itself, publishes its relay state (retained), then
listens for commands. Say e.g. *"Rudra, turn on the desk relay"*.

## No hardware yet?
`node_sim.py` is a software stand-in that speaks the exact same bus protocol
(same topics, actions, event shape) with in-memory relay/pin state instead of
real GPIO — handy for developing the `node` skill or running the test suite
without a board:
```bash
pip install -r requirements.txt
export MQTT_HOST=<broker-host>
python node_sim.py
```

## Wiring
Add a `{name, pin}` entry to `RELAYS`/`SENSORS` in `config.h` — that's the
whole mapping. `node.set_relay {"relay": "desk", "on": true}` looks up `"desk"`
in `RELAYS` and drives that pin; `node.read_sensor` does the same for `SENSORS`
(currently `analogRead`; swap in a real sensor library if you need one).

Status: 🟢 implemented (Phase 5).
