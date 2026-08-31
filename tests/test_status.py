import time

from robotd.actors.status import StatusActor
from robotd.messages import Blink, SetLed

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


def test_blink_toggles_more_than_once():
    led = RecordingLed()
    actor = StatusActor.start(led=led)
    try:
        actor.tell(Blink(0.02))
        time.sleep(0.15)
    finally:
        actor.stop()

    toggles = [c for c in led.calls if c in ("on", "off")]
    assert len(toggles) >= 2


def test_set_led_cancels_blink():
    led = RecordingLed()
    actor = StatusActor.start(led=led)
    try:
        actor.tell(Blink(0.02))
        time.sleep(0.05)
        actor.tell(SetLed(False))
        count_after_cancel = None
        time.sleep(0.1)
        count_after_cancel = len([c for c in led.calls if c in ("on", "off")])
        time.sleep(0.1)
        count_later = len([c for c in led.calls if c in ("on", "off")])
    finally:
        actor.stop()

    assert count_after_cancel == count_later


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
