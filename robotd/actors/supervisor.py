"""Starts and stops the actor tree. Not itself an actor."""

from __future__ import annotations

from robotd.config import RobotConfig
from robotd.hal.audio import PyAudioMicrophone, PyAudioSpeaker
from robotd.hal.buttons import open_button
from robotd.hal.leds import open_led
from robotd.models.chat import open_chat
from robotd.models.llm import NeedleLlm
from robotd.models.stt import WhisperStt
from robotd.models.tts import PiperTts
from robotd.tools import build_registry

from .brain import BrainActor
from .hearing import HearingActor
from .light import LightActor
from .voice import VoiceActor


class Supervisor:
    def __init__(self, cfg: RobotConfig) -> None:
        # A missing voice model or output device fails at startup; the LED,
        # chat model and button degrade to no-ops instead (open_led / open_chat
        # / open_button). The mic and STT model fail startup like the speaker —
        # they're the same USB device the speaker already hard-depends on, so
        # degrading one and not the other would be incoherent.
        tts = PiperTts(cfg.voice_model_path, cfg.voice_length_scale)
        speaker = PyAudioSpeaker()
        self.light = LightActor.start(led=open_led(cfg.pin("led")))
        self.voice = VoiceActor.start(tts=tts, speaker=speaker)

        registry = build_registry(light=self.light)
        llm = NeedleLlm(registry.specs())
        chat = open_chat(cfg.chat_model_path)
        self.brain = BrainActor.start(llm=llm, registry=registry, voice=self.voice, chat=chat)

        mic = PyAudioMicrophone()
        stt = WhisperStt(cfg.stt_model)
        self.hearing = HearingActor.start(
            mic=mic, stt=stt, brain=self.brain, button=open_button(cfg.pin("button"))
        )

    def __enter__(self) -> "Supervisor":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.stop()

    def stop(self) -> None:
        self.hearing.stop()
        self.brain.stop()
        self.voice.stop()
        self.light.stop()
