import time

from robotd.actors.status import StatusActor
from robotd.messages import SetLed

from doubles import RaisingLed, RecordingLed


def test_set_led_on_off():
    led = RecordingLed()
    actor = StatusActor.start(led=led)
    try:
        actor.tell(SetLed(True))
        actor.tell(SetLed(False))
        time.sleep(0.05)
    finally:
        actor.stop()

    assert led.calls[:2] == ["on", "off"]


def test_stop_turns_led_off_and_closes():
    led = RecordingLed()
    actor = StatusActor.start(led=led)
    actor.tell(SetLed(True))
    time.sleep(0.02)
    actor.stop()

    assert led.calls[-2:] == ["off", "close"]


def test_raising_led_still_gets_closed():
    led = RaisingLed()
    actor = StatusActor.start(led=led)
    actor.tell(SetLed(True))
    time.sleep(0.05)
    actor.stop()

    assert "close" in led.calls
