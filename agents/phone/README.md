# RUDRA — Phone Agent

You don't need to build an app to start. RUDRA reaches your phone through tools
that already exist.

## Android (recommended)
**Option A — Home Assistant Companion app**
- Install the HA Companion app and connect it to your Home Assistant.
- It exposes notifications, location, ringing ("find phone"), and sensors.
- RUDRA's `phone` skill sends these via Home Assistant.

**Option B — Tasker + MQTT Client**
- Tasker subscribes to `rudra/phone/my-phone/cmd` and runs profiles
  (notify, ring, locate, launch app), publishing results to `.../event`.

## iOS
- Use **Shortcuts** + a webhook/MQTT bridge.
- `phone.run_automation` triggers a named Shortcut.

## Mapping
| Tool                  | Android (HA / Tasker)          | iOS (Shortcuts)        |
|-----------------------|--------------------------------|------------------------|
| `phone.notify`        | HA notify / Tasker Notify      | Notification shortcut  |
| `phone.find`          | HA "ring" / Tasker max volume  | Find My (limited)      |
| `phone.locate`        | HA device_tracker              | Location shortcut      |
| `phone.run_automation`| Tasker task / HA script        | named Shortcut         |

Status: 🟡 recipes only — wired up in Phase 6.
