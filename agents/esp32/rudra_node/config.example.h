/*
 * Copy this file to  config.h  and fill in your values.
 * config.h is git-ignored so your Wi-Fi / broker details stay private.
 */
#pragma once

#define WIFI_SSID  "your-wifi-name"
#define WIFI_PASS  "your-wifi-password"

#define MQTT_HOST  "192.168.1.10"   // the machine running the RUDRA brain/broker
#define MQTT_PORT  1883

#define NODE_ID    "esp32-desk"      // unique id for this board

// --- Relays / digital outputs you've wired up ---
// Add one line per relay: name (what you'll say) -> GPIO pin.
// "Rudra, turn on the desk relay" -> RELAYS[i].name == "desk"
struct RelayDef { const char* name; uint8_t pin; };
static const RelayDef RELAYS[] = {
  {"desk",  26},
  {"lamp",  27},
};
#define NUM_RELAYS (sizeof(RELAYS) / sizeof(RELAYS[0]))

// --- Sensors you've wired up ---
// "temp" reads analog pin 34 and reports the raw ADC value (scale in your
// skill/orchestrator, or extend readSensor() below for a real sensor lib).
struct SensorDef { const char* name; uint8_t pin; };
static const SensorDef SENSORS[] = {
  {"temp", 34},
};
#define NUM_SENSORS (sizeof(SENSORS) / sizeof(SENSORS[0]))

// How often to publish retained state (ms).
#define STATE_INTERVAL_MS 30000
