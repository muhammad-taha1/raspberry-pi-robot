import logging
from typing import Protocol

from gpiozero import LED

logger = logging.getLogger(__name__)


class Led(Protocol):
    def on(self) -> None: ...
    def off(self) -> None: ...
    def close(self) -> None: ...


class GpioLed:
    def __init__(self, pin: int) -> None:
        self._led = LED(pin)

    def on(self) -> None:
        self._led.on()

    def off(self) -> None:
        self._led.off()

    def close(self) -> None:
        self._led.close()


class NullLed:
    """Stand-in used when the LED's GPIO pin can't be claimed (e.g. the LED
    circuit is disconnected during bring-up). Keeps the daemon running with
    the status LED simply unavailable, rather than crashing at startup.
    """

    def on(self) -> None: ...
    def off(self) -> None: ...
    def close(self) -> None: ...


def open_led(pin: int) -> Led:
    """Claim the status LED, falling back to a no-op LED with a warning if the
    GPIO pin can't be claimed.
    """
    try:
        return GpioLed(pin)
    except Exception:
        logger.warning("Status LED on GPIO %s unavailable; continuing without it", pin, exc_info=True)
        return NullLed()
