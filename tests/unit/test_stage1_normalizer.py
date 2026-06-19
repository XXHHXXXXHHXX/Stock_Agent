"""Tests for Stage 1 JSON normalization."""
from __future__ import annotations

from tests.fixtures.validators import schema_test_validator
from pa_agent.ai.coherence_checks import validate_stage1_coherence
from pa_agent.ai.stage1_normalizer import normalize_stage1
from pa_agent.data.base import IndicatorBundle, KlineBar, KlineFrame
from tests.integration.conftest import VALID_STAGE1


def test_hoists_bar_by_bar_summary_from_bar_analysis() -> None:
    """Regression: model nests bar_by_bar_summary inside bar_analysis."""
    nested = [
        {
            "bar": "K1",
            "role": "noise",
            "bar_type": "outside_bull",
            "context_effect": "weakens_bear",
            "follow_through": "pending",
            "trapped_side": "none",
            "reason": "外包阳线",
        }
    ]
    raw = {**VALID_STAGE1}
    del raw["bar_by_bar_summary"]
    raw["bar_analysis"] = {**raw.get("bar_analysis", {}), "bar_by_bar_summary": nested}
    out = normalize_stage1(raw)
    assert out["bar_by_bar_summary"] == nested
    assert "bar_by_bar_summary" not in (out.get("bar_analysis") or {})


def test_maps_recommended_strategy_files() -> None:
    raw = {**VALID_STAGE1}
    del raw["strategy_files_needed"]
    raw["recommended_strategy_files"] = ["下跌通道分析识别.txt"]
    out = normalize_stage1(raw)
    assert out["strategy_files_needed"] == ["下跌通道分析识别.txt"]


def test_repair_gate_23_neutral_answer_with_bearish_branch() -> None:
    """Regression: answer=中性 but branch/direction bearish (model conflates enums)."""
    raw = {**VALID_STAGE1, "direction": "bearish"}
    raw["gate_trace"] = [
        {
            "node_id": "2.3",
            "question": "当前方向是多头还是空头？",
            "answer": "中性",
            "branch": "bearish",
            "reason": "波段高低点下移，判定为空头。",
            "bar_range": "K10-K1",
        }
    ]
    out = normalize_stage1(raw, normalization_mode="strict")
    assert out["gate_trace"][0]["answer"] == "是"
    assert out["gate_trace"][0]["branch"] == "bearish"
    errs = validate_stage1_coherence(out)
    assert not any("2.3 answer=中性" in e for e in errs)


def test_normalizes_gate_2_3_directional_answer() -> None:
    raw = {**VALID_STAGE1}
    raw["gate_trace"] = [
        {
            "node_id": "2.3",
            "question": "当前方向是多头还是空头？",
            "answer": "空头",
            "reason": "EMA下倾",
            "bar_range": "K20-K1",
        }
    ]
    out = normalize_stage1(raw, normalization_mode="lenient")
    assert out["gate_trace"][0]["answer"] == "是"
    assert out["gate_trace"][0]["branch"] == "bearish"


def test_normalizes_context_effect_typos_and_gate_12_branch() -> None:
    """Regression: strengthen_bull / gate 1.2 branch=yes vs broad_channel."""
    raw = {
        "cycle_position": "broad_channel",
        "direction": "bullish",
        "diagnosis_confidence": 68,
        "market_phase": "transitioning",
        "detected_patterns": [],
        "key_signals": ["sig"],
        "htf_context": "htf",
        "entry_setup": "等待",
        "strategy_files_needed": ["宽通道交易策略.txt"],
        "risk_warning": "warn",
        "bar_by_bar_summary": [
            {
                "bar": "K8",
                "role": "signal",
                "bar_type": "outside_bear",
                "context_effect": "strengthen_bear",
                "follow_through": "yes",
                "trapped_side": "bulls",
                "reason": "r",
            },
            {
                "bar": "K6",
                "role": "trap",
                "bar_type": "inside",
                "context_effect": "strengthen_bull",
                "follow_through": "no",
                "trapped_side": "bulls",
                "reason": "r",
            },
        ],
        "gate_trace": [
            {
                "node_id": "1.2",
                "question": "是否能识别市场周期？",
                "answer": "是",
                "branch": "yes",
                "reason": "宽通道",
                "bar_range": "K19-K1",
            }
        ],
        "gate_result": "proceed",
    }
    out = normalize_stage1(raw, normalization_mode="lenient")
    assert out["bar_by_bar_summary"][0]["context_effect"] == "strengthens_bear"
    assert out["bar_by_bar_summary"][1]["context_effect"] == "strengthens_bull"
    assert out["gate_trace"][0]["branch"] == "broad_channel"


def test_validator_accepts_normalized_user_payload() -> None:
    """Regression: payload like user's failing response after normalize."""
    import json

    payload = {
        "cycle_position": "micro_channel",
        "direction": "bearish",
        "diagnosis_confidence": 82,
        "spike_stage": None,
        "market_phase": "transitioning",
        "transition_risk": "medium",
        "detected_patterns": [],
        "key_signals": ["sig"],
        "htf_context": "htf",
        "entry_setup": "等待",
        "recommended_strategy_files": ["下跌通道策略"],
        "risk_warning": "warn",
        "gate_trace": [
            {
                "node_id": "2.3",
                "question": "当前方向是多头还是空头？",
                "answer": "空头",
                "reason": "bear",
                "bar_range": "K20-K1",
            }
        ],
        "gate_result": "proceed",
    }
    normalized = normalize_stage1(payload, normalization_mode="lenient")
    gate_trace = [dict(x) for x in VALID_STAGE1["gate_trace"]]
    for item in gate_trace:
        if item.get("node_id") == "1.2":
            item["branch"] = "micro_channel"
        if item.get("node_id") == "2.3":
            item["branch"] = "bearish"
    normalized["gate_trace"] = gate_trace
    normalized["bar_by_bar_summary"] = VALID_STAGE1["bar_by_bar_summary"]
    normalized["strategy_files_needed"] = ["下跌通道分析识别.txt"]
    result = schema_test_validator().validate("stage1", json.dumps(normalized, ensure_ascii=False))
    from pa_agent.ai.json_validator import Ok

    assert isinstance(result, Ok)


def test_normalize_signal_bar_null_infers_from_summary() -> None:
    """Regression: signal_bar=null fails schema; infer from bar_by_bar_summary role=signal."""
    import json

    from pa_agent.ai.json_validator import Ok

    raw = {**VALID_STAGE1, "direction": "bearish"}
    raw["bar_analysis"] = {
        "always_in": "short",
        "last_closed_bar": "K1",
        "bar_type": "doji",
        "signal_bar": None,
        "entry_setup_type": "none",
        "follow_through": "failed",
    }
    raw["bar_by_bar_summary"] = [
        {
            "bar": "K7",
            "role": "signal",
            "bar_type": "trend_bear",
            "context_effect": "strengthens_bear",
            "follow_through": "yes",
            "trapped_side": "none",
            "reason": "空头最强信号棒",
        },
        {
            "bar": "K1",
            "role": "trap",
            "bar_type": "doji",
            "context_effect": "strengthens_bear",
            "follow_through": "pending",
            "trapped_side": "bulls",
            "reason": "高开长上影测试失败",
        },
    ]
    out = normalize_stage1(raw)
    sb = out["bar_analysis"]["signal_bar"]
    assert isinstance(sb, dict)
    assert sb["bar"] == "K7"
    assert sb["quality"] == "strong"

    result = schema_test_validator().validate("stage1", json.dumps(out, ensure_ascii=False))
    assert isinstance(result, Ok)


def test_normalize_bar_type_ine_truncation_passes_schema() -> None:
    """Regression: models truncate inside→ine in bar_analysis.bar_type."""
    import json

    from pa_agent.ai.json_validator import Ok

    raw = {**VALID_STAGE1}
    raw["bar_analysis"] = {
        "always_in": "long",
        "last_closed_bar": "K1",
        "bar_type": "ine",
        "signal_bar": {"bar": "K1", "quality": "weak", "reason": "inside回调"},
        "entry_setup_type": "none",
        "follow_through": "pending",
    }
    raw["bar_by_bar_summary"] = [
        {
            "bar": "K1",
            "role": "test",
            "bar_type": "inside",
            "context_effect": "weakens_bull",
            "follow_through": "pending",
            "trapped_side": "bulls",
            "reason": "内包阴线",
        },
    ]
    out = normalize_stage1(raw)
    assert out["bar_analysis"]["bar_type"] == "inside"

    result = schema_test_validator().validate("stage1", json.dumps(out, ensure_ascii=False))
    assert isinstance(result, Ok)


def test_pad_bar_by_bar_summary_when_model_only_sends_five_bars() -> None:
    n = 100
    frame = KlineFrame(
        symbol="XAUUSD",
        timeframe="15m",
        bars=tuple(
            KlineBar(
                seq=i + 1,
                ts_open=float(1000 - i),
                open=4550.0,
                high=4560.0,
                low=4540.0,
                close=4555.0,
                volume=1.0,
                closed=True,
            )
            for i in range(n)
        ),
        snapshot_ts_local_ms=1,
        indicators=IndicatorBundle(
            ema20=tuple([4550.0] * n),
            atr14=tuple([5.0] * n),
        ),
    )
    summary = [
        {"bar": f"K{i}", "role": "structure", "bar_type": "doji", "context_effect": "neutral",
         "follow_through": "no", "trapped_side": "none", "reason": f"棒K{i}"}
        for i in (5, 4, 3, 2, 1)
    ]
    out = normalize_stage1({"bar_by_bar_summary": summary}, kline_frame=frame)
    assert len(out["bar_by_bar_summary"]) == 8
    bars = [item["bar"] for item in out["bar_by_bar_summary"]]
    assert bars == [f"K{i}" for i in range(8, 0, -1)]
    errs = validate_stage1_coherence(
        {**VALID_STAGE1, "bar_by_bar_summary": out["bar_by_bar_summary"]},
        kline_frame=frame,
    )
    assert not any("bar_by_bar_summary has" in e and "expected at least" in e for e in errs)


def test_fill_incremental_delta_from_risk_warning() -> None:
    prev = {
        "cycle_position": "trading_range",
        "direction": "neutral",
        "diagnosis_confidence": 70,
        "gate_result": "proceed",
    }
    out = normalize_stage1(
        {
            "cycle_position": "trending_tr",
            "direction": "bullish",
            "diagnosis_confidence": 60,
            "gate_result": "proceed",
            "risk_warning": "相对上一轮：新增K1突破，方向由中性转偏多。",
            "gate_trace": [{"node_id": "0.1", "answer": "是", "reason": "x", "bar_range": "K1"}],
            "bar_by_bar_summary": [{"bar": "K1", "role": "structure", "bar_type": "doji",
                "context_effect": "neutral", "follow_through": "no", "trapped_side": "none", "reason": "x"}],
        },
        incremental_new_bar_count=1,
        incremental_previous_stage1=prev,
    )
    delta = out["incremental_delta"]
    assert delta["new_closed_bars"] == ["K1"]
    assert len(delta["summary"]) >= 16
    assert "direction" in delta["changed_fields"]
    assert "cycle_position" in delta["changed_fields"]
