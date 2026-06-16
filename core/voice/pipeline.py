"""
Voice pipeline — chains the ears, brain, and mouth into one loop.

    wake word  →  STT  →  orchestrator.handle()  →  TTS

Phase 0: `run()` just idles (so `docker compose up` stays alive without a mic).
Phase 2: flip USE_VOICE on and the real loop below takes over.
"""
from __future__ import annotations

import asyncio

from core.config import Config
from core.log import get_logger
from core.voice.stt import STT
from core.voice.tts import TTS
from core.voice.wakeword import WakeWord

log = get_logger("rudra.voice.pipeline")

# Phase 2 flips this on. Until then we don't touch the microphone.
USE_VOICE = False


class VoicePipeline:
    def __init__(self, config: Config, brain):
        self.config = config
        self.brain = brain
        self.wake = WakeWord(config)
        self.stt = STT(config)
        self.tts = TTS(config)

    async def run(self) -> None:
        if not USE_VOICE:
            log.info("🛌 voice loop idle (Phase 0). Set USE_VOICE=True in Phase 2.")
            # Keep the process alive so the bus/brain stay up.
            while True:
                await asyncio.sleep(3600)

        # --- Phase 2: the real loop ---
        while True:
            await self.wake.wait_for_wake()        # "Rudra"
            text = await self.stt.listen()         # what you said
            if not text:
                continue
            reply = await self.brain.handle(text)  # think + act
            await self.tts.say(reply)              # speak the answer
