"""Starts and stops the actor tree. A plain lifecycle holder, not itself an
actor — nothing needs to send it messages yet.
"""

from __future__ import annotations

from robotd.config import RobotConfig
from robotd.hal.leds import GpioLed

from .status import StatusActor


class Supervisor:
    def __init__(self, cfg: RobotConfig) -> None:
        self.status = StatusActor.start(led=GpioLed(cfg.pin("led")))

    def __enter__(self) -> "Supervisor":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.stop()

    def stop(self) -> None:
        self.status.stop()
