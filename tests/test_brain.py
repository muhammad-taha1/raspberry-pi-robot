from robotd import phrases
from robotd.actors.brain import BrainActor
from robotd.actors.light import LightActor
from robotd.actors.voice import VoiceActor
from robotd.messages import Transcript
from robotd.models.llm import Completion, ToolCall
from robotd.tools import build_registry

from doubles import (
    RaisingChat,
    RecordingLed,
    RecordingSpeaker,
    RecordingTts,
    ScriptedChat,
    ScriptedLlm,
    wait_until,
)


def start(completions, chat=None):
    led = RecordingLed()
    tts = RecordingTts()
    light = LightActor.start(led=led)
    voice = VoiceActor.start(tts=tts, speaker=RecordingSpeaker())
    chat = chat if chat is not None else ScriptedChat([])
    brain = BrainActor.start(
        llm=ScriptedLlm(completions),
        registry=build_registry(light=light),
        voice=voice,
        chat=chat,
    )
    return brain, light, voice, led, tts, chat


def stop(brain, light, voice):
    brain.stop()
    voice.stop()
    light.stop()


def test_tool_call_lights_the_led_and_speaks_an_ack():
    completions = [Completion([ToolCall("set_led", {"turn_on": True})], "reasoning", 0.9)]
    brain, light, voice, led, tts, chat = start(completions)
    try:
        reply = brain.ask(Transcript("turn on the light"))
        wait_until(lambda: led.calls and tts.texts)
    finally:
        stop(brain, light, voice)

    assert led.calls[0] == "on"
    assert reply.text in phrases.ACK
    assert tts.texts == [reply.text]
    assert chat.texts == []  # tool path never consults chat


def test_two_calls_in_one_completion_both_fire_and_speak_one_ack():
    completions = [
        Completion(
            [ToolCall("set_led", {"turn_on": True}), ToolCall("set_led", {"turn_on": False})],
            "reasoning",
            0.8,
        )
    ]
    brain, light, voice, led, tts, chat = start(completions)
    try:
        reply = brain.ask(Transcript("light on then off"))
        wait_until(lambda: len(led.calls) >= 2 and tts.texts)
    finally:
        stop(brain, light, voice)

    assert led.calls[:2] == ["on", "off"]
    assert reply.text in phrases.ACK
    assert tts.texts == [reply.text]


def test_dispatch_failure_speaks_failed_and_does_not_consult_chat():
    completions = [Completion([ToolCall("sparkle", {})], "reasoning", 0.9)]
    brain, light, voice, led, tts, chat = start(completions)
    try:
        reply = brain.ask(Transcript("sparkle please"))
    finally:
        stop(brain, light, voice)

    assert reply.text in phrases.FAILED
    assert chat.texts == []


def test_empty_calls_asks_chat_and_speaks_its_reply():
    completions = [Completion([], "off topic", 0.05)]
    chat = ScriptedChat(["Here's a joke."])
    brain, light, voice, led, tts, chat = start(completions, chat=chat)
    try:
        reply = brain.ask(Transcript("tell me a joke"))
        wait_until(lambda: tts.texts)
    finally:
        stop(brain, light, voice)

    assert chat.texts == ["tell me a joke"]
    assert reply.text == "Here's a joke."
    assert tts.texts == ["Here's a joke."]
    assert led.calls == ["off", "close"]  # only LightActor's own shutdown touched it


def test_raising_chat_speaks_unsure_and_brain_stays_alive():
    completions = [Completion([], "off topic", 0.05)]
    brain, light, voice, led, tts, chat = start(completions, chat=RaisingChat())
    try:
        reply = brain.ask(Transcript("tell me a joke"))
        wait_until(lambda: tts.texts)
    finally:
        stop(brain, light, voice)

    assert reply.text in phrases.UNSURE
    assert tts.texts == [reply.text]


def test_blank_chat_reply_speaks_unsure():
    completions = [Completion([], "off topic", 0.05)]
    brain, light, voice, led, tts, chat = start(completions, chat=ScriptedChat(["   "]))
    try:
        reply = brain.ask(Transcript("hmm"))
    finally:
        stop(brain, light, voice)

    assert reply.text in phrases.UNSURE


def test_dead_voice_actor_does_not_break_the_reply():
    completions = [Completion([], "off topic", 0.05)]
    chat = ScriptedChat(["Here's a joke."])
    brain, light, voice, led, tts, chat = start(completions, chat=chat)
    voice.stop()
    try:
        reply = brain.ask(Transcript("tell me a joke"))
    finally:
        brain.stop()
        light.stop()

    assert reply.text == "Here's a joke."


def test_needle_failure_speaks_failed_and_chat_is_never_consulted():
    completions = [Completion([], "", None, ok=False, error="model crashed")]
    brain, light, voice, led, tts, chat = start(completions)
    try:
        reply = brain.ask(Transcript("anything"))
    finally:
        stop(brain, light, voice)

    assert reply.text in phrases.FAILED
    assert chat.texts == []
    assert led.calls == ["off", "close"]
