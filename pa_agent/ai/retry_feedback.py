"""Build structured retry user messages from ValidationError."""
from __future__ import annotations

import json
from typing import Any, Literal

from pa_agent.ai.retry_policy import StageName, extract_feedback_targets
from pa_agent.ai.validation_messages import format_validation_errors

StageLit = Literal["stage1", "stage2"]

_CATEGORY_ZH: dict[str, str] = {
    "a": "JSON 语法错误",
    "b": "缺少必填字段",
    "c": "字段值/一致性不符合规则",
    "d": "未输出 JSON（正文为空或纯文字）",
}

_FORBIDDEN_STAGE1 = (
    "direction / cycle_position / gate_result（除非反馈明确要求修改且你有 K 线依据）",
    "bar_by_bar_summary[].bar_type（必须服从程序几何表）",
    "程序锁定节点 §1.1",
)

_FORBIDDEN_STAGE2 = (
    "diagnosis_summary.cycle_position / direction（除非反馈明确要求）",
    "为通过校验把 order_type 从「不下单」改成下单（或反之）",
    "交易者方程 10.3 的数值结论（须基于真实 entry/stop/target 重算）",
)


def _try_parse_obj(raw: str) -> dict[str, Any] | None:
    text = (raw or "").strip()
    if not text.startswith("{"):
        return None
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _geometry_excerpt(frame: Any, limit: int = 8) -> str:
    try:
        from pa_agent.ai.kline_features import compute_kline_geometry_features

        feats = compute_kline_geometry_features(frame, limit=limit)
        lines = ["程序 K 线几何表（bar_type 权威来源，bar_by_bar_summary 必须一致）："]
        for f in feats:
            lines.append(f"  K{f.seq}: {f.bar_type}")
        return "\n".join(lines)
    except Exception:  # noqa: BLE001
        return ""


def build_retry_feedback(
    err: Any,
    *,
    stage: StageLit,
    attempt: int,
    max_attempts: int,
    frame: Any = None,
    previous_raw: str | None = None,
) -> str:
    """Compose a concise retry user turn."""
    category = str(getattr(err, "category", "c") or "c")
    missing = list(getattr(err, "missing_fields", None) or [])
    invalid = list(getattr(err, "invalid_fields", None) or [])
    detail = format_validation_errors(invalid, missing_fields=missing, max_items=6)
    cat_zh = _CATEGORY_ZH.get(category, category)

    lines = [
        f"## 校验未通过（第 {attempt}/{max_attempts} 次重试）",
        "",
        f"阶段：**{stage}**",
        f"失败类型：**{cat_zh}** (category={category})",
        f"说明：{getattr(err, 'message', '')}",
    ]
    if getattr(err, "parse_position", None):
        lines.append(f"JSON 解析位置：{err.parse_position}")
    lines.append("")
    lines.append("**必须修正（仅修下列项；其余字段保持与上一轮一致）：**")
    if missing:
        for i, m in enumerate(missing[:6], 1):
            lines.append(f"{i}. [缺少] {m}")
    for i, inv in enumerate(invalid[:6], start=len(missing[:6]) + 1):
        lines.append(f"{i}. [无效] {inv}")
    if detail:
        lines.append(f"摘要：{detail}")

    lines.append("")
    lines.append("**禁止为通过校验而修改：**")
    forbidden = _FORBIDDEN_STAGE1 if stage == "stage1" else _FORBIDDEN_STAGE2
    for item in forbidden:
        lines.append(f"- {item}")

    geo = _geometry_excerpt(frame) if stage == "stage1" and frame is not None else ""
    if geo:
        lines.append("")
        lines.append(geo)

    lines.append("")
    lines.append(
        "请根据以上说明，在 assistant 正文 `content` 输出**完整**阶段"
        f"{'一' if stage == 'stage1' else '二'}裸 JSON（不要 markdown 围栏）。"
        "交易结论须与 K 线分析一致，不得仅为修字段而反转方向。"
    )

    if category == "d":
        if not (previous_raw or "").strip():
            lines.append(
                "⚠️ 上一轮正文 content 为空：请把 JSON 写在 content，不要只写在思考区。"
            )
        if stage == "stage2":
            lines.append(
                "⚠️ 禁止输出英文说明、Markdown 表格/摘要、「修改完成」「已写入文件」等对话文字；"
                "禁止 ` ```json ` 围栏。content 必须整段为可 `json.loads` 的阶段二裸 JSON。"
            )

    return "\n".join(lines)


def parse_previous_for_cheat(raw: str | None) -> dict[str, Any] | None:
    return _try_parse_obj(raw or "")
