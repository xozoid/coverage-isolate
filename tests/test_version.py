from __future__ import annotations

from importlib.metadata import version

from coverage_isolate import __version__


def test_version_matches_installed_distribution() -> None:
    assert __version__ == version("coverage-isolate")
