"""Unit tests for api.logging_setup."""

from __future__ import annotations

import logging

from api import logging_setup


def test_configure_logging_sets_level() -> None:
    logging_setup._CONFIGURED = False
    logging_setup.configure_logging("DEBUG")
    assert logging.getLogger().level == logging.DEBUG


def test_configure_logging_falls_back_on_unknown_level() -> None:
    logging_setup._CONFIGURED = False
    logging_setup.configure_logging("NOT_A_LEVEL")
    assert logging.getLogger().level == logging.INFO


def test_configure_logging_is_idempotent() -> None:
    logging_setup._CONFIGURED = False
    logging_setup.configure_logging("WARNING")
    root = logging.getLogger()
    handler_count = len(root.handlers)
    logging_setup.configure_logging("ERROR")
    assert len(root.handlers) == handler_count
    assert root.level == logging.WARNING
