"""VoiceActor — owns text-to-speech and speaker playback."""

from __future__ import annotations

import logging

import pykka

from robotd.hal.audio import Speaker
from robotd.messages import Speak
from robotd.models.tts import TextToSpeech

logger = logging.getLogger(__name__)


class VoiceActor(pykka.ThreadingActor):
    def __init__(self, tts: TextToSpeech, speaker: Speaker) -> None:
        super().__init__()
        self._tts = tts
        self._speaker = speaker

    def on_receive(self, message: object) -> None:
        if isinstance(message, Speak):
            try:
                self._speaker.play(self._tts.synthesize(message.text))
            except Exception:
                # A bad frame or a device hiccup must not take the actor down —
                # there's no supervisor to restart it, so this would be permanent.
                logger.exception("playback failed")

    def on_stop(self) -> None:
        self._close()

    def on_failure(self, exception_type, exception_value, traceback) -> None:
        self._close()

    def _close(self) -> None:
        try:
            self._speaker.close()
        except Exception:
            logger.exception("speaker close failed")
