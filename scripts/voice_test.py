"""Speak one line through Piper and the system-default output on the Pi.

This is a hardware bring-up bench: it intentionally bypasses robotd's HAL and
actors so model, PortAudio, and USB-speaker faults can be diagnosed directly.
"""

from __future__ import annotations

import argparse

import pyaudio
from piper import PiperVoice

from robotd.config import DEFAULT_CONFIG_PATH, load


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--text", default="hi i am raspberry pi, i am yourr personal assistant. ask me anything, i know everything, did you know the color of the sun is actually white?")
    args = parser.parse_args()

    voice = PiperVoice.load(str(load(args.config).voice_model_path))
    audio = pyaudio.PyAudio()
    stream = None
    try:
        for chunk in voice.synthesize(args.text):
            if stream is None:
                stream = audio.open(
                    format=audio.get_format_from_width(chunk.sample_width),
                    channels=chunk.sample_channels,
                    rate=chunk.sample_rate,
                    output=True,
                )
            stream.write(chunk.audio_int16_bytes)
    finally:
        if stream is not None:
            stream.stop_stream()
            stream.close()
        audio.terminate()


if __name__ == "__main__":
    main()
