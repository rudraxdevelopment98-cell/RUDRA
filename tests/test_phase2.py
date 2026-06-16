"""
Phase 2 tests — the deterministic parts that don't need a microphone/speaker.

Audio I/O (openWakeWord, faster-whisper, sounddevice, ElevenLabs) is imported
lazily inside each module so these checks run without any of those packages
or real hardware installed. Covers: config defaults/warnings, voice classes
construct cleanly, and the pipeline idles instead of touching the mic when
voice is disabled.

Run:
    python -m tests.test_phase2
"""
from __future__ import annotations

import asyncio

from core.config import Config
from core.voice.pipeline import VoicePipeline
from core.voice.stt import STT
from core.voice.tts import TTS
from core.voice.wakeword import WakeWord

PASS, FAIL = "✅", "❌"
_failures = 0


def check(name: str, cond: bool) -> None:
    global _failures
    print(f"  {PASS if cond else FAIL} {name}")
    if not cond:
        _failures += 1


async def run() -> None:
    print("config:")
    cfg = Config()
    check("voice is opt-in by default", cfg.voice_enabled is False)
    check("no voice warnings when voice is disabled",
          not any("wake" in w.lower() or "TTS_API_KEY" in w for w in cfg.validate()))

    cfg_on = Config(voice_enabled=True)
    warnings = cfg_on.validate()
    check("missing wake model warns when voice is enabled",
          any("WAKE_MODEL_PATH" in w for w in warnings))
    check("missing TTS key warns when voice is enabled",
          any("TTS_API_KEY" in w for w in warnings))

    print("voice classes:")
    wake = WakeWord(cfg)
    stt = STT(cfg)
    tts = TTS(cfg)
    check("WakeWord builds without touching hardware", wake.word == "rudra")
    check("STT builds without touching hardware", stt.engine == "faster-whisper")
    check("TTS builds without touching hardware", tts.engine == "elevenlabs")

    print("pipeline:")
    brain_calls = []

    class FakeBrain:
        async def handle(self, text: str) -> str:
            brain_calls.append(text)
            return "ok"

    pipeline = VoicePipeline(cfg, FakeBrain())
    try:
        await asyncio.wait_for(pipeline.run(), timeout=0.05)
        idled_without_crashing = False
    except asyncio.TimeoutError:
        idled_without_crashing = True
    check("idles (no mic access) when voice is disabled", idled_without_crashing)
    check("never calls the brain while idling", brain_calls == [])

    print()
    if _failures:
        print(f"{FAIL} {_failures} check(s) failed")
        raise SystemExit(1)
    print(f"{PASS} all Phase 2 checks passed")


if __name__ == "__main__":
    asyncio.run(run())
