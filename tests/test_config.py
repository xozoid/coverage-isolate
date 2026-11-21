from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

import coverage_isolate.exceptions as exc
from coverage_isolate.config import load_config

if TYPE_CHECKING:
    from pathlib import Path


def test_load_config_reads_coverage_absent_options(project: Path) -> None:
    config = load_config(project)

    assert config.project_root == project
    assert config.source is None
    assert config.run_omit == ()
    assert config.report_omit is None
    assert config.test_roots == {}
    assert config.test_paths == {}


def test_load_config_reads_coverage_source_and_omit_patterns(project: Path) -> None:
    config = load_config(project)

    assert config.source == ("src", "pkg.module")
    assert config.run_omit == ("*/generated/*", "*/legacy.py")
    assert config.report_omit == ("*/tests/*",)
    assert config.test_roots == {project / "pkg.module": project / "tests"}
    expected_paths = {project / "src/api.py": (project / "tests/test_api.py",)}
    assert config.test_paths == expected_paths


def test_load_config_allows_parent_components_that_stay_within_project(
    project: Path,
) -> None:
    config = load_config(project)

    assert config.test_roots == {project / "tests": project / "tests"}


def test_load_config_rejects_symlink_escape(project: Path) -> None:
    outside = project.parent / "outside"
    outside.mkdir()
    (project / "linked").symlink_to(outside, target_is_directory=True)

    with pytest.raises(
        exc.ConfigurationError,
        match=r"resolves outside the project root",
    ):
        load_config(project)


@pytest.mark.parametrize(
    ("project", "message"),
    [
        ("unknown_source_roots", "Unknown [tool.coverage-isolate] setting"),
        ("unknown_test_root", "Unknown [tool.coverage-isolate] setting"),
        ("unknown_exclude_files", "Unknown [tool.coverage-isolate] setting"),
        ("unknown_setting", "Unknown [tool.coverage-isolate] setting"),
        ("source_path_escapes", "project-relative path"),
    ],
    indirect=["project"],
)
def test_load_config_rejects_invalid_settings(
    project: Path,
    message: str,
) -> None:
    with pytest.raises(exc.ConfigurationError, match=re.escape(message)):
        load_config(project)


def test_load_config_reports_missing_pyproject(tmp_path: Path) -> None:
    with pytest.raises(
        exc.ConfigurationError,
        match="Project configuration not found",
    ):
        load_config(tmp_path)


@pytest.mark.parametrize(
    ("project", "message"),
    [
        ("roots_not_table", r"test-roots must be a table of paths"),
        ("root_source_escapes", r"project-relative path"),
        ("root_target_escapes", r"project-relative path"),
        (
            "empty_test_paths",
            r"test-paths mapping for .*mod\.py cannot be empty",
        ),
        (
            "duplicate_test_paths",
            r"test-paths mapping for .*mod\.py contains duplicates",
        ),
        ("non_string_test_path", r"test-paths must be a non-empty string"),
        ("absolute_test_path", r"project-relative path"),
    ],
    indirect=["project"],
)
def test_load_config_rejects_invalid_values(
    project: Path,
    message: str,
) -> None:
    with pytest.raises(exc.ConfigurationError, match=message):
        load_config(project)


@pytest.mark.parametrize(
    "project",
    [
        "tool_not_table",
        "coverage_isolate_not_table",
        "roots_string",
        "paths_string",
    ],
    indirect=["project"],
)
def test_load_config_rejects_non_table_values(project: Path) -> None:
    with pytest.raises(exc.ConfigurationError):
        load_config(project)


def test_load_config_reports_invalid_toml(project: Path) -> None:
    with pytest.raises(exc.ConfigurationError, match=r"Could not read"):
        load_config(project)
