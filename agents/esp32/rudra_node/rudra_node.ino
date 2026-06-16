/*
 * RUDRA Node — ESP32 firmware skeleton
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
 * Phase 0: skeleton. Phase 5: implement command handling + sensors.
 *
 * Build: Arduino IDE / PlatformIO. Copy config.example.h -> config.h and fill in.
 * Libraries: WiFi, PubSubClient, ArduinoJson.
 */

#include <WiFi.h>
#include <PubSubClient.h>
// #include <ArduinoJson.h>   // enable in Phase 5
#include "config.h"           // WIFI_SSID, WIFI_PASS, MQTT_HOST, MQTT_PORT, NODE_ID

WiFiClient net;
PubSubClient mqtt(net);

void connectWifi() {
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) { delay(300); }
}

void publishRegister() {
  // TODO(Phase 5): build JSON {device, domain:"node", capabilities:[...]}
  String topic = String("rudra/system/all/register");
  mqtt.publish(topic.c_str(), "{\"device\":\"" NODE_ID "\",\"domain\":\"node\"}");
}

void onMessage(char* topic, byte* payload, unsigned int len) {
  // TODO(Phase 5): parse JSON command, switch on "action":
  //   node.set_pin   -> digitalWrite(pin, value)
  //   node.set_relay -> drive named relay pin
  //   node.read_sensor -> read + publish event
  // Then publish an Event on rudra/node/<NODE_ID>/event.
}

void connectMqtt() {
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(onMessage);
  while (!mqtt.connected()) {
    if (mqtt.connect(NODE_ID)) {
      mqtt.subscribe("rudra/node/" NODE_ID "/cmd");
      publishRegister();
    } else {
      delay(1000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  // TODO(Phase 5): pinMode() for your relays/LEDs here.
  connectWifi();
  connectMqtt();
}

void loop() {
  if (!mqtt.connected()) connectMqtt();
  mqtt.loop();
  // TODO(Phase 5): periodically publish sensor state (retained).
}
