import time

from robotd.actors.status import StatusActor
from robotd.actors.voice import VoiceActor
from robotd.messages import SetLed, Speak
from robotd.models.llm import ToolCall
from robotd.tools import build_registry

from doubles import RecordingLed, RecordingSpeaker, RecordingTts


def start(led=None, tts=None, speaker=None):
    led = led or RecordingLed()
    tts = tts or RecordingTts()
    speaker = speaker or RecordingSpeaker()
    status = StatusActor.start(led=led)
    voice = VoiceActor.start(tts=tts, speaker=speaker)
    return status, voice, led, tts


def test_say_reaches_voice_actor():
    status, voice, led, tts = start()
    registry = build_registry(voice=voice, status=status)
    try:
        registry.dispatch(ToolCall("say", {"text": "hello"}))
        time.sleep(0.05)
    finally:
        status.stop()
        voice.stop()

    assert tts.texts == ["hello"]


def test_set_led_reaches_status_actor():
    status, voice, led, tts = start()
    registry = build_registry(voice=voice, status=status)
    try:
        registry.dispatch(ToolCall("set_led", {"on": True}))
        time.sleep(0.05)
    finally:
        status.stop()
        voice.stop()

    assert led.calls[0] == "on"


def test_unknown_tool_is_ignored():
    status, voice, led, tts = start()
    registry = build_registry(voice=voice, status=status)
    try:
        registry.dispatch(ToolCall("sparkle", {}))
        time.sleep(0.02)
    finally:
        status.stop()
        voice.stop()

    assert tts.texts == []
    assert led.calls == ["off", "close"]  # only StatusActor's own shutdown touched it


def test_functions_carry_name_and_docstring_for_needle_schema():
    status, voice, led, tts = start()
    registry = build_registry(voice=voice, status=status)
    try:
        names = {fn.__name__: fn.__doc__ for fn in registry.functions()}
    finally:
        status.stop()
        voice.stop()

    assert names["say"]
    assert names["set_led"]
