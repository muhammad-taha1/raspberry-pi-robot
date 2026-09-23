"""The call gates only — NeedleLlm needs a deferred cactus-needle import."""

from robotd.models.llm import CONFIDENCE_FLOOR, ToolCall, apply_floor, hold_untriggered

CALL = ToolCall("set_led", {"on": True})
OTHER = ToolCall("look", {})


def test_holds_call_whose_triggers_did_not_match():
    # "how are you?" -> set_led at confidence 1.0, seen live on the Pi.
    calls, suppressed = hold_untriggered([CALL, OTHER], [], untriggered={"set_led"})
    assert calls == [OTHER]
    assert suppressed == [CALL]


def test_passes_call_whose_triggers_matched():
    calls, suppressed = hold_untriggered([CALL], [], untriggered=set())
    assert calls == [CALL]
    assert suppressed == []


def test_holds_low_confidence_call():
    calls, suppressed = apply_floor([CALL], [], CONFIDENCE_FLOOR - 0.1, set())
    assert calls == []
    assert suppressed == [CALL]


def test_passes_high_confidence_call():
    calls, suppressed = apply_floor([CALL], [], CONFIDENCE_FLOOR + 0.1, set())
    assert calls == [CALL]
    assert suppressed == []


def test_exempts_triggered_tool_below_floor():
    calls, suppressed = apply_floor([CALL], [], CONFIDENCE_FLOOR - 0.1, {"set_led"})
    assert calls == [CALL]
    assert suppressed == []


def test_never_gates_none_confidence():
    calls, suppressed = apply_floor([CALL], [], None, set())
    assert calls == [CALL]
    assert suppressed == []
