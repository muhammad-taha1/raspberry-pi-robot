"""Text-to-speech model seam backed by Piper's Python API."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Protocol

from robotd.hal.audio import AudioChunk


class TextToSpeech(Protocol):
    def synthesize(self, text: str) -> Iterable[AudioChunk]: ...


class PiperTts:
    """A Piper voice loaded once and streamed in raw PCM chunks."""

    def __init__(self, model_path: str | Path) -> None:
        # Deferred so laptop tests can import this module without Piper.
        from piper import PiperVoice

        self._voice = PiperVoice.load(str(model_path))

    def synthesize(self, text: str) -> Iterable[AudioChunk]:
        for chunk in self._voice.synthesize(text):
            yield AudioChunk(
                data=chunk.audio_int16_bytes,
                sample_rate=chunk.sample_rate,
                sample_width=chunk.sample_width,
                channels=chunk.sample_channels,
            )
