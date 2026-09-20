"""VoiceActor — owns text-to-speech and speaker playback."""

from __future__ import annotations

import pykka

from robotd.hal.audio import Speaker
from robotd.messages import Speak
from robotd.models.tts import TextToSpeech


def command(action: str) -> Speak:
    """Translate a Command.action string into the message VoiceActor understands.

    Unlike StatusActor's on/off, voice has no fixed action vocabulary — the action
    string *is* the utterance, so this translator is total. Rejecting empty text is
    the HTTP boundary's job (robotd/web.py), not this actor's.
    """
    return Speak(action)


class VoiceActor(pykka.ThreadingActor):
    """Synthesizes and plays one Speak message at a time in mailbox order."""

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
