"""The message contract — what actors send each other. Pykka dispatches on type."""

from __future__ import annotations

from dataclasses import dataclass, field

from robotd.models.llm import ToolCall


@dataclass(frozen=True)
class SetLed:
    on: bool


@dataclass(frozen=True)
class Speak:
    text: str


@dataclass(frozen=True)
class Command:
    device: str
    action: str


@dataclass(frozen=True)
class CommandResult:
    ok: bool
    detail: str


@dataclass(frozen=True)
class Transcript:
    text: str


@dataclass(frozen=True)
class ChatReply:
    text: str
    tool_calls: list[ToolCall]
    reasoning: str
    confidence: float | None
    error: str | None = None
    suppressed_calls: list[ToolCall] = field(default_factory=list)
    ungrounded: bool = False
