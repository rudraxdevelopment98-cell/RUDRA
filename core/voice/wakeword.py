"""
Wake-word detection (local) — listens for "Rudra".

Engine: openWakeWord (free, runs locally). Behind an interface so it can be
swapped for Porcupine or a custom model later.

Phase 0: stub. Phase 2: real microphone + model.
"""
from __future__ import annotations

from core.config import Config
from core.log import get_logger

log = get_logger("rudra.voice.wakeword")


class WakeWord:
    def __init__(self, config: Config):
        self.config = config
        self.word = config.wake_word

    async def wait_for_wake(self) -> bool:
        """
        Block until the wake word is heard, then return True.

        Phase 2:
          - capture mic audio in small frames
          - run openWakeWord on each frame
          - return when confidence crosses a threshold
        """
        # TODO(Phase 2): real detection loop.
        log.info("👂 (stub) listening for wake word %r", self.word)
        return True
