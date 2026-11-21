"""Resolve source selections into deterministic Python source files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import coverage_isolate.exceptions as exc

if TYPE_CHECKING:
    from collections.abc import Iterable


@dataclass
class _Discovery:
    """State shared while resolving source selections."""

    root: Path
    source_roots: tuple[Path, ...]
    excluded: frozenset[str]
    discovered: set[Path] = field(default_factory=set)
    visited: set[Path] = field(default_factory=set)

    def walk(self, directory: Path) -> None:
        """Walk a source directory while validating every symlink target.

        Raises:
            SourceDiscoveryError: If a traversed path escapes allowed roots or
                cannot be read.
        """
        if directory in self.visited:
            return
        self.visited.add(directory)
        try:
            children = sorted(directory.iterdir())
        except OSError as error:
            msg = f"Could not read source directory {directory}: {error}"
            raise exc.SourceDiscoveryError(msg) from error
        for entry in children:
            child = _absolute(self.root, entry)
            self.validate(child)
            if child.is_dir():
                self.walk(child)
            elif child.suffix == ".py":
                self.add_source(child)

    def add_source(self, path: Path) -> None:
        """Validate and add one candidate source file.

        Raises:
            SourceDiscoveryError: If the candidate is outside allowed roots or
                is not a Python file.
        """
        if not path.is_file():
            msg = f"Source path is not a file: {path}"
            raise exc.SourceDiscoveryError(msg)
        if path.suffix != ".py":
            msg = f"Unsupported source file extension: {path}"
            raise exc.SourceDiscoveryError(msg)
        if path.name not in self.excluded:
            self.discovered.add(path)

    def validate(self, path: Path) -> None:
        """Validate the containment of a resolved path.

        Raises:
            SourceDiscoveryError: If the path is outside configured roots.
        """
        _validate_containment(self.root, path)
        if self.source_roots and not any(
            path.is_relative_to(root) for root in self.source_roots
        ):
            msg = f"Source path is outside configured source roots: {path}"
            raise exc.SourceDiscoveryError(msg)


def discover_sources(
    project_root: Path,
    selections: Iterable[str | Path] = (),
    *,
    source_roots: Iterable[str | Path] = (),
    exclude_files: Iterable[str] = (),
) -> tuple[Path, ...]:
    """Resolve source files and directories under a project root.

    Args:
        project_root: Root directory that source selections must remain within.
        selections: Absolute or project-relative Python files and directories.
            When omitted, the source roots are traversed.
        source_roots: Optional configured source directories. When supplied,
            every selection must be contained by one of these directories.
        exclude_files: File names to omit at any depth.

    Returns:
        Unique, absolute source paths sorted lexicographically.

    Invalid, missing, or out-of-root paths raise SourceDiscoveryError.
    """
    root = project_root.resolve()
    resolved_roots = tuple(_resolve_source_root(root, path) for path in source_roots)
    selected_paths = tuple(_absolute(root, path) for path in selections)
    discovery = _Discovery(root, resolved_roots, frozenset(exclude_files))
    for path in selected_paths or resolved_roots:
        discovery.validate(path)
        if path.is_dir():
            discovery.walk(path)
        else:
            discovery.add_source(path)
    return tuple(sorted(discovery.discovered))


def _absolute(project_root: Path, path: Path | str) -> Path:
    path = Path(path)
    path = path if path.is_absolute() else project_root / path
    try:
        path = path.resolve(strict=True)
    except OSError as error:
        msg = f"Could not resolve source path {path}: {error}"
        raise exc.SourceDiscoveryError(msg) from error
    return path


def _resolve_source_root(project_root: Path, source_root: Path | str) -> Path:
    """Resolve and validate one configured source directory.

    Returns:
        The resolved source directory.

    Raises:
        SourceDiscoveryError: If the root is missing, escapes the project, or
            is not a directory.
    """
    path = _absolute(project_root, source_root)
    _validate_containment(project_root, path)
    if not path.is_dir():
        msg = f"Configured source root is not a directory: {path}"
        raise exc.SourceDiscoveryError(msg)
    return path


def _validate_containment(project_root: Path, path: Path) -> None:
    """Resolve a path and ensure it remains inside the project root.

    Raises:
        SourceDiscoveryError: If the path cannot resolve or escapes the root.
    """
    if not path.is_relative_to(project_root):
        msg = f"Source path resolves outside the project root: {path}"
        raise exc.SourceDiscoveryError(msg)
