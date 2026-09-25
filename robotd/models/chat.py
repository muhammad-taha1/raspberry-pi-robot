"""Chat seam — the robot's mouth for anything Needle can't serve as a tool call."""

from __future__ import annotations

import logging
import time
from collections import deque
from pathlib import Path
from typing import Protocol

from robotd import phrases

logger = logging.getLogger(__name__)

# Kept short on purpose: a 0.5B model loses long rule lists and will read
# quotable rules back verbatim. Says nothing about specific devices — Needle
# decides which tools run, and only Needle can actuate anything.
PERSONA = (
    "You are Alfred, a small desk robot with the manners of a polite, loyal "
    "knight, speaking modern English and now and then saying 'milord' or 'miss'. "
    "Reply in one or two short spoken sentences. "
    "You can only talk: you cannot operate devices or remember things."
)

# Tone is taught by example better than by instruction at this size. Prompts
# deliberately differ from scripts/chat_test.py's so the bench still measures
# generalisation, not copying.
FEW_SHOT: list[dict] = [
    {"role": "user", "content": "good evening"},
    {"role": "assistant", "content": "Good evening, milord. A pleasure to keep you company."},
    {"role": "user", "content": "open the window"},
    {"role": "assistant", "content": "Alas, I have no hands for that, milord, only my voice."},
]

# Qwen2.5-0.5B-Instruct's own generation_config.json values. Near-greedy
# sampling (temperature 0.1) made it parrot the prompt and stock phrases.
# max_tokens caps a runaway reply while leaving room for two sentences.
SAMPLING = {
    "max_tokens": 60,
    "temperature": 0.7,
    "top_p": 0.8,
    "top_k": 20,
    "repeat_penalty": 1.1,
}

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
        messages.append({"role": "user", "content": text})

        start = time.monotonic()
        result = self._llm.create_chat_completion(messages=messages, **SAMPLING)
        logger.info("chat_ms=%.0f", (time.monotonic() - start) * 1000)
        choice = result["choices"][0]
        spoken = choice["message"]["content"].strip()
        if choice.get("finish_reason") == "length":
            # Hit max_tokens mid-sentence; speaking half a sentence sounds broken.
            end = max(spoken.rfind(mark) for mark in ".!?")
            if end > 0:
                spoken = spoken[: end + 1]
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
