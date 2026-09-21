"""apply_floor only — NeedleLlm needs a deferred cactus-needle import."""

from robotd.models.llm import CONFIDENCE_FLOOR, ToolCall, apply_floor

CALL = ToolCall("set_led", {"on": True})


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
