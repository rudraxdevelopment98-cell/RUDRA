"""
Text-to-speech (cloud) — gives RUDRA a natural voice.

Cloud engine: ElevenLabs, chosen for quality. Kept behind this interface so a
local engine (Piper) can replace it for fully-offline mode later.
"""
from __future__ import annotations

import asyncio

from core.config import Config
from core.log import get_logger

log = get_logger("rudra.voice.tts")


class TTS:
    def __init__(self, config: Config):
        self.config = config
        self.engine = config.tts_engine
        self._client = None

    def _load_client(self):
        if self._client is not None:
            return self._client
        from elevenlabs.client import ElevenLabs

        self._client = ElevenLabs(api_key=self.config.tts_api_key)
        return self._client

    async def say(self, text: str) -> None:
        """Speak `text` aloud."""
        if not text:
            return
        if self.engine != "elevenlabs" or not self.config.tts_api_key:
            log.info("🔊 (stub) RUDRA says: %s", text)
            return

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._say_sync, text)

    def _say_sync(self, text: str) -> None:
        from elevenlabs import play

        log.info("🔊 RUDRA says: %s", text)
        client = self._load_client()
        audio = client.text_to_speech.convert(
            voice_id=self.config.tts_voice_id,
            text=text,
            model_id="eleven_turbo_v2_5",
        )
        play(audio)
