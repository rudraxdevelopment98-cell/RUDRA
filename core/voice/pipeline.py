"""
Voice pipeline — chains the ears, brain, and mouth into one loop.

    wake word  →  STT  →  orchestrator.handle()  →  TTS

Set RUDRA_VOICE_ENABLED=true (and a microphone/speaker) to run the real loop.
Otherwise the pipeline idles so `docker compose up` stays alive headless.
"""
from __future__ import annotations

import asyncio

from core.config import Config
from core.log import get_logger
from core.voice.stt import STT
from core.voice.tts import TTS
from core.voice.wakeword import WakeWord

log = get_logger("rudra.voice.pipeline")


class VoicePipeline:
    def __init__(self, config: Config, brain):
        self.config = config
        self.brain = brain
        self.wake = WakeWord(config)
        self.stt = STT(config)
        self.tts = TTS(config)

    async def run(self) -> None:
        if not self.config.voice_enabled:
            log.info("🛌 voice loop idle. Set RUDRA_VOICE_ENABLED=true to turn on the mic.")
            # Keep the process alive so the bus/brain stay up.
            while True:
                await asyncio.sleep(3600)

        while True:
            await self.wake.wait_for_wake()        # "Rudra"
            text = await self.stt.listen()         # what you said
            if not text:
                continue
            reply = await self.brain.handle(text)  # think + act
            await self.tts.say(reply)              # speak the answer
