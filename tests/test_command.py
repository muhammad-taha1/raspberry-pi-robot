import time

from robotd.actors.command import CommandActor, Route
from robotd.actors.status import StatusActor
from robotd.actors.status import command as led_command
from robotd.actors.voice import VoiceActor
from robotd.actors.voice import command as say_command
from robotd.messages import Command

from doubles import RecordingLed, RecordingSpeaker, RecordingTts


def start_commands():
    led = RecordingLed()
    status = StatusActor.start(led=led)
    commands = CommandActor.start(routes={"led": Route(target=status, translate=led_command)})
    return led, status, commands


def test_voice_reaches_the_voice_actor():
    tts = RecordingTts()
    speaker = RecordingSpeaker()
    voice = VoiceActor.start(tts=tts, speaker=speaker)
    commands = CommandActor.start(routes={"voice": Route(target=voice, translate=say_command)})
    try:
        result = commands.ask(Command("voice", "hi"))
        time.sleep(0.05)
    finally:
        commands.stop()
        voice.stop()

    assert result.ok
    assert tts.texts == ["hi"]


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
