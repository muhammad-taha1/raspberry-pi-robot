"""Test doubles implementing robotd/hal protocols. Never shipped in robotd/."""

from __future__ import annotations


class RecordingLed:
    """Implements Led. Records every call for assertion."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def on(self) -> None:
        self.calls.append("on")

    def off(self) -> None:
        self.calls.append("off")

    def close(self) -> None:
        self.calls.append("close")


class RaisingLed:
    """Implements Led. Raises on on() — proves shutdown still turns it off and closes it."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def on(self) -> None:
        self.calls.append("on")
        raise RuntimeError("led hardware fault")

    def off(self) -> None:
        self.calls.append("off")

    def close(self) -> None:
        self.calls.append("close")
