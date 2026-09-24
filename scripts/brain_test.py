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
from robotd.tools import build_registry


class PrintingLight:
    """Stands in for LightActor's ref so the bench runs the real tool schema."""

    def tell(self, message: object) -> None:
        print(f"[tool] {message}")


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

    tools = [
        needle.tool(triggers=list(spec.triggers))(spec.fn) if spec.triggers else needle.tool(spec.fn)
        for spec in build_registry(light=PrintingLight()).specs()
    ]
    agent = needle.Needle(tools=tools, system=SYSTEM_FACTS)

    for text in args.turns or [args.text]:
        run_turn(agent, text)


if __name__ == "__main__":
    main()
