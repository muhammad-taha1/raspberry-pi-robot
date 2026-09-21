"""Generic spoken phrases for BrainActor's static replies.

Deliberately tool-agnostic — "Task completed", never "The light's on" — because
dispatch is tell() (fire-and-forget): the brain knows a message reached the
device actor, not that the device physically responded. Two consumers
(robotd/actors/brain.py, robotd/models/chat.py's NullChat), so this earns
being its own module rather than constants buried in one of them.
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
