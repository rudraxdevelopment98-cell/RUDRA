"""
Wake-word detection (local) — listens for "Rudra".

Engine: openWakeWord (free, runs locally). Behind an interface so it can be
swapped for Porcupine or a custom model later.

openWakeWord ships pretrained models (e.g. "hey jarvis") but has no model for
the word "rudra" out of the box — train one with its `train_custom_model`
notebook and point `RUDRA_WAKE_MODEL_PATH` at the resulting .onnx/.tflite file.
Without one we fall back to whatever stock model ships with the package, so
the pipeline still runs end-to-end during development.
"""
from __future__ import annotations

import asyncio

from core.config import Config
from core.log import get_logger

log = get_logger("rudra.voice.wakeword")

_FRAME_SAMPLES = 1280  # 80ms @ 16kHz, the hop size openWakeWord expects


class WakeWord:
    def __init__(self, config: Config):
        self.config = config
        self.word = config.wake_word
        self._model = None

    def _load_model(self):
        if self._model is not None:
            return self._model
        from openwakeword.model import Model

        kwargs = {}
        if self.config.wake_model_path:
            kwargs["wakeword_models"] = [self.config.wake_model_path]
        self._model = Model(**kwargs)
        return self._model

    async def wait_for_wake(self) -> bool:
        """Block until the wake word is heard, then return True."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._wait_for_wake_sync)

    def _wait_for_wake_sync(self) -> bool:
        import numpy as np
        import sounddevice as sd

        model = self._load_model()
        model.reset()
        log.info("👂 listening for wake word %r", self.word)

        with sd.InputStream(
            samplerate=self.config.sample_rate,
            channels=1,
            dtype="int16",
            blocksize=_FRAME_SAMPLES,
        ) as stream:
            while True:
                frame, _overflowed = stream.read(_FRAME_SAMPLES)
                audio = np.squeeze(frame)
                predictions = model.predict(audio)
                if any(score >= self.config.wake_threshold for score in predictions.values()):
                    log.info("🔔 wake word detected")
                    return True
