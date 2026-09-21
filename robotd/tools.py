"""ToolRegistry — how a device becomes something the brain can ask for.

Without this, BrainActor would need to know every device by name. Instead it
knows zero devices: build_registry() wires each tool to a `tell()` into the
actor that owns the device, so dispatch never blocks and adding hardware
never touches BrainActor. A tool's name and description come from the
function itself (name, docstring, type hints) — that's the schema Needle
reads, so there's no parallel description string to drift out of sync.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

import pykka

from robotd.messages import SetLed
from robotd.models.llm import ToolCall

logger = logging.getLogger(__name__)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Callable] = {}

    def add_action(self, fn: Callable[..., None]) -> None:
        self._tools[fn.__name__] = fn

    def functions(self) -> list[Callable]:
        return list(self._tools.values())

    def dispatch(self, call: ToolCall) -> bool:
        fn = self._tools.get(call.name)
        if fn is None:
            logger.warning("ignoring unknown tool call '%s'", call.name)
            return False
        try:
            fn(**call.arguments)
        except TypeError:
            logger.warning("bad arguments for tool call '%s'", call.name, exc_info=True)
            return False
        return True


def build_registry(status: pykka.ActorRef) -> ToolRegistry:
    registry = ToolRegistry()

    def set_led(on: bool) -> None:
        """Turn the robot's status LED on or off."""
        status.tell(SetLed(on))

    registry.add_action(set_led)
    return registry
