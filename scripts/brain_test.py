"""Bring-up spike for Needle 3 on the Pi: confirms cactus-needle installs,
loads its cached weights, and produces tool calls with a confidence score in
a few seconds.

This is a hardware/model bring-up bench: it intentionally bypasses robotd's
models/ and actors so install, download, and inference-speed faults can be
diagnosed directly, the same way voice_test.py does for Piper.
"""

from __future__ import annotations

import argparse

import needle


@needle.tool
def set_led(on: bool) -> None:
    """Turn the robot's status LED on or off."""
    print(f"[tool] set_led(on={on})")


@needle.tool
def say(text: str) -> None:
    """Speak a sentence out loud."""
    print(f"[tool] say(text={text!r})")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--text", default="turn the light on and say good evening"
    )
    args = parser.parse_args()

    agent = needle.Needle(tools=[set_led, say])
    result = agent.complete(args.text)

    print("function_calls:", result["function_calls"])
    print("reasoning:", result["reasoning"])
    print("confidence:", result["confidence"])
    print("decode_tps:", result["decode_tps"])
    print("peak_ram_mb:", result["peak_ram_mb"])


if __name__ == "__main__":
    main()
