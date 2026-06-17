/*
 * RUDRA Node — ESP32 firmware
 * -----------------------------------------------------------------------------
 * A custom-electronics agent. Connects to Wi-Fi + the MQTT bus, announces
 * itself, then listens for commands to drive pins/relays and read sensors.
 *
 * Topics (see ../../../docs/PROTOCOL.md):
 *   subscribe : rudra/node/<NODE_ID>/cmd
 *   publish   : rudra/node/<NODE_ID>/event   (results)
 *               rudra/node/<NODE_ID>/state   (retained)
 *               rudra/system/all/register    (on boot)
 *
 * Build: Arduino IDE / PlatformIO. Copy config.example.h -> config.h and fill in.
 * Libraries: WiFi, PubSubClient, ArduinoJson (>=6).
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include "config.h"           // WIFI_SSID, WIFI_PASS, MQTT_HOST, MQTT_PORT, NODE_ID, RELAYS, SENSORS

WiFiClient net;
PubSubClient mqtt(net);

const String CMD_TOPIC = String("rudra/node/") + NODE_ID + "/cmd";
const String EVENT_TOPIC = String("rudra/node/") + NODE_ID + "/event";
const String STATE_TOPIC = String("rudra/node/") + NODE_ID + "/state";
const String REGISTER_TOPIC = "rudra/system/all/register";

unsigned long lastStatePublish = 0;

void connectWifi() {
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) { delay(300); }
}

void publishRegister() {
  StaticJsonDocument<256> doc;
  doc["device"] = NODE_ID;
  doc["domain"] = "node";
  JsonArray caps = doc.createNestedArray("capabilities");
  caps.add("node.set_pin");
  caps.add("node.set_relay");
  caps.add("node.read_sensor");
  JsonObject meta = doc.createNestedObject("meta");
  meta["relays"] = NUM_RELAYS;
  meta["sensors"] = NUM_SENSORS;
  meta["agent"] = "0.1.0";

  char buf[256];
  size_t n = serializeJson(doc, buf);
  mqtt.publish(REGISTER_TOPIC.c_str(), buf, n);
}

// Find a relay's pin by name, or -1 if not configured.
int relayPin(const char* name) {
  for (size_t i = 0; i < NUM_RELAYS; i++) {
    if (strcmp(RELAYS[i].name, name) == 0) return RELAYS[i].pin;
  }
  return -1;
}

int sensorPin(const char* name) {
  for (size_t i = 0; i < NUM_SENSORS; i++) {
    if (strcmp(SENSORS[i].name, name) == 0) return SENSORS[i].pin;
  }
  return -1;
}

void publishEvent(const char* inReplyTo, bool ok, JsonVariant result, const char* error) {
  StaticJsonDocument<256> doc;
  doc["id"] = String("evt_") + String(millis(), HEX);
  doc["ts"] = millis() / 1000;
  doc["in_reply_to"] = inReplyTo;
  doc["ok"] = ok;
  if (ok) doc["result"] = result;
  else doc["error"] = error;

  char buf[256];
  size_t n = serializeJson(doc, buf);
  mqtt.publish(EVENT_TOPIC.c_str(), buf, n);
}

void handleCommand(JsonDocument& cmd) {
  const char* action = cmd["action"];
  JsonObject args = cmd["args"];
  const char* cmdId = cmd["id"] | "";

  StaticJsonDocument<128> resultDoc;
  JsonVariant result = resultDoc.to<JsonVariant>();

  if (strcmp(action, "node.set_pin") == 0) {
    int pin = args["pin"];
    int value = args["value"];
    pinMode(pin, OUTPUT);
    digitalWrite(pin, value ? HIGH : LOW);
    resultDoc["pin"] = pin;
    resultDoc["value"] = value;
    publishEvent(cmdId, true, result, nullptr);

  } else if (strcmp(action, "node.set_relay") == 0) {
    const char* relay = args["relay"];
    bool on = args["on"];
    int pin = relayPin(relay);
    if (pin < 0) {
      publishEvent(cmdId, false, result, "unknown relay");
      return;
    }
    pinMode(pin, OUTPUT);
    digitalWrite(pin, on ? HIGH : LOW);
    resultDoc["relay"] = relay;
    resultDoc["on"] = on;
    publishEvent(cmdId, true, result, nullptr);

  } else if (strcmp(action, "node.read_sensor") == 0) {
    const char* sensor = args["sensor"];
    int pin = sensorPin(sensor);
    if (pin < 0) {
      publishEvent(cmdId, false, result, "unknown sensor");
      return;
    }
    int reading = analogRead(pin);
    resultDoc["sensor"] = sensor;
    resultDoc["value"] = reading;
    publishEvent(cmdId, true, result, nullptr);

  } else {
    publishEvent(cmdId, false, result, "unknown action");
  }
}

void onMessage(char* topic, byte* payload, unsigned int len) {
  StaticJsonDocument<256> cmd;
  DeserializationError parseErr = deserializeJson(cmd, payload, len);
  if (parseErr) return;  // malformed JSON — nothing sensible to reply to
  handleCommand(cmd);
}

void publishState() {
  StaticJsonDocument<256> doc;
  JsonObject relays = doc.createNestedObject("relays");
  for (size_t i = 0; i < NUM_RELAYS; i++) {
    relays[RELAYS[i].name] = digitalRead(RELAYS[i].pin) == HIGH;
  }
  char buf[256];
  size_t n = serializeJson(doc, buf);
  mqtt.publish(STATE_TOPIC.c_str(), buf, n, true /* retained */);
}

void connectMqtt() {
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(onMessage);
  while (!mqtt.connected()) {
    if (mqtt.connect(NODE_ID)) {
      mqtt.subscribe(CMD_TOPIC.c_str());
      publishRegister();
      publishState();
    } else {
      delay(1000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  for (size_t i = 0; i < NUM_RELAYS; i++) {
    pinMode(RELAYS[i].pin, OUTPUT);
    digitalWrite(RELAYS[i].pin, LOW);
  }
  connectWifi();
  connectMqtt();
}

void loop() {
  if (!mqtt.connected()) connectMqtt();
  mqtt.loop();

  unsigned long now = millis();
  if (now - lastStatePublish > STATE_INTERVAL_MS) {
    publishState();
    lastStatePublish = now;
  }
}
