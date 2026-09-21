"""HTTP boundary — decodes a request, asks an actor, writes a response."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pykka

from robotd.messages import Command, Transcript

COMMAND_PORT = 8080
STATIC_DIR = Path(__file__).parent / "static"

COMMAND_TIMEOUT = 2
CHAT_TIMEOUT = 30


def parse_command(body: bytes) -> Command:
    payload = json.loads(body)
    return Command(payload["device"], payload["action"])


def parse_text(body: bytes) -> str:
    text = json.loads(body)["text"]
    if not text.strip():
        raise ValueError("text must not be empty")
    return text


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
                lambda body: Command("voice", parse_text(body)), "expected {text}"
            )
        elif self.path == "/chat":
            self._handle_chat()
        else:
            self._respond(404, {"ok": False, "detail": "not found"})

    def _body(self) -> bytes:
        return self.rfile.read(int(self.headers.get("Content-Length", 0)))

    def _handle_command(self, parse, bad_request_detail: str) -> None:
        try:
            cmd = parse(self._body())
        except Exception:
            self._respond(400, {"ok": False, "detail": bad_request_detail})
            return

        result = self.server.commands.ask(cmd, timeout=COMMAND_TIMEOUT)
        self._respond(200 if result.ok else 400, {"ok": result.ok, "detail": result.detail})

    def _handle_chat(self) -> None:
        try:
            text = parse_text(self._body())
        except Exception:
            self._respond(400, {"ok": False, "detail": "expected {text}"})
            return

        try:
            reply = self.server.brain.ask(Transcript(text), timeout=CHAT_TIMEOUT)
        except pykka.Timeout:
            self._respond(504, {"ok": False, "detail": "brain did not reply in time"})
            return

        self._respond(
            200,
            {
                "ok": reply.error is None,
                "text": reply.text,
                "reasoning": reply.reasoning,
                "confidence": reply.confidence,
                "calls": [{"name": c.name, "arguments": c.arguments} for c in reply.tool_calls],
                "error": reply.error,
                "suppressed_calls": [
                    {"name": c.name, "arguments": c.arguments} for c in reply.suppressed_calls
                ],
                "ungrounded": reply.ungrounded,
            },
        )

    def _respond(self, status: int, body: dict) -> None:
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        pass


def serve(commands: pykka.ActorRef, brain: pykka.ActorRef) -> CommandServer:
    server = CommandServer(("0.0.0.0", COMMAND_PORT), commands, brain)
    Thread(target=server.serve_forever, daemon=True).start()
    return server
