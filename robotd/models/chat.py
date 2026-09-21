"""Chat model seam — the robot's mouth for anything Needle can't serve as a
tool call (jokes, greetings, small talk). Separate from LlmProvider on
purpose: Needle never generates prose, so this is a second protocol rather
than a resurrected Completion.text.

Mirrors robotd/models/tts.py's shape (protocol + one real impl, deferred
import) and robotd/hal/leds.py's open_led() (degrade to a no-op with a
logged warning rather than crash the daemon).
"""

from __future__ import annotations

import logging
from collections import deque
from pathlib import Path
from typing import Protocol

from robotd import phrases

logger = logging.getLogger(__name__)

PERSONA = (
    "You are a small desk companion robot. Answer in one or two short spoken "
    "sentences. Never output JSON, code, or invent tool names — just talk."
)

HISTORY_TURNS = 4


class ChatProvider(Protocol):
    def reply(self, text: str) -> str: ...


class LlamaCppChat:
    """A small local GGUF, loaded once and reused. Owns its own short
    conversation window, the same way NeedleLlm owns its 256-token window —
    BrainActor still holds no history.
    """

    def __init__(self, model_path: str | Path) -> None:
        # Deferred so laptop tests can import this module without a compiled
        # llama.cpp or any GGUF on disk.
        from llama_cpp import Llama

        self._llm = Llama(model_path=str(model_path), n_ctx=1024, n_threads=4, verbose=False)
        self._history: deque[tuple[str, str]] = deque(maxlen=HISTORY_TURNS)

    def reply(self, text: str) -> str:
        messages = [{"role": "system", "content": PERSONA}]
        for user, assistant in self._history:
            messages.append({"role": "user", "content": user})
            messages.append({"role": "assistant", "content": assistant})
        messages.append({"role": "user", "content": text})

        result = self._llm.create_chat_completion(
            messages=messages,
            max_tokens=80,
            temperature=0.1,
            top_k=50,
            repeat_penalty=1.05,
        )
        spoken = result["choices"][0]["message"]["content"].strip()
        self._history.append((text, spoken))
        return spoken


class NullChat:
    """The real no-weights behaviour — not a test double. Used when the
    configured GGUF is missing so the daemon keeps running with chat
    unavailable, instead of crashing at startup.
    """

    def reply(self, text: str) -> str:
        return phrases.pick(phrases.UNSURE)


def open_chat(model_path: str | Path) -> ChatProvider:
    """Load the chat model, falling back to NullChat with a warning if the
    GGUF is missing or fails to load.
    """
    if not Path(model_path).exists():
        logger.warning("Chat model %s not found; chat replies unavailable", model_path)
        return NullChat()
    try:
        return LlamaCppChat(model_path)
    except Exception:
        logger.warning("Chat model %s failed to load; chat replies unavailable", model_path, exc_info=True)
        return NullChat()
