"""Chat seam — the robot's mouth for anything Needle can't serve as a tool call."""

from __future__ import annotations

import logging
import time
from collections import deque
from pathlib import Path
from typing import Protocol

from robotd import phrases

logger = logging.getLogger(__name__)

# Says nothing about specific devices — Needle decides which tools run, and a
# hardcoded list here would need editing every time tools.py grows. Personality
# stays light: a 350M model pushed into heavy period language gets incoherent.
PERSONA = (
    "You are Alfred, a small desk companion robot with the manner of a "
    "polite, dutiful medieval English knight — courteous and a little "
    "formal, occasionally 'milord'/'miss', but always clear, modern, plain "
    "English. Never full archaic language (no 'thee'/'thou'/'verily'). Never "
    "generic assistant phrases like 'How can I help you today?'. "
    "Answer in one or two short spoken sentences. Never output JSON, code, "
    "or invent tool names — just talk. You have no hands, motors, lights, or "
    "memory, so you cannot touch any device or remember things for the "
    "user — never claim you did. Speaking is not an action: telling a joke, "
    "writing a short verse, or sharing an opinion is just talking, so do it "
    "if asked."
)

# Two in-character exchanges, sent as real conversation turns (not prose
# instruction) right after PERSONA. A small, heavily instruction-tuned model
# resists tonal instructions far more than it resists factual ones — it
# followed "you are Alfred" but not "sound like a knight" — so showing the
# voice as example turns (pattern-matching) works better than describing it.
# The second example doubles as a live sample of declining a device action
# without breaking character, tying the two instructions together.
FEW_SHOT: list[dict] = [
    {"role": "user", "content": "hi"},
    {"role": "assistant", "content": "Good day to you. How might I serve?"},
    {"role": "user", "content": "turn on the light"},
    {"role": "assistant", "content": "I've no hands for that, milord — only my voice."},
]

# Appended right before the user turn — small models weight recency, and
# PERSONA's tone/no-action instructions get ignored 60+ tokens away from a
# direct imperative. Always true here: reply() is only reached when Needle
# dispatched nothing.
NO_ACTION = (
    "You just did nothing — no light, no motor, no memory. Only say you "
    "can't if this needs a device or memory you don't have; a joke, poem, "
    "or opinion is just talking, so go ahead. Keep the polite, dutiful "
    "knight's voice — no generic assistant talk."
)

# A longer window carried unrelated LED small-talk into "tell me a joke".
HISTORY_TURNS = 2


class ChatProvider(Protocol):
    def reply(self, text: str) -> str: ...


class LlamaCppChat:
    """A small local GGUF, loaded once. Owns its own short conversation window."""

    def __init__(self, model_path: str | Path) -> None:
        # Deferred so laptop tests can import this module without llama.cpp.
        from llama_cpp import Llama

        self._llm = Llama(model_path=str(model_path), n_ctx=1024, n_threads=4, verbose=False)
        self._history: deque[tuple[str, str]] = deque(maxlen=HISTORY_TURNS)

    def reply(self, text: str) -> str:
        messages = [{"role": "system", "content": PERSONA}, *FEW_SHOT]
        for user, assistant in self._history:
            messages.append({"role": "user", "content": user})
            messages.append({"role": "assistant", "content": assistant})
        messages.append({"role": "system", "content": NO_ACTION})
        messages.append({"role": "user", "content": text})

        start = time.monotonic()
        result = self._llm.create_chat_completion(
            messages=messages,
            max_tokens=80,
            temperature=0.1,
            top_k=50,
            repeat_penalty=1.05,
        )
        logger.info("chat_ms=%.0f", (time.monotonic() - start) * 1000)
        spoken = result["choices"][0]["message"]["content"].strip()
        self._history.append((text, spoken))
        return spoken


class NullChat:
    """Real no-weights behaviour, not a test double — used when the GGUF is missing."""

    def reply(self, text: str) -> str:
        return phrases.pick(phrases.UNSURE)


def open_chat(model_path: str | Path) -> ChatProvider:
    try:
        return LlamaCppChat(model_path)
    except Exception:
        logger.warning("Chat model %s unavailable; chat replies disabled", model_path, exc_info=True)
        return NullChat()
