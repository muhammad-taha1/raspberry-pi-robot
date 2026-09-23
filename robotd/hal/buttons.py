"""Push-button seam. The brain's ears are wired to a physical button."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Protocol

logger = logging.getLogger(__name__)


class Button(Protocol):
    def on_press(self, callback: Callable[[], None]) -> None: ...
    def is_pressed(self) -> bool: ...
    def close(self) -> None: ...


class GpioButton:
    def __init__(self, pin: int) -> None:
        # Deferred so laptop tests can import this module without gpiozero.
        from gpiozero import Button as _Button

        self._button = _Button(pin, bounce_time=0.05)

    def on_press(self, callback: Callable[[], None]) -> None:
        self._button.when_pressed = callback

    def is_pressed(self) -> bool:
        return self._button.is_pressed

    def close(self) -> None:
        self._button.close()


class NullButton:
    """Used when the pin can't be claimed, so the daemon runs without push-to-talk."""

    def on_press(self, callback: Callable[[], None]) -> None: ...

    def is_pressed(self) -> bool:
        return False

    def close(self) -> None: ...


def open_button(pin: int) -> Button:
    try:
        return GpioButton(pin)
    except Exception:
        logger.warning(
            "Push-to-talk button on GPIO %s unavailable; continuing without it",
            pin,
            exc_info=True,
        )
        return NullButton()
