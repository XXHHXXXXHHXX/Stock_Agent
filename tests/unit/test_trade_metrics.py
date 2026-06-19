"""Unit tests for trade_metrics helpers."""
from __future__ import annotations

from pa_agent.util.trade_metrics import (
    compute_risk_reward,
    format_estimated_win_rate,
    format_estimated_win_rate_reasoning,
    is_long_direction,
    max_risk_reward_ratio,
    min_risk_reward_ratio,
)


def test_is_long_direction():
    assert is_long_direction("做多") is True
    assert is_long_direction("做空") is False


def test_compute_risk_reward_short():
    rr = compute_risk_reward(4541, 4510, 4553, "做空")
    assert rr is not None
    assert rr["risk"] == 12
    assert rr["reward"] == 31


def test_rr_bounds_all_stances_share_one_floor() -> None:
    for stance in ("conservative", "balanced", "aggressive", "extreme_aggressive", None):
        assert min_risk_reward_ratio(stance) == 1.0
    assert max_risk_reward_ratio() == 1.5


def test_format_estimated_win_rate_from_model_field():
    decision = {
        "estimated_win_rate": 47,
        "estimated_win_rate_reasoning": "宽通道顺势，方程用 47%",
    }
    assert format_estimated_win_rate(decision) == "47%"
    assert "47" in format_estimated_win_rate_reasoning(decision)
