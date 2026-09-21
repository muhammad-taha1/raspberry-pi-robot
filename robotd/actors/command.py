"""CommandActor — routes external Command requests via a device->Route table."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pykka

from robotd.messages import Command, CommandResult

Translator = Callable[[str], object | None]


@dataclass(frozen=True)
class Route:
    target: pykka.ActorRef
    translate: Translator


class CommandActor(pykka.ThreadingActor):
    def __init__(self, routes: dict[str, Route]) -> None:
        super().__init__()
        self._routes = routes

    def on_receive(self, message: object) -> CommandResult | None:
        if not isinstance(message, Command):
            return None

        route = self._routes.get(message.device)
        if route is None:
            return CommandResult(False, f"unknown device '{message.device}'")

        msg = route.translate(message.action)
        if msg is None:
            return CommandResult(False, f"unknown action '{message.action}'")

        route.target.tell(msg)
        return CommandResult(True, message.action)
