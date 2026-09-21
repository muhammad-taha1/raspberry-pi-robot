from robotd.actors.status import StatusActor
from robotd.models.llm import ToolCall
from robotd.tools import build_registry

from doubles import RecordingLed, wait_until


def start():
    led = RecordingLed()
    status = StatusActor.start(led=led)
    return status, led, build_registry(status=status)


def test_set_led_reaches_status_actor():
    status, led, registry = start()
    try:
        assert registry.dispatch(ToolCall("set_led", {"on": True})) is True
        wait_until(lambda: led.calls)
    finally:
        status.stop()

    assert led.calls[0] == "on"


def test_unknown_tool_is_ignored():
    status, led, registry = start()
    try:
        assert registry.dispatch(ToolCall("sparkle", {})) is False
    finally:
        status.stop()

    assert led.calls == ["off", "close"]  # only StatusActor's own shutdown touched it


def test_bad_arguments_return_false():
    status, led, registry = start()
    try:
        assert registry.dispatch(ToolCall("set_led", {"colour": "red"})) is False
    finally:
        status.stop()
