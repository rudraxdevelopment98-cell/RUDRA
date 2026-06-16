"""
Speech-to-text (local) — turns recorded audio into text.

Engine: faster-whisper (accurate, runs locally; keeps audio private).

Records from the microphone until the user stops talking (simple energy-based
silence detection), then transcribes the buffered audio in one shot.
"""
from __future__ import annotations

import asyncio

from core.config import Config
from core.log import get_logger

log = get_logger("rudra.voice.stt")

_CHUNK_MS = 30
_SILENCE_RMS = 500          # below this = silence (int16 samples)
_SILENCE_HANG_MS = 800      # stop after this much trailing silence
_MAX_RECORD_MS = 15_000     # hard cap so a stuck mic can't hang forever
_LISTEN_TIMEOUT_MS = 5_000  # give up if the user never starts speaking


class STT:
    def __init__(self, config: Config):
        self.config = config
        self.engine = config.stt_engine
        self._model = None

    def _load_model(self):
        if self._model is not None:
            return self._model
        from faster_whisper import WhisperModel

        self._model = WhisperModel(self.config.stt_model_size, device="cpu", compute_type="int8")
        return self._model

    async def listen(self) -> str:
        """Record the user's command and return the transcribed text."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._listen_sync)

    def _record_until_silence(self):
        import numpy as np
        import sounddevice as sd

        rate = self.config.sample_rate
        chunk_samples = int(rate * _CHUNK_MS / 1000)
        max_chunks = _MAX_RECORD_MS // _CHUNK_MS
        timeout_chunks = _LISTEN_TIMEOUT_MS // _CHUNK_MS
        hang_chunks = _SILENCE_HANG_MS // _CHUNK_MS

        frames = []
        speaking = False
        silence_run = 0

        with sd.InputStream(samplerate=rate, channels=1, dtype="int16", blocksize=chunk_samples) as stream:
            for i in range(max_chunks):
                chunk, _overflowed = stream.read(chunk_samples)
                samples = np.squeeze(chunk)
                rms = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))

                if rms >= _SILENCE_RMS:
                    speaking = True
                    silence_run = 0
                    frames.append(samples)
                elif speaking:
                    silence_run += 1
                    frames.append(samples)
                    if silence_run >= hang_chunks:
                        break
                elif i >= timeout_chunks:
                    break

        if not frames:
            return None
        return np.concatenate(frames)

    def _listen_sync(self) -> str:
        import numpy as np

        log.info("🎙  listening via %s", self.engine)
        audio = self._record_until_silence()
        if audio is None:
            log.info("🎙  heard nothing")
            return ""

        model = self._load_model()
        audio_float = audio.astype(np.float32) / 32768.0
        segments, _info = model.transcribe(audio_float, language="en")
        text = " ".join(segment.text.strip() for segment in segments).strip()
        log.info("🎙  heard: %r", text)
        return text
