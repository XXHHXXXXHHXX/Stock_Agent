"""Validation retry policy: which errors may retry and immutable field guards."""
from __future__ import annotations

import re
from typing import Any, Literal

StageName = Literal["stage1", "stage2"]

# Format-like invalid field prefixes — safe to retry without changing trade thesis.
_FORMAT_PREFIXES: tuple[str, ...] = (
    "gate_trace",
    "decision_trace",
    "bar_by_bar_summary",
    "bar_range",
    "incremental",
    "next_bar_prediction",
    "next_cycle_prediction",
)

# Semantic errors that must NOT trigger retry (program should downgrade instead).
_NO_RETRY_PREFIXES: tuple[str, ...] = (
    "metrics:",
    "trace:§14",
    "s2:order_direction",
)

IMMUTABLE_FIELDS: dict[StageName, tuple[str, ...]] = {
    "stage1": ("direction", "cycle_position", "gate_result"),
    "stage2": (),  # stage2 direction lives in diagnosis_summary; checked separately
}

IMMUTABLE_DIAG_SUMMARY: tuple[str, ...] = ("cycle_position",)


def max_retries_for_category(category: str, settings: Any) -> int:
    """Return allowed retry count for a validation category."""
    if category == "e":
        return 0
    if not getattr(settings, "retry_enabled", True):
        return 0
    base = int(getattr(settings, "retry_max", 3) or 0)
    if category in ("a", "b", "d"):
        return base
    if category == "c":
        return min(base, int(getattr(settings, "retry_max_semantic", 1) or 1))
    return 0


def should_retry(
    category: str,
    invalid_fields: list[str],
    missing_fields: list[str],
    *,
    attempt: int,
    settings: Any,
) -> bool:
    """Whether another API call is warranted."""
    if category == "e":
        return False
    if attempt >= max_retries_for_category(category, settings):
        return False
    if category in ("a", "b", "d"):
        return True
    if category != "c":
        return False
    fields = list(invalid_fields or []) + list(missing_fields or [])
    if not fields:
        return False
    if any(_starts_any(f, _NO_RETRY_PREFIXES) for f in fields):
        return False
    if any(_starts_any(f, _FORMAT_PREFIXES) for f in fields):
        return True
    if any(
        f.startswith(("s1:", "s2:", "gate:", "trace:", "breakout_price:", "signal_chain:"))
        for f in fields
    ):
        # Default: one semantic retry if enabled
        return attempt < int(getattr(settings, "retry_max_semantic", 1) or 1)
    return False


def _starts_any(field: str, prefixes: tuple[str, ...]) -> bool:
    text = str(field or "")
    return any(text.startswith(p) or p in text for p in prefixes)


def _get_path(obj: dict[str, Any], path: str) -> Any:
    cur: Any = obj
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def detect_cheat(
    stage: StageName,
    before: dict[str, Any] | None,
    after: dict[str, Any],
    *,
    feedback_mentioned: set[str] | None = None,
) -> list[str]:
    """Return human-readable cheat flags when immutable fields changed without cause."""
    if not before or not isinstance(after, dict):
        return []
    mentioned = feedback_mentioned or set()
    violations: list[str] = []

    for key in IMMUTABLE_FIELDS.get(stage, ()):
        if key in mentioned:
            continue
        b = before.get(key)
        a = after.get(key)
        if b is not None and a is not None and str(b) != str(a):
            violations.append(f"{key}: {b!r} → {a!r}")

    if stage == "stage2":
        bsum = before.get("diagnosis_summary") if isinstance(before.get("diagnosis_summary"), dict) else {}
        asum = after.get("diagnosis_summary") if isinstance(after.get("diagnosis_summary"), dict) else {}
        for key in IMMUTABLE_DIAG_SUMMARY:
            path = f"diagnosis_summary.{key}"
            if path in mentioned or key in mentioned:
                continue
            b = bsum.get(key)
            a = asum.get(key)
            if b is not None and a is not None and str(b) != str(a):
                violations.append(f"{path}: {b!r} → {a!r}")

    return violations


def extract_feedback_targets(invalid_fields: list[str], missing_fields: list[str]) -> set[str]:
    """Map error lines to field paths mentioned in retry feedback."""
    targets: set[str] = set()
    for raw in list(missing_fields or []) + list(invalid_fields or []):
        text = str(raw)
        for key in (
            "direction",
            "cycle_position",
            "gate_result",
            "diagnosis_summary",
            "order_type",
            "next_bar_prediction",
            "next_cycle_prediction",
        ):
            if key in text:
                targets.add(key)
    return targets
