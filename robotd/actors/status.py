"""StatusActor — owns the status LED. The first actor in the tree.

Deliberately dumb: it only knows how to turn the LED on/off and clean up
after itself. Behaviour (blink patterns, expressions) is policy that belongs
in whichever actor actually needs it, not baked into the device owner — e.g.
the attention/face logic arriving in M8 will drive this via SetLed, the same
way any future actor would.
"""

from __future__ import annotations

import pykka

from robotd.hal.leds import Led
from robotd.messages import SetLed


def command(action: str) -> SetLed | None:
    """Translate a Command.action string into the message StatusActor understands.

    Lives here, next to the actor that understands SetLed, rather than inside
    CommandActor — so CommandActor never grows per-device knowledge.
    """
    if action == "on":
        return SetLed(True)
    if action == "off":
        return SetLed(False)
    return None


class StatusActor(pykka.ThreadingActor):
    def __init__(self, led: Led) -> None:
        super().__init__()
        self._led = led

    def on_receive(self, message: object) -> None:
        if isinstance(message, SetLed):
            self._led.on() if message.on else self._led.off()

    def on_stop(self) -> None:
        self._shutdown()

    def on_failure(self, exception_type, exception_value, traceback) -> None:
        self._shutdown()

    def _shutdown(self) -> None:
        try:
            self._led.off()
        finally:
            self._led.close()
