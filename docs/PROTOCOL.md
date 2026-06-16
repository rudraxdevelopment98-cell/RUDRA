# RUDRA — Bus Protocol (MQTT)

The brain and every agent communicate **only** through MQTT messages that follow
this contract. Keep this file and `shared/schema/*.json` in sync.

## Topic structure

```
rudra/<domain>/<device>/<channel>
```

| Part      | Meaning                              | Examples                     |
|-----------|--------------------------------------|------------------------------|
| `rudra`   | root namespace (always)              | `rudra`                      |
| `domain`  | category of target                   | `pc` · `phone` · `iot` · `node` · `system` |
| `device`  | which specific device                | `main-pc` · `esp32-desk` · `all` |
| `channel` | direction / kind                     | `cmd` · `event` · `state` · `register` |

### Channels
- **`cmd`**  — brain → agent. "Do this." (a **Command**)
- **`event`** — agent → brain. "This happened / here's the result." (an **Event**)
- **`state`** — agent → bus (retained). Last-known state of a device.
- **`register`** — agent → brain. "I'm online, here's what I can do."

### Examples
```
rudra/pc/main-pc/cmd          brain tells the PC to do something
rudra/pc/main-pc/event        PC reports the result
rudra/node/esp32-desk/cmd     brain tells an ESP32 to flip a pin
rudra/node/esp32-desk/state   ESP32's retained last-known pin states
rudra/system/all/register     any agent announces itself on boot
```

## Message: Command (`cmd`)
```json
{
  "id": "cmd_a1b2c3",
  "ts": 1718500000,
  "action": "pc.open_app",
  "args": { "app": "code" },
  "reply_to": "rudra/pc/main-pc/event",
  "needs_confirm": false
}
```

## Message: Event (`event`)
```json
{
  "id": "evt_d4e5f6",
  "ts": 1718500001,
  "in_reply_to": "cmd_a1b2c3",
  "ok": true,
  "result": { "opened": "code" },
  "error": null
}
```

## Message: Register (`register`)
```json
{
  "device": "main-pc",
  "domain": "pc",
  "ts": 1718500000,
  "capabilities": ["pc.open_app", "pc.run_script", "pc.volume", "pc.lock"],
  "meta": { "os": "windows", "agent": "0.1.0" }
}
```

## Rules
1. Every `cmd` has a unique `id`; the matching `event` echoes it in `in_reply_to`.
2. Agents publish a `register` message on connect and a retained `state` per device.
3. `needs_confirm: true` means the agent must NOT act until it receives a second
   `cmd` with `confirmed: true` (used for power-off, delete, unlock, etc.).
4. Timestamps are UNIX seconds (`ts`).
5. Unknown actions → an `event` with `ok: false` and an `error`.
