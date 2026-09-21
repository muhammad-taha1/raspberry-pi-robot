import time

from robotd.actors.brain import FALLBACK, BrainActor
from robotd.actors.status import StatusActor
from robotd.actors.voice import VoiceActor
from robotd.messages import Transcript
from robotd.models.llm import Completion, ToolCall
from robotd.tools import build_registry

from doubles import RecordingLed, RecordingSpeaker, RecordingTts, ScriptedLlm


def start(completions):
    led = RecordingLed()
    tts = RecordingTts()
    speaker = RecordingSpeaker()
    status = StatusActor.start(led=led)
    voice = VoiceActor.start(tts=tts, speaker=speaker)
    registry = build_registry(voice=voice, status=status)
    llm = ScriptedLlm(completions)
    brain = BrainActor.start(llm=llm, registry=registry, voice=voice)
    return brain, status, voice, led, tts


def stop(brain, status, voice):
    brain.stop()
    voice.stop()
    status.stop()


def test_say_call_speaks_it():
    completions = [Completion([ToolCall("say", {"text": "hi there"})], "reasoning", 0.9)]
    brain, status, voice, led, tts = start(completions)
    try:
        reply = brain.ask(Transcript("say hi"))
        time.sleep(0.05)
    finally:
        stop(brain, status, voice)

    assert tts.texts == ["hi there"]
    assert reply.confidence == 0.9


def test_set_led_call_lights_the_led():
    completions = [Completion([ToolCall("set_led", {"on": True})], "reasoning", 0.9)]
    brain, status, voice, led, tts = start(completions)
    try:
        brain.ask(Transcript("turn on the light"))
        time.sleep(0.05)
    finally:
        stop(brain, status, voice)

    assert led.calls[0] == "on"


def test_two_calls_in_one_completion_both_fire_in_order():
    completions = [
        Completion(
            [ToolCall("set_led", {"on": True}), ToolCall("say", {"text": "done"})],
            "reasoning",
            0.8,
        )
    ]
    brain, status, voice, led, tts = start(completions)
    try:
        brain.ask(Transcript("light on and say done"))
        time.sleep(0.05)
    finally:
        stop(brain, status, voice)

    assert led.calls[0] == "on"
    assert tts.texts == ["done"]


def test_empty_calls_speaks_fallback_and_touches_no_device():
    completions = [Completion([], "off topic", 0.05)]
    brain, status, voice, led, tts = start(completions)
    try:
        brain.ask(Transcript("what is the capital of Peru"))
        time.sleep(0.05)
    finally:
        stop(brain, status, voice)

    assert tts.texts == [FALLBACK]
    assert led.calls == ["off", "close"]  # only StatusActor's own shutdown touched it


def test_reply_carries_confidence_through():
    completions = [Completion([], "off topic", None)]
    brain, status, voice, led, tts = start(completions)
    try:
        reply = brain.ask(Transcript("hmm"))
    finally:
        stop(brain, status, voice)

    assert reply.confidence is None
    assert reply.reasoning == "off topic"
