"""Play a short test tone through the system-default audio output on the Pi."""

from __future__ import annotations

import math
import struct
import subprocess

SAMPLE_RATE = 44_100
DURATION_SECONDS = 1
FREQUENCY_HZ = 440


def main() -> None:
    samples = (
        int(0.2 * 32767 * math.sin(2 * math.pi * FREQUENCY_HZ * i / SAMPLE_RATE))
        for i in range(SAMPLE_RATE * DURATION_SECONDS)
    )
    pcm = b"".join(struct.pack("<h", sample) for sample in samples)
    subprocess.run(
        [
            "aplay",
            "--quiet",
            "--format=S16_LE",
            f"--rate={SAMPLE_RATE}",
            "--channels=1",
            "--file-type=raw",
        ],
        input=pcm,
        check=True,
    )


if __name__ == "__main__":
    main()
