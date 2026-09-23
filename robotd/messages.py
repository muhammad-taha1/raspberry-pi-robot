"""The message contract — what actors send each other. Pykka dispatches on type."""

from __future__ import annotations

from dataclasses import dataclass, field

from robotd.models.llm import ToolCall


@dataclass(frozen=True)
class SetLed:
    turn_on: bool


@dataclass(frozen=True)
class Speak:
    text: str


@dataclass(frozen=True)
class Transcript:
    text: str


@dataclass(frozen=True)
class StartListening:
    """Sent by a button press. HearingActor records for as long as the button
    stays held — the release is a predicate it polls, never a second message,
    since the actor's mailbox is busy recording when the button comes up.
    """


@dataclass(frozen=True)
class GetState:
    """Asked of BrainActor; returns list[Turn], most recent last."""


@dataclass(frozen=True)
class Turn:
    heard: str
    spoken: str


@dataclass(frozen=True)
class ChatReply:
    text: str
    tool_calls: list[ToolCall]
    reasoning: str
    confidence: float | None
    error: str | None = None
    suppressed_calls: list[ToolCall] = field(default_factory=list)
    ungrounded: bool = False
