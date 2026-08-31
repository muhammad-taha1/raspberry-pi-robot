"""StatusActor — owns the status LED. The first actor in the tree.

Blinking is driven by a self-rearming `threading.Timer` that re-`tell()`s the
actor a private `_Tick`, never by `sleep()` inside `on_receive` — the mailbox
must stay free. This is the same shape the dead-man's switch will use once
motors arrive (M14).
"""

from __future__ import annotations

import threading

import pykka

from robotd.hal.leds import Led
from robotd.messages import Blink, SetLed


class _Tick:
    """Internal scheduling signal — not bus traffic, so it stays out of messages.py."""


class StatusActor(pykka.ThreadingActor):
    def __init__(self, led: Led) -> None:
        super().__init__()
        self._led = led
        self._blink_interval: float | None = None
        self._blink_on = False
        self._timer: threading.Timer | None = None

    def on_receive(self, message: object) -> None:
        if isinstance(message, SetLed):
            self._stop_blink()
            self._led.on() if message.on else self._led.off()
        elif isinstance(message, Blink):
            self._blink_interval = message.interval
            self._blink_on = False
            self._arm_tick()
        elif isinstance(message, _Tick):
            self._on_tick()

    def _on_tick(self) -> None:
        if self._blink_interval is None:
            return  # a SetLed cancelled the blink before this tick landed
        self._blink_on = not self._blink_on
        self._led.on() if self._blink_on else self._led.off()
        self._arm_tick()

    def _arm_tick(self) -> None:
        assert self._blink_interval is not None
        self._timer = threading.Timer(self._blink_interval, self._send_tick)
        self._timer.daemon = True
        self._timer.start()

    def _send_tick(self) -> None:
        self.actor_ref.tell(_Tick())

    def _stop_blink(self) -> None:
        self._blink_interval = None
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def on_stop(self) -> None:
        self._shutdown()

    def on_failure(self, exception_type, exception_value, traceback) -> None:
        self._shutdown()

    def _shutdown(self) -> None:
        self._stop_blink()
        try:
            self._led.off()
        finally:
            self._led.close()
