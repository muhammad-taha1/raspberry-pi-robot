"""Test doubles for robotd/hal and robotd/models protocols. Never shipped."""

from __future__ import annotations

import time
from collections.abc import Iterable

from robotd.hal.audio import AudioChunk
from robotd.models.llm import Completion


def wait_until(predicate, timeout: float = 1.0) -> None:
    """Wait for a tell()'d message to land, without a fixed sleep."""
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        time.sleep(0.005)


class RecordingLed:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def on(self) -> None:
        self.calls.append("on")

    def off(self) -> None:
        self.calls.append("off")

    def close(self) -> None:
        self.calls.append("close")


class RaisingLed(RecordingLed):
    """on() raises — proves shutdown still turns it off and closes it."""

    def on(self) -> None:
        super().on()
        raise RuntimeError("led hardware fault")


class RecordingTts:
    def __init__(self) -> None:
        self.texts: list[str] = []

    def synthesize(self, text: str) -> Iterable[AudioChunk]:
        self.texts.append(text)
        return [AudioChunk(text.encode(), 22_050, 2, 1)]


class RecordingSpeaker:
    def __init__(self) -> None:
        self.utterances: list[bytes] = []
        self.closed = False

    def play(self, chunks: Iterable[AudioChunk]) -> None:
        self.utterances.append(b"".join(chunk.data for chunk in chunks))

    def close(self) -> None:
        self.closed = True


class ScriptedLlm:
    def __init__(self, completions: list[Completion]) -> None:
        self._completions = list(completions)
        self.texts: list[str] = []

    def complete(self, text: str) -> Completion:
        self.texts.append(text)
        return self._completions.pop(0)


class ScriptedChat:
    def __init__(self, replies: list[str]) -> None:
        self._replies = list(replies)
        self.texts: list[str] = []

    def reply(self, text: str) -> str:
        self.texts.append(text)
        return self._replies.pop(0)


class RaisingChat:
    def reply(self, text: str) -> str:
        raise RuntimeError("chat model fault")
