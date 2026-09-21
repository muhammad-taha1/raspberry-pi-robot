"""HTTP boundary — decodes a request, asks an actor, writes a response."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pykka

from robotd.messages import Speak, Transcript

HTTP_PORT = 8080
STATIC_DIR = Path(__file__).parent / "static"

CHAT_TIMEOUT = 30


def parse_text(body: bytes) -> str:
    text = json.loads(body)["text"]
    if not text.strip():
        raise ValueError("text must not be empty")
    return text


class RobotServer(ThreadingHTTPServer):
    def __init__(
        self, address: tuple[str, int], voice: pykka.ActorRef, brain: pykka.ActorRef
    ) -> None:
        super().__init__(address, _Handler)
        self.voice = voice
        self.brain = brain


class _Handler(BaseHTTPRequestHandler):
    server: RobotServer

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
        if self.path == "/say":
            self._handle_say()
        elif self.path == "/chat":
            self._handle_chat()
        else:
            self._respond(404, {"ok": False, "detail": "not found"})

    def _body(self) -> bytes:
        return self.rfile.read(int(self.headers.get("Content-Length", 0)))

    def _handle_say(self) -> None:
        try:
            text = parse_text(self._body())
        except Exception:
            self._respond(400, {"ok": False, "detail": "expected {text}"})
            return

        self.server.voice.tell(Speak(text))
        self._respond(200, {"ok": True, "detail": text})

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


def serve(voice: pykka.ActorRef, brain: pykka.ActorRef) -> RobotServer:
    server = RobotServer(("0.0.0.0", HTTP_PORT), voice, brain)
    Thread(target=server.serve_forever, daemon=True).start()
    return server
