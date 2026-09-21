import json

import pytest

from robotd.messages import Command
from robotd.web import parse_command, parse_text


def test_parses_valid_command():
    body = json.dumps({"device": "led", "action": "on"}).encode()
    assert parse_command(body) == Command("led", "on")


@pytest.mark.parametrize("body", [b"not json", b"{}", json.dumps({"device": "led"}).encode()])
def test_rejects_bad_command_bodies(body):
    with pytest.raises((ValueError, KeyError)):
        parse_command(body)


def test_parses_valid_text():
    assert parse_text(json.dumps({"text": "Good evening."}).encode()) == "Good evening."


@pytest.mark.parametrize("body", [b"not json", b"{}", json.dumps({"text": "   "}).encode()])
def test_rejects_bad_text_bodies(body):
    with pytest.raises((ValueError, KeyError)):
        parse_text(body)
