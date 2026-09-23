"""Loads config/robot.toml — the authoritative pin map and model paths."""

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
    mic_device_name: str
    stt_model: str

    def pin(self, name: str) -> int:
        return self.pins[name]


def load(path: str | Path = DEFAULT_CONFIG_PATH) -> RobotConfig:
    with Path(path).open("rb") as f:
        data = tomllib.load(f)

    return RobotConfig(
        pins=data["pins"],
        voice_model_path=Path(data["voice"]["model_path"]),
        chat_model_path=Path(data["chat"]["model_path"]),
        mic_device_name=data["mic"]["device_name"],
        stt_model=data["stt"]["model"],
    )
