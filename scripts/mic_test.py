"""Record a few seconds from the mic and play it straight back, via arecord/aplay.

Below the HAL on purpose, same as speaker_test.py — answers "is the capture
device even there, at all?" before any Python audio library is involved.
"""

from __future__ import annotations

import subprocess

SAMPLE_RATE = 16_000
DURATION_SECONDS = 3


def main() -> None:
    # ALSA's default device, pinned to the USB card by /etc/asound.conf — the
    # same path PyAudioMicrophone takes, so a pass here means the daemon's mic works.
    print(f"Recording {DURATION_SECONDS}s from the ALSA default input — speak now...")
    recording = subprocess.run(
        [
            "arecord",
            "--quiet",
            "--format=S16_LE",
            f"--rate={SAMPLE_RATE}",
            "--channels=1",
            f"--duration={DURATION_SECONDS}",
            "--file-type=raw",
        ],
        capture_output=True,
        check=True,
    ).stdout

    print("Playing it back...")
    subprocess.run(
        [
            "aplay",
            "--quiet",
            "--format=S16_LE",
            f"--rate={SAMPLE_RATE}",
            "--channels=1",
            "--file-type=raw",
        ],
        input=recording,
        check=True,
    )


if __name__ == "__main__":
    main()
