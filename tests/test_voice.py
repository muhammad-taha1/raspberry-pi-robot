import time

from robotd.actors.voice import VoiceActor
from robotd.actors.voice import command as say_command
from robotd.messages import Speak

from doubles import RecordingSpeaker, RecordingTts


def test_command_translates_action_to_speak():
    assert say_command("Hello there") == Speak("Hello there")


def test_speak_messages_synthesize_and_play_in_mailbox_order():
    tts = RecordingTts()
    speaker = RecordingSpeaker()
    actor = VoiceActor.start(tts=tts, speaker=speaker)
    try:
        actor.tell(Speak("First."))
        actor.tell(Speak("Second."))
        time.sleep(0.05)
    finally:
        actor.stop()

    assert tts.texts == ["First.", "Second."]
    assert speaker.utterances == [b"First.", b"Second."]
    assert speaker.closed
