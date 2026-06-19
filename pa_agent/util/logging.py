"""Centralised logging configuration for PA Agent.

Public API
----------
configure_logging(api_key: str = "") -> None
update_api_key(new_key: str) -> None
"""
from __future__ import annotations

import logging
import logging.handlers
from typing import List

from pa_agent.config.paths import LOG_FILE_PATH
from pa_agent.util.mask_secret import mask_secret

# ── Module-level state ────────────────────────────────────────────────────────

_active_formatters: List["MaskingFormatter"] = []
_configured: bool = False

# ── MaskingFormatter ──────────────────────────────────────────────────────────


class MaskingFormatter(logging.Formatter):
    """Logging formatter that replaces the plaintext API key with its masked form."""

    def __init__(self, fmt: str, api_key: str = "") -> None:
        super().__init__(fmt)
        self._api_key = api_key

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        message = super().format(record)
        if self._api_key:
            message = message.replace(self._api_key, mask_secret(self._api_key))
        return message

    def set_api_key(self, new_key: str) -> None:
        self._api_key = new_key


# ── Public functions ──────────────────────────────────────────────────────────

_LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"

_THIRD_PARTY_LOGGERS = ("urllib3", "openai", "httpx")

# tvdatafeed opens a websocket every refresh tick and logs at DEBUG — keep quiet
_QUIET_LOGGER_NAMES = (
    "urllib3",
    "openai",
    "httpx",
    "tvDatafeed",
    "tvDatafeed.main",
    "root",  # tvdatafeed uses logging.getLogger("root") for websocket
    "websocket",
)


def configure_logging(api_key: str = "") -> None:
    """Configure the root logger with rotating file handler and console handler.

    Both handlers use MaskingFormatter that replaces api_key with mask_secret(api_key).
    Third-party loggers (urllib3, openai, httpx) are also attached to the same handlers.
    """
    global _configured  # noqa: PLW0603

    if _configured:
        # Only update the masking key if already configured; skip re-adding handlers.
        if api_key:
            update_api_key(api_key)
        return

    # Build formatters
    file_formatter = MaskingFormatter(_LOG_FORMAT, api_key=api_key)
    console_formatter = MaskingFormatter(_LOG_FORMAT, api_key=api_key)

    # Track all active formatters so update_api_key can reach them
    _active_formatters.clear()
    _active_formatters.append(file_formatter)
    _active_formatters.append(console_formatter)

    # Rotating file handler
    LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE_PATH,
        maxBytes=5 * 1024 * 1024,
        backupCount=10,
        encoding="utf-8",
    )
    file_handler.setFormatter(file_formatter)

    # Console (stream) handler — INFO+ only; file keeps DEBUG for troubleshooting
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    handlers: list[logging.Handler] = [file_handler, console_handler]

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    # Remove any previously installed handlers to avoid duplicates on re-call
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)
    for h in handlers:
        root_logger.addHandler(h)

    # Attach the same handlers to third-party loggers
    for name in _THIRD_PARTY_LOGGERS:
        tp_logger = logging.getLogger(name)
        for h in list(tp_logger.handlers):
            tp_logger.removeHandler(h)
        for h in handlers:
            tp_logger.addHandler(h)
        # Prevent double-logging via root propagation
        tp_logger.propagate = False

    _silence_noisy_libraries()

    _configured = True


def _silence_noisy_libraries() -> None:
    """Turn down chatty third-party DEBUG loggers (tvdatafeed websocket spam)."""
    for name in _QUIET_LOGGER_NAMES:
        logging.getLogger(name).setLevel(logging.WARNING)


def update_api_key(new_key: str) -> None:
    """Update the masking key in all active MaskingFormatter instances."""
    for formatter in _active_formatters:
        formatter.set_api_key(new_key)
