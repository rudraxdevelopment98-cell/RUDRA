"""
Speech-to-text (local) — turns recorded audio into text.

Engine: faster-whisper (accurate, runs locally; keeps audio private).

Phase 0: stub. Phase 2: record until silence, transcribe.
"""
from __future__ import annotations

from core.config import Config
from core.log import get_logger

log = get_logger("rudra.voice.stt")


class STT:
    def __init__(self, config: Config):
        self.config = config
        self.engine = config.stt_engine

    async def listen(self) -> str:
        """
        Record the user's command and return the transcribed text.

        Phase 2:
          - record mic audio until silence (VAD)
          - run faster-whisper → text
        """
        # TODO(Phase 2): real recording + transcription.
        log.info("🎙  (stub) STT via %s — returning placeholder", self.engine)
        return ""
