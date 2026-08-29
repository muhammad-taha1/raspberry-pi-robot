"""Loads config/robot.toml — the authoritative GPIO pin map.

Every device's pin is looked up through RobotConfig.pin(name) rather than
hardcoded, so the bring-up scripts in scripts/ and the robotd package can
never disagree about wiring.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CONFIG_PATH = Path("config/robot.toml")


class DuplicatePinError(ValueError):
    """Two different names claim the same GPIO pin."""


@dataclass(frozen=True)
class RobotConfig:
    pins: dict[str, int]

    def pin(self, name: str) -> int:
        return self.pins[name]


def load(path: str | Path = DEFAULT_CONFIG_PATH) -> RobotConfig:
    with Path(path).open("rb") as f:
        data = tomllib.load(f)

    pins: dict[str, int] = data.get("pins", {})
    _check_duplicates(pins)
    return RobotConfig(pins=pins)


def _check_duplicates(pins: dict[str, int]) -> None:
    claimed_by: dict[int, str] = {}
    for name, gpio in pins.items():
        if gpio in claimed_by:
            raise DuplicatePinError(
                f"GPIO {gpio} is claimed by both '{claimed_by[gpio]}' and '{name}'"
            )
        claimed_by[gpio] = name
