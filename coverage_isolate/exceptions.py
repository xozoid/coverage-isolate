"""Exceptions raised by coverage-isolate."""

from __future__ import annotations


class ConfigurationError(Exception):
    """Error when project configuration is missing or invalid."""


class SourceDiscoveryError(Exception):
    """Error when a source selection is invalid."""


class MappingError(Exception):
    """Error when source-to-test mapping paths are invalid."""
