from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from coverage_isolate.discovery import discover_sources
from coverage_isolate.exceptions import SourceDiscoveryError

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator


def test_discover_sources_accepts_individual_file(
    project_tree: Callable[..., tuple[Path, ...]],
) -> None:
    project, source = project_tree("src/one.py")
    result = discover_sources(project, ["src/one.py"])
    assert result == (source,)


def test_discover_sources_recurses_and_sorts_directory(
    project_tree: Callable[..., tuple[Path, ...]],
) -> None:
    project, nested_source, top_source = project_tree(
        "src/nested/z.py",
        "src/a.py",
    )
    result = discover_sources(project, ["src"])
    assert result == (top_source, nested_source)


def test_discover_sources_deduplicates_overlapping_selections(
    project_tree: Callable[..., tuple[Path, ...]],
) -> None:
    project, source = project_tree("src/one.py")
    result = discover_sources(project, ["src", source])
    assert result == (source,)


def test_discover_sources_excludes_file_names(
    project_tree: Callable[..., tuple[Path, ...]],
) -> None:
    project, kept, _ = project_tree("src/keep.py", "src/skip.py")
    result = discover_sources(project, [project / "src"], exclude_files=["skip.py"])
    assert result == (kept,)


def test_discover_sources_accepts_empty_directory(
    project_tree: Callable[..., tuple[Path, ...]],
) -> None:
    (project,) = project_tree(directories=("empty",))
    result = discover_sources(project, [project / "empty"])
    assert result == ()


def test_discover_sources_skips_non_python_files_in_directories(
    project_tree: Callable[..., tuple[Path, ...]],
) -> None:
    project, module, _ = project_tree("src/module.py", "src/readme.txt")
    result = discover_sources(project, [project / "src"])
    assert result == (module,)


def test_discover_sources_traverses_multiple_roots_by_default(
    project_tree: Callable[..., tuple[Path, ...]],
) -> None:
    project, first_file, second_file = project_tree("src_a/a.py", "src_b/b.py")
    result = discover_sources(
        project,
        source_roots=[project / "src_a", project / "src_b"],
    )
    assert result == (first_file, second_file)


def test_discover_sources_deduplicates_overlapping_roots(
    project_tree: Callable[..., tuple[Path, ...]],
) -> None:
    project, source = project_tree("src/nested/module.py")
    parent = project / "src"
    child = parent / "nested"

    result = discover_sources(
        project,
        source_roots=[parent, child],
    )
    assert result == (source,)


def test_discover_sources_rejects_selection_outside_source_roots(
    project_tree: Callable[..., tuple[Path, ...]],
) -> None:
    project, source = project_tree("other.py", directories=("src",))
    with pytest.raises(SourceDiscoveryError, match="outside configured source roots"):
        discover_sources(project, [source], source_roots=[project / "src"])


def test_discover_sources_rejects_internal_symlink_outside_source_roots(
    project_tree: Callable[..., tuple[Path, ...]],
) -> None:
    project, target = project_tree("other/module.py", directories=("src",))
    source_root = project / "src"
    (source_root / "linked.py").symlink_to(target)

    with pytest.raises(SourceDiscoveryError, match="outside configured source roots"):
        discover_sources(project, source_roots=[source_root])


@pytest.mark.parametrize("selection", ["missing.py", "missing"])
def test_discover_sources_rejects_missing_path(
    project_tree: Callable[..., tuple[Path, ...]],
    selection: str,
) -> None:
    (project,) = project_tree()
    with pytest.raises(SourceDiscoveryError, match="Could not resolve source path"):
        discover_sources(project, [selection])


def test_discover_sources_rejects_non_python_file(
    project_tree: Callable[..., tuple[Path, ...]],
) -> None:
    project, source = project_tree("data.txt")
    with pytest.raises(SourceDiscoveryError, match="Unsupported source file extension"):
        discover_sources(project, [source])


def test_discover_sources_rejects_root_escape(
    project_tree: Callable[..., tuple[Path, ...]],
    tmp_path: Path,
) -> None:
    (project,) = project_tree()
    outside = tmp_path / "outside.py"
    outside.touch()
    with pytest.raises(SourceDiscoveryError, match="outside the project root"):
        discover_sources(project, [outside])


def test_discover_sources_rejects_symlink_escape(
    project_tree: Callable[..., tuple[Path, ...]],
    tmp_path: Path,
) -> None:
    (project,) = project_tree()
    outside = tmp_path / "outside.py"
    outside.touch()
    linked = project / "linked.py"
    linked.symlink_to(outside)

    with pytest.raises(SourceDiscoveryError, match="outside the project root"):
        discover_sources(project, [linked])


def test_discover_sources_rejects_nested_directory_symlink_escape(
    project_tree: Callable[..., tuple[Path, ...]],
    tmp_path: Path,
) -> None:
    (project,) = project_tree(directories=("src",))
    source_root = project / "src"
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "module.py").touch()
    (source_root / "linked").symlink_to(outside, target_is_directory=True)

    with pytest.raises(SourceDiscoveryError, match="outside the project root"):
        discover_sources(project, source_roots=[source_root])


def test_discover_sources_rejects_invalid_source_root(
    project_tree: Callable[..., tuple[Path, ...]],
) -> None:
    (project,) = project_tree()
    with pytest.raises(SourceDiscoveryError, match="Could not resolve source path"):
        discover_sources(project, source_roots=["missing"])


def test_discover_sources_rejects_file_as_source_root(
    project_tree: Callable[..., tuple[Path, ...]],
) -> None:
    project, source = project_tree("module.py")
    with pytest.raises(SourceDiscoveryError, match="not a directory"):
        discover_sources(project, source_roots=[source])


def test_discover_sources_reports_directory_read_error(
    project_tree: Callable[..., tuple[Path, ...]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (project,) = project_tree(directories=("src",))
    source = project / "src"
    original_iterdir = Path.iterdir

    def fail_on_source_directory(path: Path) -> Iterator[Path]:
        if path == source:
            msg = "access denied"
            raise PermissionError(msg)
        return original_iterdir(path)

    monkeypatch.setattr(Path, "iterdir", fail_on_source_directory)

    with pytest.raises(SourceDiscoveryError, match="Could not read source directory"):
        discover_sources(project, [source])


def test_discover_sources_reports_broken_symlink_during_traversal(
    project_tree: Callable[..., tuple[Path, ...]],
) -> None:
    (project,) = project_tree(directories=("src",))
    source = project / "src"
    (source / "broken.py").symlink_to(project / "missing.py")

    with pytest.raises(SourceDiscoveryError, match="Could not resolve source path"):
        discover_sources(project, [source])


def test_discover_sources_rejects_non_file_python_selection(
    project_tree: Callable[..., tuple[Path, ...]],
) -> None:
    (project,) = project_tree()
    source = project / "module.py"
    os.mkfifo(source)

    with pytest.raises(SourceDiscoveryError, match="is not a file"):
        discover_sources(project, [source])
