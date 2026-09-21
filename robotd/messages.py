"""The message contract — how actors talk to each other.

Each message is its own frozen dataclass carrying only its own fields. Pykka
dispatches on message *type*, so actors branch on `isinstance`/type rather than
a generic `if msg.kind == ...` ladder.
"""

from __future__ import annotations

from dataclasses import dataclass

from robotd.models.llm import ToolCall


class RobotMessage:
    """Marker base only — no fields, no behaviour."""


@dataclass(frozen=True)
class SetLed(RobotMessage):
    """Steady on/off."""

    on: bool


@dataclass(frozen=True)
class Speak(RobotMessage):
    """Text for VoiceActor to synthesize and play."""

    text: str


@dataclass(frozen=True)
class Command(RobotMessage):
    """An external request (e.g. from robotd/web.py) -> CommandActor."""

    device: str
    action: str


@dataclass(frozen=True)
class CommandResult:
    """Reply to a Command ask() — not bus traffic, so no RobotMessage base."""

    ok: bool
    detail: str


@dataclass(frozen=True)
class Transcript(RobotMessage):
    """Something heard -> BrainActor. Today from robotd/web.py's POST /chat;
    from M4 onward, HearingActor emits this exact message unchanged."""

    text: str


@dataclass(frozen=True)
class ChatReply:
    """Reply to a Transcript ask() — not bus traffic, so no RobotMessage base."""

    tool_calls: list[ToolCall]
    reasoning: str
    confidence: float | None
