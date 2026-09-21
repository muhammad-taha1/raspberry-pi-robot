import json

import pytest

from robotd.web import parse_text


def test_parses_valid_text():
    assert parse_text(json.dumps({"text": "Good evening."}).encode()) == "Good evening."


@pytest.mark.parametrize("body", [b"not json", b"{}", json.dumps({"text": "   "}).encode()])
def test_rejects_bad_text_bodies(body):
    with pytest.raises((ValueError, KeyError)):
        parse_text(body)
