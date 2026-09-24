"""Speak one line through Piper and the system-default output on the Pi.

    python scripts/voice_test.py
    python scripts/voice_test.py --length-scale 1.0 0.9 0.8 0.7

Several --length-scale values speak the line once at each pace, in order, so
config/robot.toml's [voice] length_scale can be picked by ear. Lower is faster.
"""

from __future__ import annotations

import argparse

import pyaudio
from piper import PiperVoice, SynthesisConfig

from robotd.config import load


def speak(voice: PiperVoice, audio: pyaudio.PyAudio, text: str, length_scale: float) -> float:
    """Returns the synthesized audio's length in seconds."""
    stream = None
    seconds = 0.0
    try:
        config = SynthesisConfig(length_scale=length_scale)
        for chunk in voice.synthesize(text, syn_config=config):
            if stream is None:
                stream = audio.open(
                    format=audio.get_format_from_width(chunk.sample_width),
                    channels=chunk.sample_channels,
                    rate=chunk.sample_rate,
                    output=True,
                )
            stream.write(chunk.audio_int16_bytes)
            seconds += len(chunk.audio_int16_bytes) / chunk.sample_width / chunk.sample_rate
    finally:
        if stream is not None:
            stream.stop_stream()
            stream.close()
    return seconds


def main() -> None:
    cfg = load()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--text", default="Good evening, sir. The light is on, and I am at your service."
    )
    parser.add_argument(
        "--length-scale", type=float, nargs="+", default=[cfg.voice_length_scale]
    )
    args = parser.parse_args()

    voice = PiperVoice.load(str(cfg.voice_model_path))
    audio = pyaudio.PyAudio()
    try:
        for length_scale in args.length_scale:
            print(f"length_scale {length_scale} ...", end=" ", flush=True)
            seconds = speak(voice, audio, args.text, length_scale)
            print(f"{seconds:.2f}s of audio")
    finally:
        audio.terminate()


if __name__ == "__main__":
    main()
