"""LLM seam — a tool-calling brain. Dispatching the calls is the caller's job."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Protocol

# Needle's system= only recognises a fixed set of keys (date, locale, device,
# battery, network, location, user, assistant) and free-associates if given
# nothing. Facts only, never instructions.
SYSTEM_FACTS = "locale: en-GB; device: raspberry pi desk robot; assistant: Alfred"

# Needle auto-suppresses below 0.1; its docs recommend gating act/don't-act at 0.7.
CONFIDENCE_FLOOR = 0.7

# NeedleLlm reuses one agent as a multi-turn chat log, so bound the run —
# otherwise one bad turn's reasoning anchors every later turn.
MAX_TURNS = 3
IDLE_RESET_SECONDS = 300


def apply_floor(
    calls: list[ToolCall],
    suppressed: list[ToolCall],
    confidence: float | None,
    exempt: set[str],
) -> tuple[list[ToolCall], list[ToolCall]]:
    """Hold back calls too uncertain to actuate hardware. `exempt` names tools
    whose trigger regex matched — Needle ships those below its own floor on
    purpose. A None confidence (weights without the calibration head) never gates.
    """
    if confidence is None or confidence >= CONFIDENCE_FLOOR:
        return calls, suppressed

    kept = [c for c in calls if c.name in exempt]
    held = [c for c in calls if c.name not in exempt]
    return kept, suppressed + held


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict


@dataclass(frozen=True)
class ToolSpec:
    """A tool for a provider to declare: the function (its name/docstring/hints
    are the schema) plus trigger regexes that force a call regardless of confidence.
    """

    fn: object
    triggers: tuple[str, ...] = ()


@dataclass(frozen=True)
class Completion:
    tool_calls: list[ToolCall]
    reasoning: str
    confidence: float | None
    ok: bool = True
    error: str | None = None
    suppressed_calls: list[ToolCall] = field(default_factory=list)
    ungrounded: bool = False


class LlmProvider(Protocol):
    def complete(self, text: str) -> Completion: ...


class NeedleLlm:
    """Needle 3, on-device. Owns its own conversation history."""

    def __init__(self, specs: list[ToolSpec]) -> None:
        # Deferred so laptop tests can import this module without cactus-needle.
        import needle

        self._specs = list(specs)
        tools = [
            needle.tool(triggers=list(spec.triggers))(spec.fn)
            if spec.triggers
            else needle.tool(spec.fn)
            for spec in self._specs
        ]
        self._agent = needle.Needle(tools=tools, system=SYSTEM_FACTS)
        self._turns = 0
        self._last = time.monotonic()

    def complete(self, text: str) -> Completion:
        now = time.monotonic()
        if self._turns >= MAX_TURNS or now - self._last >= IDLE_RESET_SECONDS:
            self._agent.reset()
            self._turns = 0
        self._turns += 1
        self._last = now

        result = self._agent.complete(text)
        calls = [
            ToolCall(call["name"], call["arguments"])
            for call in result["function_calls"]
        ]
        suppressed = [
            ToolCall(call["name"], call["arguments"])
            for call in result.get("suppressed_calls", [])
        ]

        exempt = {
            spec.fn.__name__
            for spec in self._specs
            if any(re.search(pattern, text, re.IGNORECASE) for pattern in spec.triggers)
        }
        calls, suppressed = apply_floor(calls, suppressed, result["confidence"], exempt)

        return Completion(
            tool_calls=calls,
            reasoning=result["reasoning"],
            confidence=result["confidence"],
            ok=result.get("success", True),
            error=result.get("error"),
            suppressed_calls=suppressed,
            ungrounded=bool((result.get("validation") or {}).get("ungrounded", False)),
        )
