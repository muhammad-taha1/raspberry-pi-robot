"""HearingActor — owns the mic, the STT model and the push-to-talk button.

A second producer of Transcript, alongside POST /chat — BrainActor, VoiceActor
and every downstream actor are unchanged by this milestone.
"""

from __future__ import annotations

import logging

import pykka

from robotd.hal.audio import AudioChunk, Microphone
from robotd.hal.buttons import Button
from robotd.messages import StartListening, Transcript
from robotd.models.stt import SpeechToText

logger = logging.getLogger(__name__)

# Below this, a recording is a bounced tap, not an utterance — dropped before
# it ever pays for an inference.
MIN_SECONDS = 0.3


def _seconds(audio: AudioChunk) -> float:
    frame_bytes = audio.sample_width * audio.channels
    if frame_bytes == 0:
        return 0.0
    return len(audio.data) / frame_bytes / audio.sample_rate


class HearingActor(pykka.ThreadingActor):
    def __init__(
        self,
        mic: Microphone,
        stt: SpeechToText,
        brain: pykka.ActorRef,
        button: Button,
    ) -> None:
        super().__init__()
        self._mic = mic
        self._stt = stt
        self._brain = brain
        self._button = button

    def on_start(self) -> None:
        self._button.on_press(lambda: self.actor_ref.tell(StartListening()))

    def on_receive(self, message: object) -> None:
        if not isinstance(message, StartListening):
            return

        try:
            audio = self._mic.record(self._button.is_pressed)
            if _seconds(audio) < MIN_SECONDS:
                return

            text = self._stt.transcribe(audio)
            if not text:
                return

            self._brain.tell(Transcript(text))
        except Exception:
            # A bad frame or a device hiccup must not take the actor down —
            # there's no supervisor to restart it, so this would be permanent.
            logger.exception("listening failed")

    def on_stop(self) -> None:
        self._close()

    def on_failure(self, exception_type, exception_value, traceback) -> None:
        self._close()

    def _close(self) -> None:
        try:
            self._mic.close()
        except Exception:
            logger.exception("microphone close failed")
        try:
            self._button.close()
        except Exception:
            logger.exception("button close failed")
