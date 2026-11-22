"""Small shared path utilities."""

from __future__ import annotations

from pathlib import Path

import coverage_isolate.exceptions as exc


def resolve_path(
    root: Path,
    path: Path | str,
    *,
    strict: bool = True,
    label: str = "source",
) -> Path:
    """Resolve a path relative to ``root`` when it is not absolute.

    Args:
        root: Base directory for relative paths.
        path: The path to resolve.
        strict: Whether the path must exist.
        label: Description used in error messages.

    Returns:
        The absolute, resolved path.

    Raises:
        SourceDiscoveryError: If the path cannot resolve or escapes the root.
    """
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        candidate = candidate.resolve(strict=strict)
    except OSError as error:
        msg = f"Could not resolve {label} path {root / path}: {error}"
        raise exc.SourceDiscoveryError(msg) from error
    if not candidate.is_relative_to(root):
        msg = f"{label.title()} path resolves outside the project root: {path}"
        raise exc.SourceDiscoveryError(msg)
    return candidate
