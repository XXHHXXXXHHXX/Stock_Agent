"""Tests for demo replay reasoning extraction."""
from __future__ import annotations

from pa_agent.demo import replayer as replayer_mod


def test_reasoning_from_flat_record_response() -> None:
    """Pending JSON stores reasoning_content at top level (not choices[].message)."""
    text = "思考片段"
    assert (
        replayer_mod._reasoning_from_response(
            {"id": "x", "content": "{}", "reasoning_content": text}
        )
        == text
    )


def test_reasoning_from_openai_choices_shape() -> None:
    assert (
        replayer_mod._reasoning_from_response(
            {
                "choices": [
                    {"message": {"reasoning_content": "abc", "content": "{}"}}
                ]
            }
        )
        == "abc"
    )


def test_reasoning_prefers_top_level_when_both_present() -> None:
    assert (
        replayer_mod._reasoning_from_response(
            {
                "reasoning_content": "top",
                "choices": [{"message": {"reasoning_content": "nested"}}],
            }
        )
        == "top"
    )
