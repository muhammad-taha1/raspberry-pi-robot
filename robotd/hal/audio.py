"""Audio seam. Piper produces raw PCM chunks; PyAudio plays and records them."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AudioChunk:
    data: bytes
    sample_rate: int
    sample_width: int
    channels: int


class Speaker(Protocol):
    def play(self, chunks: Iterable[AudioChunk]) -> None: ...
    def close(self) -> None: ...


class Microphone(Protocol):
    def record(self, while_true: Callable[[], bool]) -> AudioChunk: ...
    def close(self) -> None: ...


class PyAudioSpeaker:
    def __init__(self) -> None:
        # Deferred so laptop tests can import this module without PyAudio.
        import pyaudio

        self._pyaudio = pyaudio.PyAudio()
        self._closed = False

    def play(self, chunks: Iterable[AudioChunk]) -> None:
        stream = None
        try:
            for chunk in chunks:
                if stream is None:
                    stream = self._pyaudio.open(
                        format=self._pyaudio.get_format_from_width(chunk.sample_width),
                        channels=chunk.channels,
                        rate=chunk.sample_rate,
                        output=True,
                    )
                stream.write(chunk.data)
        finally:
            if stream is not None:
                stream.stop_stream()
                stream.close()

    def close(self) -> None:
        if not self._closed:
            self._pyaudio.terminate()
            self._closed = True


CHUNK_FRAMES = 1024
# Whisper's native rate. ALSA's default PCM is a `plug` (see /etc/asound.conf),
# which converts from whatever the USB card actually supports — opening its raw
# hw: device instead fails with paInvalidSampleRate.
MIC_SAMPLE_RATE = 16_000


class PyAudioMicrophone:
    """Records mono int16 from the ALSA default input, same device the speaker uses."""

    def __init__(self, max_seconds: float = 15.0) -> None:
        # Deferred so laptop tests can import this module without PyAudio.
        import pyaudio

        self._pyaudio = pyaudio.PyAudio()
        self._max_seconds = max_seconds
        self._closed = False

    def record(self, while_true: Callable[[], bool]) -> AudioChunk:
        import time

        stream = self._pyaudio.open(
            format=self._pyaudio.get_format_from_width(2),
            channels=1,
            rate=MIC_SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_FRAMES,
        )
        frames: list[bytes] = []
        try:
            deadline = time.monotonic() + self._max_seconds
            while while_true() and time.monotonic() < deadline:
                frames.append(stream.read(CHUNK_FRAMES, exception_on_overflow=False))
        finally:
            stream.stop_stream()
            stream.close()

        return AudioChunk(
            data=b"".join(frames), sample_rate=MIC_SAMPLE_RATE, sample_width=2, channels=1
        )

    def close(self) -> None:
        if not self._closed:
            self._pyaudio.terminate()
            self._closed = True
