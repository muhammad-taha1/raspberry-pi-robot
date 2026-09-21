"""VoiceActor — owns text-to-speech and speaker playback."""

from __future__ import annotations

import pykka

from robotd.hal.audio import Speaker
from robotd.messages import Speak
from robotd.models.tts import TextToSpeech


def command(action: str) -> Speak:
    return Speak(action)


class VoiceActor(pykka.ThreadingActor):
    def __init__(self, tts: TextToSpeech, speaker: Speaker) -> None:
        super().__init__()
        self._tts = tts
        self._speaker = speaker

    def on_receive(self, message: object) -> None:
        if isinstance(message, Speak):
            self._speaker.play(self._tts.synthesize(message.text))

    def on_stop(self) -> None:
        self._speaker.close()

    def on_failure(self, exception_type, exception_value, traceback) -> None:
        self._speaker.close()
