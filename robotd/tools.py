"""ToolRegistry — how a device becomes something the brain can ask for.

A tool's name, docstring and type hints *are* the schema Needle reads.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

import pykka

from robotd.messages import SetLed
from robotd.models.llm import ToolCall, ToolSpec

logger = logging.getLogger(__name__)

LED_TRIGGERS = (
    r"\b(turn|switch|flick|put)\b.*\b(on|off)\b",
    r"\b(light|lights|lamp|led)\b.*\b(on|off)\b",
    r"\b(dark|darker)\b",
)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Callable] = {}
        self._triggers: dict[str, tuple[str, ...]] = {}

    def add_action(self, fn: Callable[..., None], triggers: tuple[str, ...] = ()) -> None:
        self._tools[fn.__name__] = fn
        self._triggers[fn.__name__] = triggers

    def specs(self) -> list[ToolSpec]:
        return [ToolSpec(fn, self._triggers[name]) for name, fn in self._tools.items()]

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


def build_registry(light: pykka.ActorRef) -> ToolRegistry:
    registry = ToolRegistry()

    def set_led(turn_on: bool) -> None:
        """Turn the desk light on or off.

        Also known as the lamp or the LED. If the user says it's dark, turn it on.

        Args:
            turn_on: True to switch the LED on, False to switch it off.
        """
        light.tell(SetLed(turn_on))

    registry.add_action(set_led, triggers=LED_TRIGGERS)
    return registry
