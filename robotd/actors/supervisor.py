"""Starts and stops the actor tree. A plain lifecycle holder, not itself an
actor — nothing needs to send it messages yet.
"""

from __future__ import annotations

from robotd.config import RobotConfig
from robotd.hal.audio import PyAudioSpeaker
from robotd.hal.leds import GpioLed
from robotd.models.tts import PiperTts

from .command import CommandActor, Route
from .status import StatusActor
from .status import command as led_command
from .voice import VoiceActor


class Supervisor:
    def __init__(self, cfg: RobotConfig) -> None:
        # Initialise external dependencies before starting actors. A missing voice
        # model or unavailable output device must fail cleanly at startup.
        tts = PiperTts(cfg.voice_model_path)
        speaker = PyAudioSpeaker()
        self.status = StatusActor.start(led=GpioLed(cfg.pin("led")))
        self.voice = VoiceActor.start(tts=tts, speaker=speaker)
        self.commands = CommandActor.start(
            routes={"led": Route(target=self.status, translate=led_command)}
        )

    def __enter__(self) -> "Supervisor":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.stop()

    def stop(self) -> None:
        self.commands.stop()
        self.voice.stop()
        self.status.stop()
