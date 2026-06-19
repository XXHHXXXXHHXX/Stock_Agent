from __future__ import annotations

from unittest.mock import MagicMock, patch

from pa_agent.ai.qclaw_connector import apply_qclaw_provider_to_settings
from pa_agent.ai.workbuddy_connector import apply_workbuddy_provider_to_settings
from pa_agent.config.settings import Settings


def test_openclaw_overrides_user_url_and_key() -> None:
    """When model is openclaw*, user-filled base_url/api_key must be ignored."""
    s = Settings()
    s.provider.model = "openclaw"
    s.provider.base_url = "https://example.com/v1"
    s.provider.api_key = "sk-user-input"

    # Stub QClaw detection and settings resolution to avoid filesystem/network.
    with patch("pa_agent.ai.qclaw_connector.detect_qclaw", return_value=True), patch(
        "pa_agent.ai.qclaw_connector.qclaw_provider_settings"
    ) as resolve, patch("pa_agent.ai.qclaw_connector.qclaw_health_check", return_value=(True, "ok")):
        resolved = MagicMock()
        resolved.model = "openclaw"
        resolved.base_url = "http://127.0.0.1:51187/v1"
        resolved.api_key = "tok-from-qclaw"
        resolved.thinking = True
        resolved.reasoning_effort = "max"
        resolved.context_window = 2_000_000
        resolve.return_value = resolved

        err = apply_qclaw_provider_to_settings(s, preferred_model="openclaw")
        assert err is None

    assert s.provider.base_url == "http://127.0.0.1:51187/v1"
    assert s.provider.api_key == "tok-from-qclaw"


def test_openclaw_wb_overrides_user_url_and_key() -> None:
    """When model is openclaw_wb*, user-filled base_url/api_key must be ignored."""
    s = Settings()
    s.provider.model = "openclaw_wb"
    s.provider.base_url = "https://example.com/v1"
    s.provider.api_key = "sk-user-input"

    with patch("pa_agent.ai.workbuddy_connector.detect_workbuddy", return_value=True), patch(
        "pa_agent.ai.workbuddy_connector.workbuddy_provider_settings"
    ) as resolve, patch(
        "pa_agent.ai.workbuddy_connector.workbuddy_health_check",
        return_value=(True, "ok"),
    ):
        resolved = MagicMock()
        resolved.model = "openclaw_wb"
        resolved.base_url = "https://copilot.tencent.com/v2"
        resolved.api_key = "tok-from-workbuddy"
        resolved.thinking = True
        resolved.reasoning_effort = "max"
        resolved.context_window = 2_000_000
        resolve.return_value = resolved

        err = apply_workbuddy_provider_to_settings(s, preferred_model="openclaw_wb")
        assert err is None

    assert s.provider.base_url == "https://copilot.tencent.com/v2"
    assert s.provider.api_key == "tok-from-workbuddy"

