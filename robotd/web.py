"""HTTP boundary — transport only. Reads a request, asks CommandActor, writes
a response. Knows nothing about device names or message types; all of that
lives in robotd/actors/command.py.

parse_command/status_for are plain functions so the actual logic (parsing,
status-code choice) is testable without a socket or an actor. do_POST is
just wiring around them, trusted rather than tested — verified for real on
the Pi with curl (see AGENTS.md).
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pykka

from robotd.messages import Command, CommandResult

COMMAND_PORT = 8080


def parse_command(body: bytes) -> Command:
    """Raises ValueError (or a json/KeyError, all caught alike) on bad input."""
    payload = json.loads(body)
    device = payload["device"]
    action = payload["action"]
    if not isinstance(device, str) or not isinstance(action, str):
        raise ValueError("device and action must be strings")
    return Command(device, action)


def status_for(result: CommandResult) -> int:
    return 200 if result.ok else 400


class CommandServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], commands: pykka.ActorRef) -> None:
        super().__init__(address, _Handler)
        self.commands = commands


class _Handler(BaseHTTPRequestHandler):
    server: CommandServer

    def do_POST(self) -> None:
        if self.path != "/command":
            self._respond(404, {"ok": False, "detail": "not found"})
            return

        length = int(self.headers.get("Content-Length", 0))
        try:
            cmd = parse_command(self.rfile.read(length))
        except (json.JSONDecodeError, KeyError, ValueError):
            self._respond(400, {"ok": False, "detail": "expected {device, action}"})
            return

        result = self.server.commands.ask(cmd, timeout=2)
        self._respond(status_for(result), {"ok": result.ok, "detail": result.detail})

    def _respond(self, status: int, body: dict) -> None:
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        pass  # quiet by default; robotd's own prints are the log


def serve(commands: pykka.ActorRef, port: int = COMMAND_PORT) -> CommandServer:
    """Start the server on a daemon thread and return it, already listening."""
    server = CommandServer(("0.0.0.0", port), commands)
    Thread(target=server.serve_forever, daemon=True).start()
    return server
