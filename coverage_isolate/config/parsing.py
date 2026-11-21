"""Parse and validate coverage-isolate configuration values."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, cast, overload

import coverage_isolate.exceptions as exc
from coverage_isolate.config.types import CoverageIsolateConfig


def parse_config(
    root: Path,
    document: dict[str, object],
    source: object,
    run_omit: object,
    report_omit: object,
) -> CoverageIsolateConfig:
    """Validate configuration tables and build the settings object.

    Returns:
        The validated package configuration.

    Raises:
        ConfigurationError: If configuration values are invalid.

    """
    tool = _table(document, "tool", "[tool] in pyproject.toml")
    raw = _table(tool, "coverage-isolate", "[tool.coverage-isolate]")

    allowed = {"test-roots", "test-paths"}
    unknown = raw.keys() - allowed
    if unknown:
        names = ", ".join(sorted(unknown))
        msg = f"Unknown [tool.coverage-isolate] setting(s): {names}"
        raise exc.ConfigurationError(msg)

    mapping = _table(raw, "test-roots", description="a table of paths")
    test_roots = _directory_mapping(root, mapping, "test-roots")
    mapping = _table(raw, "test-paths", description="a table of paths")
    test_paths = _test_path_mapping(root, mapping)
    return CoverageIsolateConfig(
        project_root=root,
        source=_coverage_string_tuple(source, "run:source", allow_none=True),
        run_omit=_coverage_string_tuple(run_omit, "run:omit"),
        report_omit=_coverage_string_tuple(report_omit, "report:omit", allow_none=True),
        test_roots=test_roots,
        test_paths=test_paths,
    )


@overload
def _coverage_string_tuple(
    value: object,
    setting: str,
    *,
    allow_none: Literal[True],
) -> tuple[str, ...] | None: ...


@overload
def _coverage_string_tuple(
    value: object,
    setting: str,
    *,
    allow_none: Literal[False] = False,
) -> tuple[str, ...]: ...


def _coverage_string_tuple(
    value: object,
    setting: str,
    *,
    allow_none: bool = False,
) -> tuple[str, ...] | None:
    """Convert a coverage option to a tuple without altering its entries.

    Returns:
        The configured strings, or ``None`` when an optional option is unset.

    Raises:
        ConfigurationError: If the coverage option has an unexpected shape.

    """
    if value is None and allow_none:
        return None
    if isinstance(value, list):
        items = cast("list[object]", value)
        if all(isinstance(item, str) for item in items):
            return tuple(cast("list[str]", value))
    msg = f"coverage option {setting} must be an array of strings"
    raise exc.ConfigurationError(msg)


def _string(value: object, setting: str) -> str:
    """Return one non-empty string setting.

    Returns:
        The validated string.

    Raises:
        ConfigurationError: If configuration values are invalid.

    """
    if isinstance(value, str) and (v := value.strip()):
        return v
    msg = f"{setting} must be a non-empty string"
    raise exc.ConfigurationError(msg)


def _table(
    parent: dict[str, object],
    key: str,
    setting: str | None = None,
    *,
    description: str = "a table",
) -> dict[str, object]:
    """Validate a TOML table.

    Returns:
        The table as a mapping of strings to values.

    Raises:
        ConfigurationError: If the value is not a table.
    """
    value = parent.get(key, {})
    if isinstance(value, dict):
        return cast("dict[str, object]", value)
    msg = f"{setting or key} must be {description}"
    raise exc.ConfigurationError(msg)


def _relative_path(root: Path, value: str, setting: str) -> Path:
    """Validate a configured relative path.

    Returns:
        The resolved absolute path inside the project.

    Raises:
        ConfigurationError: If the path is absolute or escapes the project.
    """
    path = Path(value)
    if path.is_absolute():
        msg = f"{setting} must be a project-relative path: {path}"
        raise exc.ConfigurationError(msg)
    resolved_root = root.resolve()
    resolved_path = (resolved_root / path).resolve()
    if resolved_path.is_relative_to(resolved_root):
        return resolved_path
    msg = (
        f"{setting} must be a project-relative path; "
        f"resolves outside the project root: {path}"
    )
    raise exc.ConfigurationError(msg)


def _directory_mapping(
    root: Path,
    mapping: dict[str, object],
    setting: str,
) -> dict[Path, Path]:
    """Validate a mapping of source roots to test directories.

    Returns:
        Resolved source-to-test-root mappings.

    """
    result: dict[Path, Path] = {}
    for source, target in mapping.items():
        source_path = _relative_path(root, _string(source, setting), setting)
        target_path = _relative_path(root, _string(target, setting), setting)
        result[source_path] = target_path
    return result


def _test_path_mapping(
    root: Path,
    mapping: dict[str, object],
) -> dict[Path, tuple[Path, ...]]:
    """Validate explicit source-file to test-target mappings.

    Returns:
        Resolved source-to-test-target mappings.

    Raises:
        ConfigurationError: If configuration values are invalid.

    """
    result: dict[Path, tuple[Path, ...]] = {}
    for source, raw_targets in mapping.items():
        source_path = _relative_path(root, _string(source, "test-paths"), "test-paths")
        if isinstance(raw_targets, list):
            targets = cast("list[object]", raw_targets)
        else:
            targets = [raw_targets]
        if targets:
            paths = tuple(
                _relative_path(root, _string(target, "test-paths"), "test-paths")
                for target in targets
            )
        else:
            msg = f"test-paths mapping for {source_path} cannot be empty"
            raise exc.ConfigurationError(msg)
        if len(set(paths)) != len(paths):
            msg = f"test-paths mapping for {source_path} contains duplicates"
            raise exc.ConfigurationError(msg)
        result[source_path] = paths
    return result
