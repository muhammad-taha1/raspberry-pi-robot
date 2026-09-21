"""HTTP boundary — transport only. Reads a request, asks CommandActor or
BrainActor, writes a response. Knows nothing about device names or message
types except two deliberate exceptions: POST /say hardcodes the "voice"
device, because an utterance is a {text} body, not a {device, action} one,
and POST /chat talks to BrainActor directly rather than through the route
table, because a reply is the whole point of /chat and CommandActor's
tell()-and-return-immediately shape structurally cannot carry one back.

parse_command/parse_say/parse_chat/status_for are plain functions so the
actual logic (parsing, status-code choice) is testable without a socket or
an actor. do_GET/do_POST are just wiring around them, trusted rather than
tested — verified for real on the Pi with curl (see AGENTS.md).
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pykka

from robotd.messages import ChatReply, Command, CommandResult, Transcript

COMMAND_PORT = 8080
STATIC_DIR = Path(__file__).parent / "static"

COMMAND_TIMEOUT = 2
CHAT_TIMEOUT = 30


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


def parse_chat(body: bytes) -> str:
    """Raises ValueError (or a json/KeyError, all caught alike) on bad input."""
    payload = json.loads(body)
    text = payload["text"]
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text must be a non-empty string")
    return text


def status_for(result: CommandResult) -> int:
    return 200 if result.ok else 400


def chat_body(reply: ChatReply) -> dict:
    return {
        "ok": True,
        "reasoning": reply.reasoning,
        "confidence": reply.confidence,
        "calls": [{"name": c.name, "arguments": c.arguments} for c in reply.tool_calls],
    }


class CommandServer(ThreadingHTTPServer):
    def __init__(
        self, address: tuple[str, int], commands: pykka.ActorRef, brain: pykka.ActorRef
    ) -> None:
        super().__init__(address, _Handler)
        self.commands = commands
        self.brain = brain


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
            self._handle_command(parse_command, "expected {device, action}")
        elif self.path == "/say":
            self._handle_command(
                lambda body: Command("voice", parse_say(body)), "expected {text}"
            )
        elif self.path == "/chat":
            self._handle_chat()
        else:
            self._respond(404, {"ok": False, "detail": "not found"})

    def _handle_command(self, parse, bad_request_detail: str) -> None:
        length = int(self.headers.get("Content-Length", 0))
        try:
            cmd = parse(self.rfile.read(length))
        except (json.JSONDecodeError, KeyError, ValueError):
            self._respond(400, {"ok": False, "detail": bad_request_detail})
            return

        result = self.server.commands.ask(cmd, timeout=COMMAND_TIMEOUT)
        self._respond(status_for(result), {"ok": result.ok, "detail": result.detail})

    def _handle_chat(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        try:
            text = parse_chat(self.rfile.read(length))
        except (json.JSONDecodeError, KeyError, ValueError):
            self._respond(400, {"ok": False, "detail": "expected {text}"})
            return

        reply = self.server.brain.ask(Transcript(text), timeout=CHAT_TIMEOUT)
        self._respond(200, chat_body(reply))

    def _respond(self, status: int, body: dict) -> None:
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        pass  # quiet by default; robotd's own prints are the log


def serve(
    commands: pykka.ActorRef, brain: pykka.ActorRef, port: int = COMMAND_PORT
) -> CommandServer:
    """Start the server on a daemon thread and return it, already listening."""
    server = CommandServer(("0.0.0.0", port), commands, brain)
    Thread(target=server.serve_forever, daemon=True).start()
    return server
