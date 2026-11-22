"""Resolve source files to pytest targets and collected test-file contexts."""

from __future__ import annotations

import functools
from typing import TYPE_CHECKING

import coverage_isolate.exceptions as exc
from coverage_isolate.utils import resolve_path

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from coverage_isolate.config.types import CoverageIsolateConfig


resolve = functools.partial(resolve_path, exc_type=exc.MappingError)


def map_sources_to_tests(
    sources: Iterable[Path],
    config: CoverageIsolateConfig,
) -> dict[Path, tuple[Path, ...]]:
    """Map each source file to explicit or conventional pytest targets.

    Explicit ``test-paths`` entries take precedence. Otherwise the most
    specific configured source root is paired with its configured test root.
    With no matching root, coverage ``source`` entries provide roots; as a
    final fallback, the conventional ``src`` directory is used when it
    contains the source. A source without a matching target raises a mapping
    diagnostic rather than selecting unrelated tests.

    Returns:
        A mapping from normalized source files to one or more test targets.

    Raises:
        MappingError: If paths are invalid or no test mapping can be found.
    """
    result: dict[Path, tuple[Path, ...]] = {}
    project_root = config.project_root
    for raw_source in sorted(set(sources)):
        path = resolve(project_root, raw_source, is_file_or_dir=True, label="source")
        if path.is_dir():
            root, test_root = _source_roots(path, config)
            relative = path.relative_to(root)
            target = resolve(
                project_root,
                test_root / relative,
                is_file_or_dir=True,
                label="test target",
            )
            result[path] = (target,)
            continue
        if path.suffix != ".py":
            msg = f"Source path is not a Python file: {path}"
            raise exc.MappingError(msg)

        explicit = config.test_paths.get(path)
        if explicit is not None:
            result[path] = tuple(
                resolve(project_root, target, is_file_or_dir=True, label="test target")
                for target in explicit
            )
            continue

        root, test_root = _source_roots(path, config)
        relative = path.relative_to(root)
        candidates = tuple(
            candidate
            for candidate in (
                test_root / relative.parent / f"test_{path.stem}.py",
                test_root / relative.parent / path.stem,
                test_root / relative.parent,
            )
            if candidate != test_root
        )
        mapped = next(
            (
                (target,)
                for candidate in candidates
                if (
                    target := resolve(
                        project_root,
                        candidate,
                        strict=False,
                        is_file_or_dir=True,
                        label="test target",
                    )
                )
            ),
            (),
        )
        if not mapped:
            candidates_text = ", ".join(str(candidate) for candidate in candidates)
            msg = (
                f"No test target found for source {path}; checked: "
                f"{candidates_text}. Configure [tool.coverage-isolate.test-paths] "
                "or [tool.coverage-isolate.test-roots]."
            )
            raise exc.MappingError(msg)
        result[path] = mapped
    return result


def expand_test_targets(
    targets: Iterable[Path],
    collected_test_files: Iterable[Path],
    root: Path,
) -> tuple[Path, ...]:
    """Expand test files/directories to paths that contain collected test items.

    Directory selections expand only to collected item file paths. Uncollected
    Python files and directories with no collected tests contribute nothing.

    Returns:
        Sorted, unique collected test-file paths.

    """
    collected = {
        resolve(root, path, is_file=True, label="collected test")
        for path in collected_test_files
    }
    expanded: set[Path] = set()
    for raw_target in targets:
        target = resolve(root, raw_target, is_file_or_dir=True, label="test target")
        if target.is_file():
            if target in collected:
                expanded.add(target)
        else:
            expanded.update(path for path in collected if path.is_relative_to(target))
    return tuple(sorted(expanded))


def _source_roots(source: Path, config: CoverageIsolateConfig) -> tuple[Path, Path]:
    """Choose the most specific matching source root and corresponding tests.

    Returns:
        The source root and its corresponding test root.

    Raises:
        MappingError: If no configured or conventional source root matches.
    """
    root = config.project_root
    configured = sorted(
        (
            (source_root, test_root)
            for source_root, test_root in config.test_roots.items()
            if source.is_relative_to(source_root)
        ),
        key=lambda pair: len(pair[0].parts),
        reverse=True,
    )
    if configured:
        return configured[0]

    roots: list[Path] = []
    for value in config.source or ():
        candidate = resolve(root, value, strict=False)
        if candidate and source.is_relative_to(candidate):
            roots.append(candidate)
    if roots:
        return max(roots, key=lambda path: len(path.parts)), root / "tests"
    default_root = root / "src"
    if source.is_relative_to(default_root):
        return default_root, root / "tests"
    msg = (
        f"No source root configured for {source}; set coverage run:source or "
        "[tool.coverage-isolate.test-roots]."
    )
    raise exc.MappingError(msg)
