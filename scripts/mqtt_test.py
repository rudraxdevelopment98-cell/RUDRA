"""
Standalone MQTT credential tester.

Connects to the broker using the SAME env vars RUDRA reads
(MQTT_HOST / MQTT_PORT / MQTT_USERNAME / MQTT_PASSWORD / MQTT_TLS)
and reports exactly what the broker says — so you can debug auth
without booting the whole brain.

Run locally:
    export MQTT_HOST=... MQTT_PORT=8883 MQTT_USERNAME=... MQTT_PASSWORD=... MQTT_TLS=true
    python3 scripts/mqtt_test.py
"""
from __future__ import annotations

import asyncio
import os

import aiomqtt


async def main() -> None:
    host = os.environ.get("MQTT_HOST", "localhost")
    port = int(os.environ.get("MQTT_PORT", "1883"))
    username = os.environ.get("MQTT_USERNAME") or None
    password = os.environ.get("MQTT_PASSWORD") or None
    tls = os.environ.get("MQTT_TLS", "false").lower() == "true"

    # Show EXACTLY what we're sending — lengths and repr catch hidden
    # whitespace, truncation, or a '#' that a .env parser ate.
    print(f"host     = {host!r}")
    print(f"port     = {port}")
    print(f"tls      = {tls}")
    print(f"username = {username!r}  (len={len(username) if username else 0})")
    if password:
        print(f"password = len={len(password)}  starts={password[:2]!r}  ends={password[-2:]!r}")
    else:
        print("password = <empty>  ← nothing was passed!")

    tls_params = aiomqtt.TLSParameters() if tls else None
    try:
        async with aiomqtt.Client(
            hostname=host, port=port,
            username=username, password=password,
            tls_params=tls_params,
        ):
            print("\n✅ CONNECTED — credentials are good. The problem is elsewhere.")
    except Exception as exc:  # noqa: BLE001 — we want to print whatever the broker said
        print(f"\n❌ FAILED: {type(exc).__name__}: {exc}")
        print("\nIf this says 'Not authorized':")
        print("  • Check username case — HiveMQ credentials are case-sensitive.")
        print("  • Re-type the password by hand in Railway (a pasted '#' can get")
        print("    truncated by .env parsers — note the password length above and")
        print("    compare it to your real password's length).")
        print("  • Confirm the credential exists under THIS cluster's Access Management.")


if __name__ == "__main__":
    asyncio.run(main())
