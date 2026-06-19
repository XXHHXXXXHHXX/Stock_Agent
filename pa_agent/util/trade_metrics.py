"""Risk/reward and estimated win-rate helpers for trading decisions."""
from __future__ import annotations

from typing import Any


def is_long_direction(direction: object) -> bool | None:
    """Return True for long, False for short, None if unknown."""
    text = str(direction or "").strip().lower()
    if not text:
        return None
    if "多" in text or text in ("long", "buy", "bull"):
        return True
    if "空" in text or text in ("short", "sell", "bear"):
        return False
    return None


def compute_risk_reward(
    entry: object,
    take_profit: object,
    stop_loss: object,
    direction: object,
) -> dict[str, float | str] | None:
    """Compute risk/reward distances and reward:risk ratio (盈亏比).

    Returns None when prices are invalid or risk is zero.
    """
    try:
        e = float(entry)
        tp = float(take_profit)
        sl = float(stop_loss)
    except (TypeError, ValueError):
        return None

    long = is_long_direction(direction)
    if long is True:
        risk = e - sl
        reward = tp - e
    elif long is False:
        risk = sl - e
        reward = e - tp
    else:
        if tp > e and sl < e:
            risk = e - sl
            reward = tp - e
        elif tp < e and sl > e:
            risk = sl - e
            reward = e - tp
        else:
            return None

    if risk <= 0 or reward <= 0:
        return None

    ratio = reward / risk
    return {
        "risk": risk,
        "reward": reward,
        "ratio": ratio,
        "ratio_text": f"{ratio:.2f} : 1",
    }


def format_estimated_win_rate(decision: dict[str, Any]) -> str | None:
    """Format model-provided estimated_win_rate (0–100) for display."""
    value = decision.get("estimated_win_rate")
    if value is None or value == "":
        return None
    try:
        pct = max(0, min(100, int(float(str(value).strip()))))
    except (ValueError, TypeError):
        return None
    return f"{pct}%"


def format_estimated_win_rate_reasoning(decision: dict[str, Any]) -> str:
    return str(decision.get("estimated_win_rate_reasoning", "") or "").strip()


# Lower cap: reward must be at least equal to risk (1:1) for any stance.
MIN_RISK_REWARD_RATIO = 1.0

# Upper cap: targets far beyond 1.5R usually imply unrealistically low win rates.
MAX_RISK_REWARD_RATIO = 1.5


def min_risk_reward_ratio(decision_stance: str | None = None) -> float:
    """Minimum reward:risk ratio required to place an order (same for all stances)."""
    _ = decision_stance  # kept for call-site compatibility
    return MIN_RISK_REWARD_RATIO


def max_risk_reward_ratio() -> float:
    """Maximum reward:risk ratio allowed for any order (win-rate realism cap)."""
    return MAX_RISK_REWARD_RATIO


def passes_trader_equation(
    win_rate_pct: float,
    risk: float,
    reward: float,
) -> bool:
    """Brooks equation: win_rate × reward > (1 - win_rate) × risk."""
    if risk <= 0 or reward <= 0:
        return False
    p = max(0.0, min(100.0, float(win_rate_pct))) / 100.0
    return p * reward > (1.0 - p) * risk


def _parse_win_rate(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return max(0.0, min(100.0, float(str(value).strip())))
    except (TypeError, ValueError):
        return None


def _latest_closed_bar(kline_frame: Any) -> Any | None:
    """Return K1 (newest closed bar) from a snapshot frame."""
    bars = getattr(kline_frame, "bars", None) if kline_frame is not None else None
    if not bars:
        return None
    for bar in bars:
        if int(getattr(bar, "seq", 0) or 0) == 1 and bool(getattr(bar, "closed", True)):
            return bar
    for bar in bars:
        if bool(getattr(bar, "closed", True)):
            return bar
    return None


def validate_limit_order_k1_freshness(
    decision: dict[str, Any],
    kline_frame: Any,
) -> list[str]:
    """Reject stale limit orders that K1 has already traded through."""
    if decision.get("order_type") != "限价单":
        return []

    try:
        entry = float(decision.get("entry_price"))
        sl = float(decision.get("stop_loss_price"))
    except (TypeError, ValueError):
        return []

    bar = _latest_closed_bar(kline_frame)
    if bar is None:
        return []

    from pa_agent.util.price_tick import infer_price_tick_from_frame

    tick = infer_price_tick_from_frame(kline_frame) or 0.0
    k_high = float(bar.high)
    k_low = float(bar.low)
    k_close = float(bar.close)
    long = is_long_direction(decision.get("order_direction"))

    errors: list[str] = []
    if long is True:
        # Buy limit waits for price to dip to entry (sl < entry < tp).
        if k_low <= entry + tick:
            errors.append(
                f"limit long: K1 low {k_low:.6g} already touched/below entry {entry:.6g}; "
                "pending buy limit is stale — use 市价单, reprice, or 不下单"
            )
        if k_low <= sl + tick:
            errors.append(
                f"limit long: K1 low {k_low:.6g} already at/below stop {sl:.6g}; "
                "plan invalid — order_type=不下单"
            )
        if k_close < entry - tick:
            errors.append(
                f"limit long: K1 close {k_close:.6g} is below entry {entry:.6g}; "
                "do not keep a buy limit above market without repricing"
            )
    elif long is False:
        # Sell limit waits for price to rally to entry (tp < entry < sl).
        if k_high >= entry - tick:
            errors.append(
                f"limit short: K1 high {k_high:.6g} already reached/exceeded entry {entry:.6g}; "
                "pending sell limit is stale — use 市价单, reprice, or 不下单"
            )
        if k_high >= sl - tick:
            errors.append(
                f"limit short: K1 high {k_high:.6g} already at/above stop {sl:.6g}; "
                "plan invalid — order_type=不下单"
            )
        if k_close > entry + tick:
            errors.append(
                f"limit short: K1 close {k_close:.6g} is above entry {entry:.6g}; "
                "do not keep a sell limit below market without repricing"
            )

    return errors


def validate_order_trade_metrics(
    decision: dict[str, Any],
    *,
    decision_stance: str | None = None,
    kline_frame: Any = None,
) -> list[str]:
    """Validate entry/TP/SL geometry, RR floor, and trader equation for live orders."""
    order_type = decision.get("order_type")
    if order_type not in ("限价单", "突破单", "市价单"):
        return []

    entry = decision.get("entry_price")
    tp = decision.get("take_profit_price")
    sl = decision.get("stop_loss_price")
    direction = decision.get("order_direction")
    rr = compute_risk_reward(entry, tp, sl, direction)
    if rr is None:
        return [
            "decision prices: entry/stop/target must form a valid long (sl<entry<tp) "
            "or short (tp<entry<sl) trade with positive risk and reward"
        ]

    errors: list[str] = []
    ratio = float(rr["ratio"])
    risk = float(rr["risk"])
    reward = float(rr["reward"])
    min_rr = min_risk_reward_ratio(decision_stance)
    max_rr = max_risk_reward_ratio()

    if ratio < min_rr:
        errors.append(
            f"decision prices: risk_reward {rr['ratio_text']} is below minimum "
            f"{min_rr:.2f}:1 for this stance; adjust take_profit/stop_loss or set "
            "order_type=不下单 with 10.3=否"
        )

    if ratio > max_rr:
        errors.append(
            f"decision prices: risk_reward {rr['ratio_text']} exceeds maximum "
            f"{max_rr:.2f}:1; move take_profit closer (higher win-rate target) or set "
            "order_type=不下单 with 10.3=否"
        )

    win_rate = _parse_win_rate(decision.get("estimated_win_rate"))
    if win_rate is None:
        errors.append(
            "decision.estimated_win_rate: required integer 0–100 when placing an order"
        )
    elif not passes_trader_equation(win_rate, risk, reward):
        ev = win_rate / 100.0 * reward - (1.0 - win_rate / 100.0) * risk
        errors.append(
            f"decision prices: trader equation fails at {win_rate:.0f}% win rate "
            f"(risk={risk:.4g}, reward={reward:.4g}, expectancy≈{ev:.4g}); "
            "10.3 must be 否 and order_type=不下单 unless prices are fixed"
        )

    if kline_frame is not None:
        errors.extend(validate_limit_order_k1_freshness(decision, kline_frame))

    return errors
