"""Small shared path utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, overload


@overload
def resolve_path[T: type[Exception]](
    root: Path,
    path: Path | str,
    *,
    strict: Literal[False],
    is_file: bool = False,
    is_file_or_dir: bool = False,
    label: str = "source",
    exc_type: type[Exception] = Exception,
) -> Path | None: ...


@overload
def resolve_path[T: type[Exception]](
    root: Path,
    path: Path | str,
    *,
    strict: Literal[True] = True,
    is_file: bool = False,
    is_file_or_dir: bool = False,
    label: str = "source",
    exc_type: type[Exception] = Exception,
) -> Path: ...


def resolve_path[T: type[Exception]](  # ruff: ignore[too-many-arguments]
    root: Path,
    path: Path | str,
    *,
    strict: bool = True,
    is_file: bool = False,
    is_file_or_dir: bool = False,
    label: str = "source",
    exc_type: type[Exception] = Exception,
) -> Path | None:
    """Resolve a path relative to ``root`` when it is not absolute.

    Args:
        root: Base directory for relative paths.
        path: The path to resolve.
        strict: Whether the path must exist.
        is_file: Whether the resolved path must be a file.
        is_file_or_dir: Whether the resolved path must be a file or directory.
        label: Description used in error messages.
        exc_type: Exception type used for invalid paths.

    Returns:
        The absolute, resolved path, or None if it is missing and non-strict.

    Raises:
        Exception: The specified exception type if path validation fails.
    """  # ruff: ignore[docstring-extraneous-exception]
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        candidate = candidate.resolve(strict=strict)
    except OSError as error:
        msg = f"Could not resolve {label} path {root / path}: {error}"
        raise exc_type(msg) from error
    if not candidate.is_relative_to(root):
        msg = f"{label.title()} path resolves outside the project root: {path}"
        raise exc_type(msg)
    if not strict and not candidate.exists():
        return None
    if is_file and not candidate.is_file():
        msg = f"{label.title()} path is not a file: {path}"
        raise exc_type(msg)
    if is_file_or_dir and not (candidate.is_file() or candidate.is_dir()):
        msg = f"{label.title()} path is not a file nor directory: {path}"
        raise exc_type(msg)
    return candidate
