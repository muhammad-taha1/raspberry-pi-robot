from robotd.actors.light import LightActor
from robotd.models.llm import ToolCall
from robotd.tools import build_registry

from doubles import RecordingLed, wait_until


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
