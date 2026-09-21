"""Bring-up bench for Needle 3 on the Pi — bypasses robotd's actors.

    python scripts/brain_test.py --text "turn the light on"
    python scripts/brain_test.py --turns "hey there" "turn on the light"

--turns sends several utterances through one agent without resetting, which is
how you reproduce Needle's history poisoning.
"""

from __future__ import annotations

import argparse

import needle

from robotd.models.llm import SYSTEM_FACTS
from robotd.tools import LED_TRIGGERS


@needle.tool(triggers=list(LED_TRIGGERS))
def set_led(on: bool) -> None:
    """Turn the robot's status LED on or off.

    Also known as the light, the lamp, or the LED.

    Args:
        on: True to switch the LED on, False to switch it off.
    """
    print(f"[tool] set_led(on={on})")


def run_turn(agent: "needle.Needle", text: str) -> None:
    result = agent.complete(text)
    print(f"\nyou: {text}")
    print("function_calls:", result["function_calls"])
    print("suppressed_calls:", result.get("suppressed_calls"))
    print("reasoning:", result["reasoning"])
    print("confidence:", result["confidence"])
    print("decode_tps:", result["decode_tps"])
    print("peak_ram_mb:", result["peak_ram_mb"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", default="turn the light on and say good evening")
    parser.add_argument("--turns", nargs="+")
    args = parser.parse_args()

    agent = needle.Needle(tools=[set_led], system=SYSTEM_FACTS)

    for text in args.turns or [args.text]:
        run_turn(agent, text)


if __name__ == "__main__":
    main()
