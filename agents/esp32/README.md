# RUDRA — ESP32 Node (custom electronics)

Firmware for an ESP32 board so RUDRA can drive your own hardware — relays,
LEDs, motors — and read sensors, all over the MQTT bus.

## Flash it (Phase 5)
1. Arduino IDE → install board support for **ESP32**.
2. Install libraries: `PubSubClient`, `ArduinoJson`.
3. Copy `rudra_node/config.example.h` → `rudra_node/config.h` and fill in
   Wi-Fi + broker (`MQTT_HOST`) + a unique `NODE_ID`.
4. Open `rudra_node/rudra_node.ino`, select your board, **Upload**.

On boot the node announces itself; then say e.g. *"Rudra, turn on the desk relay"*.

## Wiring
Define your pins in `setup()` and map them in the command handler
(`node.set_relay` / `node.set_pin`).

Status: 🟡 skeleton — handlers land in Phase 5.
