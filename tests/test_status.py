from robotd.actors.status import StatusActor
from robotd.messages import SetLed

from doubles import RaisingLed, RecordingLed, wait_until


def test_stop_turns_led_off_and_closes():
    led = RecordingLed()
    actor = StatusActor.start(led=led)
    actor.tell(SetLed(True))
    wait_until(lambda: led.calls)
    actor.stop()

    assert led.calls == ["on", "off", "close"]


def test_raising_led_still_gets_closed():
    led = RaisingLed()
    actor = StatusActor.start(led=led)
    actor.tell(SetLed(True))
    wait_until(lambda: led.calls)
    actor.stop()

    assert led.calls[-2:] == ["off", "close"]
