"""Parse and validate coverage-isolate configuration values."""

from __future__ import annotations

import functools
from typing import TYPE_CHECKING, Literal, cast, overload

import coverage_isolate.exceptions as exc
from coverage_isolate.config.types import CoverageIsolateConfig
from coverage_isolate.utils import resolve_path

if TYPE_CHECKING:
    from pathlib import Path

resolve = functools.partial(resolve_path, exc_type=exc.SourceDiscoveryError)


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
        SourceDiscoveryError: If a project path cannot be resolved.

    """
    try:
        root = root.resolve(strict=True)
    except OSError as error:
        msg = f"Could not resolve root path {root}: {error}"
        raise exc.SourceDiscoveryError(msg) from error

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
        run_omit=_coverage_string_tuple(run_omit, "run:omit", allow_none=True) or (),
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
            return tuple(cast("list[str]", items))
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
        source_path = resolve(root, _string(source, setting), label=setting)
        target_path = resolve(root, _string(target, setting), label=setting)
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
        source_path = resolve(root, _string(source, "test-paths"), label="test-paths")
        if isinstance(raw_targets, list):
            targets = cast("list[object]", raw_targets)
        else:
            targets = [raw_targets]
        if not targets:
            msg = f"test-paths mapping for {source_path} cannot be empty"
            raise exc.ConfigurationError(msg)
        paths = tuple(
            resolve(root, _string(target, "test-paths"), label="test-paths")
            for target in targets
        )
        if len(set(paths)) != len(paths):
            msg = f"test-paths mapping for {source_path} contains duplicates"
            raise exc.ConfigurationError(msg)
        result[source_path] = paths
    return result
