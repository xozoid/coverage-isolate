"""Tests for pytest plugin options."""

from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING, cast

import pytest

from coverage_isolate.plugin import pytest_addoption, pytest_configure

if TYPE_CHECKING:
    from pathlib import Path


def test_pytest_parser_accepts_isolation_options() -> None:
    class Group:
        options: dict[str, dict[str, object]]

        def __init__(self) -> None:
            self.options = {}

        def addoption(self, name: str, **kwargs: object) -> None:
            self.options[name] = kwargs

    class Parser:
        def __init__(self) -> None:
            self.group = Group()

        def getgroup(self, name: str) -> Group:
            assert name == "coverage-isolate"
            return self.group

    parser = Parser()
    pytest_addoption(cast("pytest.Parser", parser))

    assert "--iso" in parser.group.options
    assert "--iso-source" in parser.group.options
    assert parser.group.options["--iso-source"]["action"] == "append"


def test_pytest_configure_allows_isolation_to_be_disabled(tmp_path: Path) -> None:
    class Config:
        @property
        def rootpath(self) -> Path:
            return tmp_path

        @staticmethod
        def getoption(name: str) -> object:
            return False if name == "iso" else []

    pytest_configure(Config())


def test_iso_source_requires_iso(tmp_path: Path) -> None:
    class Config:
        @property
        def rootpath(self) -> Path:
            return tmp_path

        @staticmethod
        def getoption(name: str) -> object:
            if name == "iso":
                return False
            return ["src/one.py"]

    with pytest.raises(pytest.UsageError, match=r"--iso-source requires --iso"):
        pytest_configure(Config())


@pytest.mark.xfail(
    strict=True,
    raises=pytest.UsageError,
    reason="Isolated coverage is not implemented yet",
)
def test_iso_accepts_valid_project_configuration(project: Path) -> None:
    class Config:
        @property
        def rootpath(self) -> Path:
            return project

        @staticmethod
        def getoption(name: str) -> object:
            if name == "iso":
                return True
            return []

    pytest_configure(Config())


def test_iso_reports_invalid_project_configuration(project: Path) -> None:
    class Config:
        @property
        def rootpath(self) -> Path:
            return project

        @staticmethod
        def getoption(name: str) -> object:
            if name == "iso":
                return True
            return []

    with pytest.raises(
        pytest.UsageError,
        match=r"Unknown \[tool\.coverage-isolate\] setting",
    ):
        pytest_configure(Config())


def test_installed_pytest_plugin_options_appear_in_help(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--help"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "--iso" in result.stdout
    assert "--iso-source=PATH" in result.stdout
