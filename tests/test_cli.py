from __future__ import annotations

import shutil
import subprocess
import sys
from types import ModuleType
from typing import TYPE_CHECKING

import pytest

from coverage_isolate import __version__
from coverage_isolate.cli import build_parser, main

if TYPE_CHECKING:
    from pathlib import Path


def test_parser_accepts_no_sources() -> None:
    args = build_parser().parse_args([])

    assert args.sources == []
    assert args.per_file is False


def test_completion_hook_runs_when_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = ModuleType("argcomplete")
    calls: list[object] = []
    module.__dict__["autocomplete"] = calls.append
    monkeypatch.setitem(sys.modules, "argcomplete", module)

    with pytest.raises(SystemExit) as exc:
        main(["--help"])

    assert exc.value.code == 0
    assert len(calls) == 1


def test_help_succeeds_without_argcomplete(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "argcomplete", None)

    with pytest.raises(SystemExit) as exc:
        main(["--help"])

    assert exc.value.code == 0


@pytest.mark.parametrize("flag", ["--version", "-v"])
def test_version_exits_without_project_configuration(
    flag: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit) as exc:
        main([flag])

    assert exc.value.code == 0
    assert capsys.readouterr().out == f"coverage-isolate {__version__}\n"


def test_parser_accepts_sources_and_per_file_flag() -> None:
    args = build_parser().parse_args(
        ["--per-file", "src/one.py", "src/two.py"],
    )

    assert args.sources == ["src/one.py", "src/two.py"]
    assert args.per_file is True


@pytest.mark.xfail(strict=True, reason="Coverage execution is not implemented yet")
def test_main_runs_tests_and_reports_selected_source_coverage(
    project: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(project)

    result = main(["src/example.py"])
    captured = capsys.readouterr()

    assert result == 0
    assert "example.py" in captured.out
    assert "not implemented" not in captured.err


def test_main_reports_invalid_project_configuration(
    project: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(project)

    result = main([])
    captured = capsys.readouterr()

    assert result == 2
    assert "Unknown [tool.coverage-isolate] setting" in captured.err


def test_installed_cli_help_displays_options() -> None:
    executable = shutil.which("coverage-isolate")
    assert executable is not None

    result = subprocess.run(
        [executable, "--help"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "--per-file" in result.stdout
    assert "SOURCE" in result.stdout
