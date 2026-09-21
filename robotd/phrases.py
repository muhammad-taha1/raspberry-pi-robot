"""Generic spoken phrases. Tool-agnostic — dispatch is tell(), so the brain
knows a message reached the device actor, not that the device responded.
"""

from __future__ import annotations

import random

ACK: tuple[str, ...] = ("Done.", "Task completed.", "All set.")
FAILED: tuple[str, ...] = ("That didn't work.", "I couldn't do that.")
UNSURE: tuple[str, ...] = (
    "I'm not sure how to answer that.",
    "I don't have an answer for that one.",
)


def pick(phrases: tuple[str, ...]) -> str:
    return random.choice(phrases)
