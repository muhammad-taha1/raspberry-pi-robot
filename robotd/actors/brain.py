"""BrainActor — turns a Transcript into tool calls plus a spoken reply. Holds
no device references (the registry has those) and no conversation history
(NeedleLlm and the chat model each own their own).

Needle 3 never generates prose, so a Transcript that produces no tool call
(a joke, a greeting, small talk) is not a failure — it is the normal signal
to hand the utterance to the chat model instead. Generation only happens on
that path: a dispatched tool call gets a generic static acknowledgement, so
device commands never wait on inference.
"""

from __future__ import annotations

import logging

import pykka

from robotd import phrases
from robotd.messages import ChatReply, Speak, Transcript
from robotd.models.chat import ChatProvider
from robotd.models.llm import LlmProvider
from robotd.tools import ToolRegistry

logger = logging.getLogger(__name__)


class BrainActor(pykka.ThreadingActor):
    def __init__(
        self, llm: LlmProvider, registry: ToolRegistry, voice: pykka.ActorRef, chat: ChatProvider
    ) -> None:
        super().__init__()
        self._llm = llm
        self._registry = registry
        self._voice = voice
        self._chat = chat

    def on_receive(self, message: object) -> ChatReply | None:
        if not isinstance(message, Transcript):
            return None

        result = self._llm.complete(message.text)
        logger.info(
            "ok=%s confidence=%s reasoning=%s suppressed=%s ungrounded=%s",
            result.ok,
            result.confidence,
            result.reasoning,
            result.suppressed_calls,
            result.ungrounded,
        )

        if not result.ok:
            # Needle itself failed — not a cue to treat the utterance as small talk.
            spoken = phrases.pick(phrases.FAILED)
        elif result.tool_calls:
            all_dispatched = all([self._registry.dispatch(c) for c in result.tool_calls])
            spoken = phrases.pick(phrases.ACK if all_dispatched else phrases.FAILED)
        else:
            try:
                spoken = self._chat.reply(message.text).strip()
            except Exception:
                logger.exception("chat failed")
                spoken = ""
            if not spoken:
                spoken = phrases.pick(phrases.UNSURE)

        self._voice.tell(Speak(spoken))
        return ChatReply(
            text=spoken,
            tool_calls=result.tool_calls,
            reasoning=result.reasoning,
            confidence=result.confidence,
            error=result.error,
            suppressed_calls=result.suppressed_calls,
            ungrounded=result.ungrounded,
        )
