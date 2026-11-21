"""Exceptions raised by coverage-isolate."""

from __future__ import annotations


class ConfigurationError(BaseException):
    """Raised when project configuration is missing or invalid."""
