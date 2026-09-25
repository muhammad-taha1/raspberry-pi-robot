from robotd.actors.hearing import HearingActor
from robotd.hal.audio import AudioChunk
from robotd.messages import Transcript

from doubles import (
    FakeButton,
    RaisingButton,
    RaisingMic,
    RaisingStt,
    RecordingMic,
    ScriptedStt,
    wait_until,
)


class RecordingBrain:
    """Not a real actor — HearingActor only ever tell()s it, same as tests/doubles.py
    stands in for real device actors elsewhere in this suite.
    """

    def __init__(self) -> None:
        self.received: list[object] = []

    def tell(self, message: object) -> None:
        self.received.append(message)


def held_audio(seconds: float = 1.0) -> AudioChunk:
    frames = int(16_000 * seconds)
    return AudioChunk(data=b"\x00\x00" * frames, sample_rate=16_000, sample_width=2, channels=1)


def tapped_audio() -> AudioChunk:
    return AudioChunk(data=b"", sample_rate=16_000, sample_width=2, channels=1)


def start(mic=None, stt=None, button=None):
    brain = RecordingBrain()
    mic = mic if mic is not None else RecordingMic(held_audio())
    stt = stt if stt is not None else ScriptedStt(["turn on the light"])
    button = button if button is not None else FakeButton(pressed_for=3)
    hearing = HearingActor.start(mic=mic, stt=stt, brain=brain, button=button)
    return hearing, brain, mic, stt, button


def stop(hearing, brain):
    hearing.stop()


def test_press_transcribes_and_reaches_brain_as_transcript():
    hearing, brain, mic, stt, button = start()
    try:
        button.press()
        wait_until(lambda: brain.received)
    finally:
        stop(hearing, brain)

    assert len(brain.received) == 1
    assert brain.received[0] == Transcript("turn on the light")


def test_record_polls_is_pressed_until_release():
    hearing, brain, mic, stt, button = start(button=FakeButton(pressed_for=5))
    try:
        button.press()
        wait_until(lambda: brain.received)
    finally:
        stop(hearing, brain)

    # One of the five held polls is the still-held check before recording.
    assert mic.polls == 4


def test_press_handled_after_release_is_dropped():
    hearing, brain, mic, stt, button = start(button=FakeButton(pressed_for=0))
    try:
        button.press()
        hearing.ask(object())  # mailbox is FIFO: the press has been handled once this returns
    finally:
        stop(hearing, brain)

    assert mic.polls == 0
    assert stt.audios == []
    assert brain.received == []


def test_short_recording_is_dropped_before_stt_runs():
    stt = ScriptedStt([])  # would raise IndexError if ever called
    hearing, brain, mic, stt, button = start(mic=RecordingMic(tapped_audio()), stt=stt)
    try:
        button.press()
        wait_until(lambda: mic.polls > 0)
    finally:
        stop(hearing, brain)

    assert stt.audios == []
    assert brain.received == []


def test_empty_transcription_sends_no_transcript():
    hearing, brain, mic, stt, button = start(stt=ScriptedStt([""]))
    try:
        button.press()
        wait_until(lambda: stt.audios)
    finally:
        stop(hearing, brain)

    assert brain.received == []


def test_raising_stt_leaves_actor_alive():
    hearing, brain, mic, stt, button = start(stt=RaisingStt())
    try:
        button.press()
        wait_until(lambda: mic.polls > 0)
        assert hearing.is_alive()
    finally:
        stop(hearing, brain)

    assert brain.received == []


def test_raising_mic_leaves_actor_alive():
    hearing, brain, mic, stt, button = start(mic=RaisingMic())
    try:
        button.press()
        wait_until(lambda: mic.called)
        assert hearing.is_alive()
    finally:
        stop(hearing, brain)


def test_stop_closes_mic_and_button():
    hearing, brain, mic, stt, button = start()
    stop(hearing, brain)

    assert mic.closed
    assert button.closed


def test_stop_closes_both_even_when_mic_raises():
    hearing, brain, mic, stt, button = start(mic=RaisingMic(), button=RaisingButton(pressed_for=1))
    # stop() must not raise even though both close() calls fault.
    stop(hearing, brain)
