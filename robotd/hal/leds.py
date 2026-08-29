from typing import Protocol

from gpiozero import LED


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
