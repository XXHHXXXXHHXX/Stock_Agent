"""Tests for validation retry policy and feedback."""
from __future__ import annotations

from dataclasses import dataclass

from pa_agent.ai.retry_feedback import build_retry_feedback
from pa_agent.ai.retry_policy import detect_cheat, should_retry
from pa_agent.ai.stage2_normalizer import ensure_stage2_predictions
from pa_agent.gui.stage2_payload import prepare_stage2_for_ui


@dataclass
class _FakeErr:
    category: str
    message: str
    missing_fields: list[str]
    invalid_fields: list[str]
    parse_position: str | None = None
    raw_text: str = ""


class _Settings:
    retry_enabled = True
    retry_max = 2
    retry_max_semantic = 1
    retry_stage2 = True


def test_should_retry_format_errors():
    assert should_retry("b", [], ["gate_trace"], attempt=0, settings=_Settings())
    assert not should_retry("c", ["metrics:bad"], [], attempt=0, settings=_Settings())


def test_detect_cheat_immutable_direction():
    before = {"direction": "bullish", "cycle_position": "spike", "gate_result": "proceed"}
    after = {"direction": "bearish", "cycle_position": "spike", "gate_result": "proceed"}
    flags = detect_cheat("stage1", before, after)
    assert any("direction" in f for f in flags)


def test_detect_cheat_no_false_positive_when_program_normalizes_direction():
    """Raw AI direction may differ from post-normalize value; compare normalized copies."""
    from pa_agent.ai.json_validator import JsonValidator
    from pa_agent.data.base import IndicatorBundle, KlineBar, KlineFrame

    bars = tuple(
        KlineBar(
            seq=i + 1,
            ts_open=float(1_000_000 - (i + 1) * 60_000),
            open=2000.0,
            high=2010.0,
            low=1990.0,
            close=2005.0,
            volume=1.0,
            closed=True,
        )
        for i in range(25)
    )
    frame = KlineFrame(
        symbol="TEST",
        timeframe="1h",
        bars=bars,
        snapshot_ts_local_ms=1,
        indicators=IndicatorBundle(
            ema20=tuple([2000.0] * 25),
            atr14=tuple([10.0] * 25),
        ),
    )
    validator = JsonValidator()
    raw = {
        "direction": "bearish",
        "cycle_position": "broad_channel",
        "gate_result": "proceed",
        "gate_trace": [],
    }
    before_norm = validator.normalize_parsed("stage1", raw, kline_frame=frame)
    after_norm = validator.normalize_parsed("stage1", dict(raw), kline_frame=frame)
    flags = detect_cheat("stage1", before_norm, after_norm)
    assert not flags


def test_build_retry_feedback_contains_stage():
    err = _FakeErr("b", "missing", ["next_bar_prediction"], [], None, "{}")
    text = build_retry_feedback(err, stage="stage2", attempt=1, max_attempts=2)
    assert "next_bar_prediction" in text
    assert "阶段二" in text


def test_ensure_stage2_predictions_for_old_record():
    s2 = {
        "decision": {"order_type": "不下单", "reasoning": "等待"},
        "diagnosis_summary": {"cycle_position": "broad_channel", "direction": "neutral"},
        "decision_trace": [],
        "terminal": {"node_id": "9.0", "outcome": "wait", "label": "x"},
    }
    assert ensure_stage2_predictions(s2) is True
    assert isinstance(s2.get("next_bar_prediction"), dict)
    assert isinstance(s2.get("next_cycle_prediction"), dict)


def test_prepare_stage2_for_ui_merges_predictions():
    s2 = {
        "decision": {"order_type": "不下单"},
        "diagnosis_summary": {"cycle_position": "broad_channel", "direction": "neutral"},
    }
    payload = prepare_stage2_for_ui(s2)
    assert "next_bar_prediction" in payload
    assert "next_cycle_prediction" in payload
