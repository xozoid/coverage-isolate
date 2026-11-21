"""pytest command-line options for coverage-isolate."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

import pytest

import coverage_isolate.exceptions as exc
from coverage_isolate.config import load_config

if TYPE_CHECKING:
    from pathlib import Path


class _Config(Protocol):
    """The configuration methods needed by this plugin."""

    def getoption(self, name: str) -> object: ...

    @property
    def rootpath(self) -> Path: ...


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register coverage-isolate options with pytest."""
    group = parser.getgroup("coverage-isolate")
    group.addoption(
        "--iso",
        action="store_true",
        default=False,
        help="record coverage in test-file contexts for isolated reporting",
    )
    group.addoption(
        "--iso-source",
        action="append",
        default=[],
        metavar="PATH",
        help="limit isolated coverage to a source path (may be repeated)",
    )


def pytest_configure(config: _Config) -> None:
    """Validate pytest options.

    Raises:
        pytest.UsageError: If source paths are given without enabling isolation.
    """
    iso_enabled = config.getoption("iso")
    iso_sources = config.getoption("iso_source")
    if iso_sources and not iso_enabled:
        msg = "--iso-source requires --iso"
        raise pytest.UsageError(msg)
    if iso_enabled:
        try:
            load_config(config.rootpath)
        except exc.ConfigurationError as error:
            raise pytest.UsageError(str(error)) from error
        msg = "--iso is not implemented yet"
        raise pytest.UsageError(msg)
