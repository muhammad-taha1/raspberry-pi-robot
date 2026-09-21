"""LLM model seam — tool-calling brains behind one protocol.

`complete()` takes the latest utterance and returns the calls the model wants
made; dispatching those calls is the caller's job (robotd/tools.py), not the
provider's, so the same registry works no matter which provider is behind it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict


@dataclass(frozen=True)
class Completion:
    tool_calls: list[ToolCall]
    reasoning: str
    confidence: float | None


class LlmProvider(Protocol):
    def complete(self, text: str) -> Completion: ...


class NeedleLlm:
    """Needle 3, running fully on-device. Owns its own conversation history."""

    def __init__(self, functions: list[Callable]) -> None:
        # Deferred so laptop tests can import this module without cactus-needle.
        import needle

        self._agent = needle.Needle(tools=[needle.tool(fn) for fn in functions])

    def complete(self, text: str) -> Completion:
        result = self._agent.complete(text)
        calls = [
            ToolCall(call["name"], call["arguments"])
            for call in result["function_calls"]
        ]
        return Completion(
            tool_calls=calls,
            reasoning=result["reasoning"],
            confidence=result["confidence"],
        )
