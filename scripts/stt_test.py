"""Bring-up bench for the STT engine — text, latency, peak RSS, tiny.en vs base.en.

    python scripts/stt_test.py --seconds 4

Records one clip through the same PyAudioMicrophone the daemon uses, then
transcribes it with both model sizes so config/robot.toml's [stt] model can be
picked from real numbers on this board. Same role as chat_test.py / brain_test.py.
"""

from __future__ import annotations

import argparse
import resource
import time

from robotd.hal.audio import PyAudioMicrophone
from robotd.models.stt import WhisperStt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=4.0)
    parser.add_argument("--models", nargs="+", default=["tiny.en", "base.en"])
    args = parser.parse_args()

    mic = PyAudioMicrophone()
    try:
        print(f"Recording {args.seconds}s from the default input — speak now...")
        deadline = time.monotonic() + args.seconds
        audio = mic.record(lambda: time.monotonic() < deadline)
        print(f"Captured {len(audio.data)} bytes at {audio.sample_rate} Hz")
    finally:
        mic.close()

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
