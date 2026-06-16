"""
Text-to-speech (cloud) — gives RUDRA a natural voice.

Cloud engine (e.g. ElevenLabs / Deepgram) chosen for quality; behind an
interface so a local engine (Piper) can replace it for fully-offline mode.

Phase 0: stub (prints). Phase 2: synthesize + play audio.
"""
from __future__ import annotations

from core.config import Config
from core.log import get_logger

log = get_logger("rudra.voice.tts")


class TTS:
    def __init__(self, config: Config):
        self.config = config
        self.engine = config.tts_engine

    async def say(self, text: str) -> None:
        """
        Speak `text` aloud.

        Phase 2:
          - call the cloud TTS API (key = config.tts_api_key) → audio bytes
          - play through the speakers
        """
        # TODO(Phase 2): real synthesis + playback.
        log.info("🔊 (stub) RUDRA says: %s", text)
