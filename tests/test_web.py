import json

import pytest

from robotd.messages import Command, CommandResult
from robotd.web import parse_command, parse_say, status_for


def test_parses_valid_command():
    body = json.dumps({"device": "led", "action": "on"}).encode()
    assert parse_command(body) == Command("led", "on")


@pytest.mark.parametrize(
    "body",
    [
        b"not json",
        b"{}",
        json.dumps({"device": "led"}).encode(),
        json.dumps({"device": 1, "action": "on"}).encode(),
        json.dumps({"device": "led", "action": 1}).encode(),
    ],
)
def test_rejects_bad_bodies(body):
    with pytest.raises((json.JSONDecodeError, KeyError, ValueError)):
        parse_command(body)


def test_status_for_ok_result_is_200():
    assert status_for(CommandResult(True, "on")) == 200


def test_status_for_failed_result_is_400():
    assert status_for(CommandResult(False, "unknown device 'nope'")) == 400


def test_parses_valid_say():
    body = json.dumps({"text": "Good evening."}).encode()
    assert parse_say(body) == "Good evening."


@pytest.mark.parametrize(
    "body",
    [
        b"not json",
        b"{}",
        json.dumps({"text": 1}).encode(),
        json.dumps({"text": ""}).encode(),
        json.dumps({"text": "   "}).encode(),
    ],
)
def test_rejects_bad_say_bodies(body):
    with pytest.raises((json.JSONDecodeError, KeyError, ValueError)):
        parse_say(body)
