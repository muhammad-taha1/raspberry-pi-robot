from robotd.actors.command import CommandActor, Route
from robotd.actors.status import StatusActor
from robotd.actors.status import command as led_command
from robotd.messages import Command

from doubles import RecordingLed


def start_commands():
    led = RecordingLed()
    status = StatusActor.start(led=led)
    commands = CommandActor.start(routes={"led": Route(target=status, translate=led_command)})
    return led, status, commands


def test_led_on_reaches_the_led():
    led, status, commands = start_commands()
    try:
        result = commands.ask(Command("led", "on"))
    finally:
        commands.stop()
        status.stop()

    assert result.ok
    assert led.calls[0] == "on"


def test_led_off_reaches_the_led():
    led, status, commands = start_commands()
    try:
        result = commands.ask(Command("led", "off"))
    finally:
        commands.stop()
        status.stop()

    assert result.ok
    assert led.calls[0] == "off"


def test_unknown_device_is_rejected():
    led, status, commands = start_commands()
    try:
        result = commands.ask(Command("nope", "on"))
    finally:
        commands.stop()
        status.stop()

    assert not result.ok
    assert led.calls == ["off", "close"]  # only StatusActor's own shutdown touched it


def test_unknown_action_is_rejected():
    led, status, commands = start_commands()
    try:
        result = commands.ask(Command("led", "sparkle"))
    finally:
        commands.stop()
        status.stop()

    assert not result.ok
    assert led.calls == ["off", "close"]
