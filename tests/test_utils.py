from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from coverage_isolate.exceptions import SourceDiscoveryError
from coverage_isolate.utils import resolve_path

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def test_resolve_path_uses_root_for_relative_path(
    project_tree: Callable[..., tuple[Path, ...]],
) -> None:
    root, path = project_tree("source.py")
    resolved = resolve_path(root, "source.py")
    assert resolved == path.resolve()


def test_resolve_path_keeps_absolute_path(
    project_tree: Callable[..., tuple[Path, ...]],
) -> None:
    root, path = project_tree("source.py")
    resolved = resolve_path(root, path)
    assert resolved == path.resolve()


def test_resolve_path_allows_missing_path_when_non_strict(tmp_path: Path) -> None:
    path = tmp_path / "missing.py"
    resolved = resolve_path(tmp_path, path, strict=False)
    assert resolved == path


def test_resolve_path_requires_existing_path_by_default(tmp_path: Path) -> None:
    path = tmp_path / "missing.py"
    with pytest.raises(SourceDiscoveryError, match="Could not resolve source path"):
        resolve_path(tmp_path, path)


def test_resolve_path_rejects_path_outside_root(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    path = tmp_path / "outside.py"
    path.touch()

    with pytest.raises(SourceDiscoveryError, match="outside the project root"):
        resolve_path(root, path)


def test_resolve_path_uses_label_in_errors(tmp_path: Path) -> None:
    with pytest.raises(SourceDiscoveryError, match="Could not resolve config path"):
        resolve_path(tmp_path, "missing", label="config")
