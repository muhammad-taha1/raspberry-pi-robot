"""BrainActor — turns a Transcript into tool calls and, if nothing fires, a
spoken apology. Holds no device references (the registry has those) and no
conversation history (NeedleLlm owns that).
"""

from __future__ import annotations

import logging

import pykka

from robotd.messages import ChatReply, Speak, Transcript
from robotd.models.llm import LlmProvider
from robotd.tools import ToolRegistry

logger = logging.getLogger(__name__)

FALLBACK = "Sorry, I'm not sure how to do that."


class BrainActor(pykka.ThreadingActor):
    def __init__(self, llm: LlmProvider, registry: ToolRegistry, voice: pykka.ActorRef) -> None:
        super().__init__()
        self._llm = llm
        self._registry = registry
        self._voice = voice

    def on_receive(self, message: object) -> ChatReply | None:
        if not isinstance(message, Transcript):
            return None

        result = self._llm.complete(message.text)
        logger.info("confidence=%s reasoning=%s", result.confidence, result.reasoning)

        for call in result.tool_calls:
            self._registry.dispatch(call)
        if not result.tool_calls:
            self._voice.tell(Speak(FALLBACK))

        return ChatReply(result.tool_calls, result.reasoning, result.confidence)
