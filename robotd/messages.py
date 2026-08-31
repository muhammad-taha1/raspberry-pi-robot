"""The message contract — how actors talk to each other.

Each message is its own frozen dataclass carrying only its own fields. Pykka
dispatches on message *type*, so actors branch on `isinstance`/type rather than
a generic `if msg.kind == ...` ladder.
"""

from __future__ import annotations

from dataclasses import dataclass


class RobotMessage:
    """Marker base only — no fields, no behaviour."""


@dataclass(frozen=True)
class SetLed(RobotMessage):
    """Steady on/off."""

    on: bool
