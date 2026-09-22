from robotd.actors.voice import VoiceActor
from robotd.messages import Speak

from doubles import RaisingSpeaker, RecordingSpeaker, RecordingTts, wait_until


def test_speak_messages_synthesize_and_play_in_mailbox_order():
    tts = RecordingTts()
    speaker = RecordingSpeaker()
    actor = VoiceActor.start(tts=tts, speaker=speaker)
    try:
        actor.tell(Speak("First."))
        actor.tell(Speak("Second."))
        wait_until(lambda: len(speaker.utterances) == 2)
    finally:
        actor.stop()

    assert tts.texts == ["First.", "Second."]
    assert speaker.utterances == [b"First.", b"Second."]
    assert speaker.closed


def test_playback_failure_does_not_kill_the_actor():
    tts = RecordingTts()
    speaker = RaisingSpeaker()
    actor = VoiceActor.start(tts=tts, speaker=speaker)
    try:
        actor.tell(Speak("First."))
        actor.tell(Speak("Second."))
        wait_until(lambda: len(speaker.utterances) == 2)
        assert actor.is_alive()
    finally:
        actor.stop()  # must not raise even though close() also faults
