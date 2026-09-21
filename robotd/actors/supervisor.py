"""Starts and stops the actor tree. A plain lifecycle holder, not itself an
actor — nothing needs to send it messages yet.
"""

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
        # Initialise external dependencies before starting actors. A missing voice
        # model, unavailable output device, or broken model cache must fail cleanly
        # at startup. The LED is the exception: it's the device most likely to be
        # disconnected during bring-up, so a GPIO claim failure degrades to a
        # warning (see open_led) instead of taking the whole daemon down.
        tts = PiperTts(cfg.voice_model_path)
        speaker = PyAudioSpeaker()
        self.status = StatusActor.start(led=open_led(cfg.pin("led")))
        self.voice = VoiceActor.start(tts=tts, speaker=speaker)

        registry = build_registry(status=self.status)
        llm = NeedleLlm(registry.functions())
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
