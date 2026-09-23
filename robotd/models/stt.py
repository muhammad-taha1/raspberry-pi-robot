"""Speech-to-text model seam backed by faster-whisper."""

from __future__ import annotations

import io
import wave
from typing import Protocol

from robotd.hal.audio import AudioChunk


class SpeechToText(Protocol):
    def transcribe(self, audio: AudioChunk) -> str: ...


def _to_wav(audio: AudioChunk) -> io.BytesIO:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(audio.channels)
        wav.setsampwidth(audio.sample_width)
        wav.setframerate(audio.sample_rate)
        wav.writeframes(audio.data)
    buffer.seek(0)
    return buffer


class WhisperStt:
    """faster-whisper, CPU/int8. Model weights are fetched from Hugging Face and
    cached on first run — the same self-managing precedent as NeedleLlm — so
    `model` is a name, not a path.
    """

    def __init__(self, model: str = "tiny.en") -> None:
        # Deferred so laptop tests can import this module without faster-whisper.
        from faster_whisper import WhisperModel

        self._model = WhisperModel(model, device="cpu", compute_type="int8")

    def transcribe(self, audio: AudioChunk) -> str:
        # vad_filter trims leading/trailing silence off the clip; the button,
        # not the VAD, is what triggered the recording.
        segments, _ = self._model.transcribe(
            _to_wav(audio), language="en", beam_size=1, vad_filter=True
        )
        return " ".join(segment.text.strip() for segment in segments).strip()
