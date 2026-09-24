import re

import pytest

from robotd.actors.light import LightActor
from robotd.models.llm import ToolCall
from robotd.tools import LED_TRIGGERS, build_registry

from doubles import RecordingLed, wait_until


def led_triggered(text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in LED_TRIGGERS)


# Transcripts heard live on the Pi. The triggers are set_led's only permission
# to fire (see hold_untriggered), so a miss here means the light can't switch.
@pytest.mark.parametrize(
    "text",
    ["It's dark here.", "turn on the light", "Yeah, for turn off the light.", "lights on"],
)
def test_led_triggers_match_light_requests(text):
    assert led_triggered(text)


@pytest.mark.parametrize("text", ["Hey Alfred, how are you?", "Tell me a joke."])
def test_led_triggers_ignore_small_talk(text):
    assert not led_triggered(text)


def start():
    led = RecordingLed()
    light = LightActor.start(led=led)
    return light, led, build_registry(light=light)


def test_set_led_reaches_light_actor():
    light, led, registry = start()
    try:
        assert registry.dispatch(ToolCall("set_led", {"turn_on": True})) is True
        wait_until(lambda: led.calls)
    finally:
        light.stop()

    assert led.calls[0] == "on"


def test_unknown_tool_is_ignored():
    light, led, registry = start()
    try:
        assert registry.dispatch(ToolCall("sparkle", {})) is False
    finally:
        light.stop()

    assert led.calls == ["off", "close"]  # only LightActor's own shutdown touched it


def test_bad_arguments_return_false():
    light, led, registry = start()
    try:
        assert registry.dispatch(ToolCall("set_led", {"colour": "red"})) is False
    finally:
        light.stop()
