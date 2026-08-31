"""CommandActor — translates external Command requests into typed messages.

Holds no device knowledge itself. It's handed a route table mapping device
name -> (target actor, action-string -> message translator) at construction,
so adding a device means adding a translator beside that device's own actor
and one line in the route table here, never an `if device == ...` branch.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pykka

from robotd.messages import Command, CommandResult, RobotMessage

Translator = Callable[[str], RobotMessage | None]


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
