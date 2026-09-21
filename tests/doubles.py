"""Test doubles implementing robotd/hal and robotd/models protocols. Never
shipped in robotd/."""

from __future__ import annotations

from collections.abc import Iterable

from robotd.hal.audio import AudioChunk
from robotd.models.llm import Completion


class RecordingLed:
    """Implements Led. Records every call for assertion."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def on(self) -> None:
        self.calls.append("on")

    def off(self) -> None:
        self.calls.append("off")

    def close(self) -> None:
        self.calls.append("close")


class RaisingLed:
    """Implements Led. Raises on on() — proves shutdown still turns it off and closes it."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def on(self) -> None:
        self.calls.append("on")
        raise RuntimeError("led hardware fault")

    def off(self) -> None:
        self.calls.append("off")

    def close(self) -> None:
        self.calls.append("close")


class RecordingTts:
    """Implements TextToSpeech. Emits one identifiable chunk per request."""

    def __init__(self) -> None:
        self.texts: list[str] = []

    def synthesize(self, text: str) -> Iterable[AudioChunk]:
        self.texts.append(text)
        return [AudioChunk(text.encode(), 22_050, 2, 1)]


class RecordingSpeaker:
    """Implements Speaker. Consumes each streamed utterance for assertion."""

    def __init__(self) -> None:
        self.utterances: list[bytes] = []
        self.closed = False

    def play(self, chunks: Iterable[AudioChunk]) -> None:
        self.utterances.append(b"".join(chunk.data for chunk in chunks))

    def close(self) -> None:
        self.closed = True


class ScriptedLlm:
    """Implements LlmProvider. Returns queued Completions, records what it
    was asked."""

    def __init__(self, completions: list[Completion]) -> None:
        self._completions = list(completions)
        self.texts: list[str] = []

    def complete(self, text: str) -> Completion:
        self.texts.append(text)
        return self._completions.pop(0)


class ScriptedChat:
    """Implements ChatProvider. Returns queued strings, records what it was
    asked — proves chat is (or isn't) consulted for a given Transcript."""

    def __init__(self, replies: list[str]) -> None:
        self._replies = list(replies)
        self.texts: list[str] = []

    def reply(self, text: str) -> str:
        self.texts.append(text)
        return self._replies.pop(0)


class RaisingChat:
    """Implements ChatProvider. Raises on reply() — proves BrainActor speaks
    an UNSURE phrase instead of crashing when chat fails."""

    def reply(self, text: str) -> str:
        raise RuntimeError("chat model fault")
