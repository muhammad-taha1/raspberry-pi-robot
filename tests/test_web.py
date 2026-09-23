import json

import pytest

from robotd.messages import Turn
from robotd.web import parse_text, state_body


def test_parses_valid_text():
    assert parse_text(json.dumps({"text": "Good evening."}).encode()) == "Good evening."


@pytest.mark.parametrize("body", [b"not json", b"{}", json.dumps({"text": "   "}).encode()])
def test_rejects_bad_text_bodies(body):
    with pytest.raises((ValueError, KeyError)):
        parse_text(body)


def test_state_body_empty():
    assert state_body([]) == {"ok": True, "turns": []}


def test_state_body_lists_turns():
    turns = [Turn(heard="turn on the light", spoken="Done.")]
    assert state_body(turns) == {
        "ok": True,
        "turns": [{"heard": "turn on the light", "spoken": "Done."}],
    }
