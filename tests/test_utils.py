from __future__ import annotations

import functools
import os
from typing import TYPE_CHECKING

import pytest

from coverage_isolate.utils import resolve_path

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


class Error(Exception):
    """Test error."""


resolve = functools.partial(resolve_path, exc_type=Error)


def test_resolve_path_uses_root_for_relative_path(
    project_tree: Callable[..., tuple[Path, ...]],
) -> None:
    root, path = project_tree("source.py")
    resolved = resolve(root, "source.py")
    assert resolved == path.resolve()


def test_resolve_path_keeps_absolute_path(
    project_tree: Callable[..., tuple[Path, ...]],
) -> None:
    root, path = project_tree("source.py")
    resolved = resolve(root, path)
    assert resolved == path.resolve()


def test_resolve_path_allows_missing_path_when_non_strict(tmp_path: Path) -> None:
    path = tmp_path / "missing.py"
    resolved = resolve(tmp_path, path, strict=False)
    assert resolved is None


def test_resolve_path_requires_existing_path_by_default(tmp_path: Path) -> None:
    path = tmp_path / "missing.py"
    with pytest.raises(Error, match="Could not resolve source path"):
        resolve(tmp_path, path, exc_type=Error)


def test_resolve_path_rejects_path_outside_root(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    path = tmp_path / "outside.py"
    path.touch()

    with pytest.raises(Error, match="outside the project root"):
        resolve(root, path)


def test_resolve_path_uses_label_in_errors(tmp_path: Path) -> None:
    with pytest.raises(Error, match="Could not resolve config path"):
        resolve(tmp_path, "missing", label="config")


def test_resolve_path_requires_file(tmp_path: Path) -> None:
    with pytest.raises(Error, match="not a file"):
        resolve(tmp_path, tmp_path, is_file=True)


def test_resolve_path_accepts_file_when_required(
    project_tree: Callable[..., tuple[Path, ...]],
) -> None:
    root, path = project_tree("test_example.py")
    assert resolve(root, path, is_file=True) == path


def test_resolve_path_requires_file_or_directory(tmp_path: Path) -> None:
    path = tmp_path / "pipe"
    os.mkfifo(path)
    with pytest.raises(Error, match="not a file nor directory"):
        resolve(tmp_path, path, is_file_or_dir=True)


def test_resolve_path_accepts_directory_when_required(tmp_path: Path) -> None:
    assert resolve(tmp_path, tmp_path, is_file_or_dir=True) == tmp_path
