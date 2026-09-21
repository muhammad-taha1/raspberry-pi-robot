"""Loads config/robot.toml — the robot's hardware and model configuration.

Every device's pin is looked up through RobotConfig.pin(name) rather than
hardcoded, so the bring-up scripts in scripts/ and the robotd package can
never disagree about wiring.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CONFIG_PATH = Path("config/robot.toml")


@dataclass(frozen=True)
class RobotConfig:
    pins: dict[str, int]
    voice_model_path: Path
    chat_model_path: Path

    def pin(self, name: str) -> int:
        return self.pins[name]


def load(path: str | Path = DEFAULT_CONFIG_PATH) -> RobotConfig:
    with Path(path).open("rb") as f:
        data = tomllib.load(f)

    return RobotConfig(
        pins=data.get("pins", {}),
        voice_model_path=Path(data["voice"]["model_path"]),
        chat_model_path=Path(data["chat"]["model_path"]),
    )
