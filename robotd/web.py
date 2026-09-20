"""HTTP boundary — transport only. Reads a request, asks CommandActor, writes
a response. Knows nothing about device names or message types except one
deliberate exception: POST /say hardcodes the "voice" device, because an
utterance is a {text} body, not a {device, action} one, and CommandActor's
Command still needs a device name to route on.

parse_command/parse_say/status_for are plain functions so the actual logic
(parsing, status-code choice) is testable without a socket or an actor.
do_GET/do_POST are just wiring around them, trusted rather than tested —
verified for real on the Pi with curl (see AGENTS.md).
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pykka

from robotd.messages import Command, CommandResult

COMMAND_PORT = 8080
STATIC_DIR = Path(__file__).parent / "static"


def parse_command(body: bytes) -> Command:
    """Raises ValueError (or a json/KeyError, all caught alike) on bad input."""
    payload = json.loads(body)
    device = payload["device"]
    action = payload["action"]
    if not isinstance(device, str) or not isinstance(action, str):
        raise ValueError("device and action must be strings")
    return Command(device, action)


def parse_say(body: bytes) -> str:
    """Raises ValueError (or a json/KeyError, all caught alike) on bad input."""
    payload = json.loads(body)
    text = payload["text"]
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text must be a non-empty string")
    return text


def status_for(result: CommandResult) -> int:
    return 200 if result.ok else 400


class CommandServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], commands: pykka.ActorRef) -> None:
        super().__init__(address, _Handler)
        self.commands = commands


class _Handler(BaseHTTPRequestHandler):
    server: CommandServer

    def do_GET(self) -> None:
        if self.path != "/":
            self._respond(404, {"ok": False, "detail": "not found"})
            return

        html = (STATIC_DIR / "index.html").read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)

    def do_POST(self) -> None:
        if self.path == "/command":
            self._handle(parse_command, "expected {device, action}")
        elif self.path == "/say":
            self._handle(
                lambda body: Command("voice", parse_say(body)), "expected {text}"
            )
        else:
            self._respond(404, {"ok": False, "detail": "not found"})

    def _handle(self, parse, bad_request_detail: str) -> None:
        length = int(self.headers.get("Content-Length", 0))
        try:
            cmd = parse(self.rfile.read(length))
        except (json.JSONDecodeError, KeyError, ValueError):
            self._respond(400, {"ok": False, "detail": bad_request_detail})
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
