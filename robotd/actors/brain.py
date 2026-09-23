"""BrainActor — Transcript in, tool calls plus a spoken reply out.

Needle never generates prose, so a Transcript producing no tool call is not a
failure — it's the signal to hand the utterance to the chat model instead.
"""

from __future__ import annotations

import logging
from collections import deque

import pykka

from robotd import phrases
from robotd.messages import ChatReply, GetState, Speak, Transcript, Turn
from robotd.models.chat import ChatProvider
from robotd.models.llm import LlmProvider
from robotd.tools import ToolRegistry

logger = logging.getLogger(__name__)

# GET /state's whole backing store — BrainActor already sees every Transcript
# (from /chat and HearingActor both) and produces every spoken line, so this is
# state it already holds, not new state invented for an endpoint. A dedicated
# telemetry actor is deferred to M9 — see docs/open-questions.md.
STATE_TURNS = 10


class BrainActor(pykka.ThreadingActor):
    def __init__(
        self, llm: LlmProvider, registry: ToolRegistry, voice: pykka.ActorRef, chat: ChatProvider
    ) -> None:
        super().__init__()
        self._llm = llm
        self._registry = registry
        self._voice = voice
        self._chat = chat
        self._turns: deque[Turn] = deque(maxlen=STATE_TURNS)

    def on_receive(self, message: object) -> ChatReply | list[Turn] | None:
        if isinstance(message, GetState):
            return list(self._turns)

        if not isinstance(message, Transcript):
            return None

        result = self._llm.complete(message.text)
        logger.info(
            "heard=%r calls=%s ok=%s confidence=%s reasoning=%s suppressed=%s ungrounded=%s",
            message.text,
            result.tool_calls,
            result.ok,
            result.confidence,
            result.reasoning,
            result.suppressed_calls,
            result.ungrounded,
        )

        if not result.ok:
            spoken = phrases.pick(phrases.FAILED)
        elif result.tool_calls:
            # List, not a generator: all() must not short-circuit past a call.
            all_dispatched = all([self._registry.dispatch(c) for c in result.tool_calls])
            spoken = phrases.pick(phrases.ACK if all_dispatched else phrases.FAILED)
        else:
            try:
                spoken = self._chat.reply(message.text).strip() or phrases.pick(phrases.UNSURE)
            except Exception:
                logger.exception("chat failed")
                spoken = phrases.pick(phrases.UNSURE)

        try:
            self._voice.tell(Speak(spoken))
        except pykka.ActorDeadError:
            logger.error("voice actor is dead, replying without speech")

        self._turns.append(Turn(heard=message.text, spoken=spoken))

        return ChatReply(
            text=spoken,
            tool_calls=result.tool_calls,
            reasoning=result.reasoning,
            confidence=result.confidence,
            error=result.error,
            suppressed_calls=result.suppressed_calls,
            ungrounded=result.ungrounded,
        )
