"""Bring-up bench for the STT engine — text, latency, peak RSS, tiny.en vs base.en.

    python scripts/stt_test.py --seconds 4

Records one clip through the same PyAudioMicrophone the daemon uses, then
transcribes it with both model sizes so config/robot.toml's [stt] model can be
picked from real numbers on this board. Same role as chat_test.py / brain_test.py.
"""

from __future__ import annotations

import argparse
import array
import math
import resource
import time
import wave

from robotd.hal.audio import PyAudioMicrophone
from robotd.models.stt import WhisperStt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=4.0)
    parser.add_argument("--models", nargs="+", default=["tiny.en", "base.en"])
    parser.add_argument("--save", default="stt_test.wav")
    args = parser.parse_args()

    mic = PyAudioMicrophone()
    try:
        print(f"Recording {args.seconds}s from the default input — speak now...")
        deadline = time.monotonic() + args.seconds
        audio = mic.record(lambda: time.monotonic() < deadline)
        print(f"Captured {len(audio.data)} bytes at {audio.sample_rate} Hz")
    finally:
        mic.close()

    samples = array.array("h", audio.data)
    peak = max((abs(s) for s in samples), default=0)
    peak_dbfs = 20 * math.log10(peak / 32768) if peak else float("-inf")
    # Speech peaking much below about -20 dBFS is quiet enough to hurt Whisper.
    print(f"peak level: {peak_dbfs:.1f} dBFS")

    with wave.open(args.save, "wb") as wav:
        wav.setnchannels(audio.channels)
        wav.setsampwidth(audio.sample_width)
        wav.setframerate(audio.sample_rate)
        wav.writeframes(audio.data)
    print(f"saved to {args.save} — play it back with: aplay {args.save}")

    for model_name in args.models:
        print(f"\n--- {model_name} ---")
        load_start = time.monotonic()
        stt = WhisperStt(model_name)
        print(f"loaded in {time.monotonic() - load_start:.2f}s")

        start = time.monotonic()
        text = stt.transcribe(audio)
        elapsed = time.monotonic() - start
        peak_rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024

        print(f"text: {text!r}")
        print(f"latency: {elapsed:.2f}s")
        print(f"peak_rss_mb: {peak_rss_mb:.1f}")


if __name__ == "__main__":
    main()
