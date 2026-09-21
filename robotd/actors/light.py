"""LightActor — owns the status LED. Primitives only; patterns live elsewhere."""

from __future__ import annotations

import pykka

from robotd.hal.leds import Led
from robotd.messages import SetLed


class LightActor(pykka.ThreadingActor):
    def __init__(self, led: Led) -> None:
        super().__init__()
        self._led = led

    def on_receive(self, message: object) -> None:
        if isinstance(message, SetLed):
            self._led.on() if message.turn_on else self._led.off()

    def on_stop(self) -> None:
        self._shutdown()

    def on_failure(self, exception_type, exception_value, traceback) -> None:
        self._shutdown()

    def _shutdown(self) -> None:
        try:
            self._led.off()
        finally:
            self._led.close()
