"""Audio-output hardware seam.

Piper produces raw PCM chunks; PyAudio sends those chunks to the operating
system's default audio device. No utterance is written to disk.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AudioChunk:
    """One raw PCM chunk together with the format needed to play it."""

    data: bytes
    sample_rate: int
    sample_width: int
    channels: int


class Speaker(Protocol):
    def play(self, chunks: Iterable[AudioChunk]) -> None: ...
    def close(self) -> None: ...


class PyAudioSpeaker:
    """Plays raw PCM to PortAudio's default output device."""

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
