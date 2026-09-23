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


class PyAudioMicrophone:
    """Records mono int16 at the device's own native rate — WhisperStt resamples,
    not this seam. `device_name` is matched by substring, case-insensitive, since
    USB card numbering isn't stable across reboots (see AGENTS.md).
    """

    def __init__(self, device_name: str, max_seconds: float = 15.0) -> None:
        # Deferred so laptop tests can import this module without PyAudio.
        import pyaudio

        self._pyaudio = pyaudio.PyAudio()
        self._device_index = self._find_input_device(device_name)
        self._max_seconds = max_seconds
        self._closed = False

    def _find_input_device(self, device_name: str) -> int | None:
        wanted = device_name.lower()
        for index in range(self._pyaudio.get_device_count()):
            info = self._pyaudio.get_device_info_by_index(index)
            if info.get("maxInputChannels", 0) > 0 and wanted in str(info.get("name", "")).lower():
                return index
        logger.warning(
            "No input device matching '%s'; falling back to the system default input",
            device_name,
        )
        return None

    def record(self, while_true: Callable[[], bool]) -> AudioChunk:
        import time

        info = (
            self._pyaudio.get_device_info_by_index(self._device_index)
            if self._device_index is not None
            else self._pyaudio.get_default_input_device_info()
        )
        sample_rate = int(info["defaultSampleRate"])

        stream = self._pyaudio.open(
            format=self._pyaudio.get_format_from_width(2),
            channels=1,
            rate=sample_rate,
            input=True,
            input_device_index=self._device_index,
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

        return AudioChunk(data=b"".join(frames), sample_rate=sample_rate, sample_width=2, channels=1)

    def close(self) -> None:
        if not self._closed:
            self._pyaudio.terminate()
            self._closed = True
