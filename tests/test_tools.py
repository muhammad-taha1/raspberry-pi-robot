import time

from robotd.actors.status import StatusActor
from robotd.models.llm import ToolCall
from robotd.tools import build_registry

from doubles import RecordingLed


def start(led=None):
    led = led or RecordingLed()
    status = StatusActor.start(led=led)
    return status, led


def test_set_led_reaches_status_actor():
    status, led = start()
    registry = build_registry(status=status)
    try:
        assert registry.dispatch(ToolCall("set_led", {"on": True})) is True
        time.sleep(0.05)
    finally:
        status.stop()

    assert led.calls[0] == "on"


def test_unknown_tool_is_ignored():
    status, led = start()
    registry = build_registry(status=status)
    try:
        assert registry.dispatch(ToolCall("sparkle", {})) is False
        time.sleep(0.02)
    finally:
        status.stop()

    assert led.calls == ["off", "close"]  # only StatusActor's own shutdown touched it


def test_bad_arguments_return_false():
    status, led = start()
    registry = build_registry(status=status)
    try:
        assert registry.dispatch(ToolCall("set_led", {"colour": "red"})) is False
    finally:
        status.stop()


def test_functions_carry_name_and_docstring_for_needle_schema():
    status, led = start()
    registry = build_registry(status=status)
    try:
        names = {fn.__name__: fn.__doc__ for fn in registry.functions()}
    finally:
        status.stop()

    assert names["set_led"]
