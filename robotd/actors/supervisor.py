"""Starts and stops the actor tree. Not itself an actor."""

from __future__ import annotations

from robotd.config import RobotConfig
from robotd.hal.audio import PyAudioSpeaker
from robotd.hal.leds import open_led
from robotd.models.chat import open_chat
from robotd.models.llm import NeedleLlm
from robotd.models.tts import PiperTts
from robotd.tools import build_registry

from .brain import BrainActor
from .command import CommandActor, Route
from .status import StatusActor
from .status import command as led_command
from .voice import VoiceActor
from .voice import command as say_command


class Supervisor:
    def __init__(self, cfg: RobotConfig) -> None:
        # A missing voice model or output device fails at startup; the LED and
        # chat model degrade to no-ops instead (open_led / open_chat).
        tts = PiperTts(cfg.voice_model_path)
        speaker = PyAudioSpeaker()
        self.status = StatusActor.start(led=open_led(cfg.pin("led")))
        self.voice = VoiceActor.start(tts=tts, speaker=speaker)

        registry = build_registry(status=self.status)
        llm = NeedleLlm(registry.specs())
        chat = open_chat(cfg.chat_model_path)
        self.brain = BrainActor.start(llm=llm, registry=registry, voice=self.voice, chat=chat)

        self.commands = CommandActor.start(
            routes={
                "led": Route(target=self.status, translate=led_command),
                "voice": Route(target=self.voice, translate=say_command),
            }
        )

    def __enter__(self) -> "Supervisor":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.stop()

    def stop(self) -> None:
        self.commands.stop()
        self.brain.stop()
        self.voice.stop()
        self.status.stop()
