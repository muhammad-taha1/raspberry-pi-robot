import logging
from typing import Protocol

from gpiozero import LED

logger = logging.getLogger(__name__)


class Led(Protocol):
    def on(self) -> None: ...
    def off(self) -> None: ...
    def close(self) -> None: ...


class NullLed:
    """Used when the pin can't be claimed, so the daemon runs without the LED."""

    def on(self) -> None: ...
    def off(self) -> None: ...
    def close(self) -> None: ...


def open_led(pin: int) -> Led:
    try:
        return LED(pin)
    except Exception:
        logger.warning("Status LED on GPIO %s unavailable; continuing without it", pin, exc_info=True)
        return NullLed()
