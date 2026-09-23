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


class RaisingSpeaker(RecordingSpeaker):
    """play() and close() both raise — proves the actor survives a bad device."""

    def play(self, chunks: Iterable[AudioChunk]) -> None:
        super().play(chunks)
        raise RuntimeError("device hardware fault")

    def close(self) -> None:
        super().close()
        raise RuntimeError("device close fault")


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


class RecordingMic:
    """Polls while_true to exhaustion, like the real record loop, then returns
    a pre-set clip — so a test can assert the button's is_pressed was actually
    consulted the right number of times.
    """

    def __init__(self, audio: AudioChunk) -> None:
        self._audio = audio
        self.polls = 0
        self.closed = False

    def record(self, while_true) -> AudioChunk:
        while while_true():
            self.polls += 1
        return self._audio

    def close(self) -> None:
        self.closed = True


class RaisingMic:
    """record() and close() both raise — proves HearingActor survives a bad mic."""

    def __init__(self) -> None:
        self.called = False

    def record(self, while_true) -> AudioChunk:
        self.called = True
        raise RuntimeError("mic hardware fault")

    def close(self) -> None:
        raise RuntimeError("mic close fault")


class ScriptedStt:
    def __init__(self, texts: list[str]) -> None:
        self._texts = list(texts)
        self.audios: list[AudioChunk] = []

    def transcribe(self, audio: AudioChunk) -> str:
        self.audios.append(audio)
        return self._texts.pop(0)


class RaisingStt:
    def transcribe(self, audio: AudioChunk) -> str:
        raise RuntimeError("stt model fault")


class FakeButton:
    """is_pressed() returns True for `pressed_for` polls, then False — a script
    for how long the button stays held once record() starts polling it.
    """

    def __init__(self, pressed_for: int = 1) -> None:
        self._callback = None
        self._pressed_for = pressed_for
        self._polls = 0
        self.closed = False

    def on_press(self, callback) -> None:
        self._callback = callback

    def press(self) -> None:
        self._callback()

    def is_pressed(self) -> bool:
        self._polls += 1
        return self._polls <= self._pressed_for

    def close(self) -> None:
        self.closed = True


class RaisingButton(FakeButton):
    def close(self) -> None:
        super().close()
        raise RuntimeError("button close fault")
