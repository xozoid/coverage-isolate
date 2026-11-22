from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

import coverage_isolate.exceptions as exc
from coverage_isolate.config import load_config
from coverage_isolate.config.parsing import parse_config

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def test_load_config_reads_coverage_absent_options(project: Path) -> None:
    config = load_config(project)

    assert config.project_root == project
    assert config.source is None
    assert config.run_omit == ()
    assert config.report_omit is None
    assert config.test_roots == {}
    assert config.test_paths == {}


def test_load_config_reads_coverage_source_and_omit_patterns(
    project: Path,
    project_tree: Callable[..., tuple[Path, ...]],
) -> None:
    project_tree(
        "src/api.py",
        "tests/test_api.py",
        directories=("pkg.module",),
        root=project,
    )

    config = load_config(project)

    assert config.source == ("src", "pkg.module")
    assert config.run_omit == ("*/generated/*", "*/legacy.py")
    assert config.report_omit == ("*/tests/*",)
    assert config.test_roots == {project / "pkg.module": project / "tests"}
    expected_paths = {project / "src/api.py": (project / "tests/test_api.py",)}
    assert config.test_paths == expected_paths


def test_load_config_allows_parent_components_that_stay_within_project(
    project: Path,
    project_tree: Callable[..., tuple[Path, ...]],
) -> None:
    project_tree(directories=("src", "tests"), root=project)
    config = load_config(project)
    assert config.test_roots == {project / "tests": project / "tests"}


def test_load_config_rejects_symlink_escape(
    project: Path,
    project_tree: Callable[..., tuple[Path, ...]],
) -> None:
    outside = project.parent / "outside"
    outside.mkdir(exist_ok=True)
    (outside / "test.py").touch()
    project_tree("src/mod.py", root=project)
    (project / "linked").symlink_to(outside, target_is_directory=True)

    with pytest.raises(
        exc.SourceDiscoveryError,
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
    ],
    indirect=["project"],
)
def test_load_config_rejects_invalid_settings(
    project: Path,
    message: str,
) -> None:
    with pytest.raises(exc.ConfigurationError, match=re.escape(message)):
        load_config(project)


@pytest.mark.parametrize("project", ["source_path_escapes"], indirect=True)
def test_load_config_rejects_source_path_outside_project(project: Path) -> None:
    (project.parent / "source.py").touch()

    with pytest.raises(
        exc.SourceDiscoveryError,
        match="outside the project root",
    ):
        load_config(project)


def test_load_config_reports_missing_pyproject(tmp_path: Path) -> None:
    with pytest.raises(
        exc.ConfigurationError,
        match="Project configuration not found",
    ):
        load_config(tmp_path)


@pytest.mark.parametrize(
    ("project", "message", "error"),
    [
        (
            "roots_not_table",
            r"test-roots must be a table of paths",
            exc.ConfigurationError,
        ),
        ("root_source_escapes", r"outside the project root", exc.SourceDiscoveryError),
        ("root_target_escapes", r"outside the project root", exc.SourceDiscoveryError),
        (
            "empty_test_paths",
            r"test-paths mapping for .*mod\.py cannot be empty",
            exc.ConfigurationError,
        ),
        (
            "duplicate_test_paths",
            r"test-paths mapping for .*mod\.py contains duplicates",
            exc.ConfigurationError,
        ),
        (
            "non_string_test_path",
            r"test-paths must be a non-empty string",
            exc.ConfigurationError,
        ),
    ],
    indirect=["project"],
)
def test_load_config_rejects_invalid_values(
    project: Path,
    message: str,
    error: type[Exception],
    project_tree: Callable[..., tuple[Path, ...]],
) -> None:
    project_tree("src/mod.py", "tests/test.py", root=project)
    (project.parent / "src").mkdir(exist_ok=True)
    (project.parent / "tests").mkdir(exist_ok=True)

    with pytest.raises(error, match=message):
        load_config(project)


@pytest.mark.parametrize("project", ["absolute_test_path"], indirect=True)
def test_load_config_rejects_absolute_test_path_outside_project(
    project: Path,
    project_tree: Callable[..., tuple[Path, ...]],
) -> None:
    project_tree("src/mod.py", root=project)
    with pytest.raises(
        exc.SourceDiscoveryError,
        match=r"Could not resolve test-paths path /tests/test\.py",
    ):
        load_config(project)


def test_parse_config_accepts_absolute_mapping_paths_inside_project(
    project_tree: Callable[..., tuple[Path, ...]],
) -> None:
    project, source, target = project_tree("src/mod.py", "tests/test_mod.py")

    config = parse_config(
        project,
        {"tool": {"coverage-isolate": {"test-paths": {str(source): str(target)}}}},
        None,
        [],
        None,
    )

    assert config.test_paths == {source: (target,)}


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


@pytest.mark.parametrize("source", [1, ["src", 1]])
def test_parse_config_rejects_non_string_coverage_source(
    tmp_path: Path,
    source: object,
) -> None:
    with pytest.raises(exc.ConfigurationError, match=r"coverage option run:source"):
        parse_config(tmp_path, {}, source, [], None)


@pytest.mark.parametrize("run_omit", [None, []])
def test_parse_config_accepts_unset_run_omit(tmp_path: Path, run_omit: object) -> None:
    config = parse_config(tmp_path, {}, None, run_omit, None)
    assert config.run_omit == ()


def test_parse_config_rejects_invalid_run_omit(tmp_path: Path) -> None:
    with pytest.raises(exc.ConfigurationError, match=r"coverage option run:omit"):
        parse_config(tmp_path, {}, None, 0, None)


def test_parse_config_rejects_missing_root(tmp_path: Path) -> None:
    root = tmp_path / "missing"
    with pytest.raises(exc.SourceDiscoveryError, match="Could not resolve root path"):
        parse_config(root, {}, None, [], None)
