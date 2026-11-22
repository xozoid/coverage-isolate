from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from coverage_isolate.config.types import CoverageIsolateConfig
from coverage_isolate.exceptions import MappingError
from coverage_isolate.mapping import expand_test_targets, map_sources_to_tests

if TYPE_CHECKING:
    from collections.abc import Callable


def _config(
    root: Path,
    *,
    roots: dict[Path, Path] | None = None,
    paths: dict[Path, tuple[Path, ...]] | None = None,
    source: tuple[str, ...] | None = None,
) -> CoverageIsolateConfig:
    return CoverageIsolateConfig(
        project_root=root,
        source=source,
        run_omit=(),
        report_omit=None,
        test_roots=roots or {},
        test_paths=paths or {},
    )


def _touch(root: Path, relative: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    return path.resolve()


def test_explicit_targets_override_convention_and_support_multiple(
    tmp_path: Path,
) -> None:
    source = _touch(tmp_path, "pkg/api.py")
    conventional = _touch(tmp_path, "tests/test_api.py")
    first = _touch(tmp_path, "tests/custom_api.py")
    second = _touch(tmp_path, "tests/integration_api.py")
    config = _config(tmp_path, paths={source: (first, second)})

    assert map_sources_to_tests([source], config) == {source: (first, second)}
    assert conventional.exists()


def test_uses_most_specific_configured_source_root(tmp_path: Path) -> None:
    source = _touch(tmp_path, "pkg/nested/feature.py")
    nested_test = _touch(tmp_path, "tests/test_feature.py")
    _touch(tmp_path, "tests/pkg/nested/test_feature.py")
    config = _config(
        tmp_path,
        roots={
            (tmp_path / "pkg").resolve(): (tmp_path / "tests/pkg").resolve(),
            (tmp_path / "pkg/nested").resolve(): (tmp_path / "tests").resolve(),
        },
    )

    assert map_sources_to_tests([source], config)[source] == (nested_test,)


def test_conventional_mapping_tries_file_then_directory_candidates(
    tmp_path: Path,
) -> None:
    source = _touch(tmp_path, "pkg/_impl/codec.py")
    matching_directory = tmp_path / "tests/_impl/codec"
    matching_directory.mkdir(parents=True)
    config = _config(tmp_path, source=("pkg",))

    assert map_sources_to_tests([source], config)[source] == (matching_directory,)


def test_does_not_fall_back_to_entire_test_root(tmp_path: Path) -> None:
    source = _touch(tmp_path, "pkg/api.py")
    (tmp_path / "tests").mkdir()
    config = _config(tmp_path, source=("pkg",))

    with pytest.raises(MappingError, match="No test target found") as error:
        map_sources_to_tests([source], config)
    assert f"{tmp_path}/tests, " not in str(error.value)


def test_source_directory_maps_to_nested_test_directory(tmp_path: Path) -> None:
    source = _touch(tmp_path, "pkg/_impl/codec.py")
    test_dir = tmp_path / "tests/_impl"
    test_dir.mkdir(parents=True)
    config = _config(tmp_path, source=("pkg",))

    assert map_sources_to_tests([source], config)[source] == (test_dir.resolve(),)


def test_selected_source_root_maps_directly_to_test_root(tmp_path: Path) -> None:
    source_root = tmp_path / "src"
    source_root.mkdir()
    test_root = tmp_path / "tests"
    test_root.mkdir()
    config = _config(tmp_path, source=("src",))

    assert map_sources_to_tests([source_root], config) == {
        source_root.resolve(): (test_root.resolve(),),
    }


def test_selected_nested_directory_maps_to_matching_test_directory(
    tmp_path: Path,
) -> None:
    source_directory = tmp_path / "src/package/features"
    source_directory.mkdir(parents=True)
    test_directory = tmp_path / "tests/package/features"
    test_directory.mkdir(parents=True)
    config = _config(
        tmp_path,
        roots={
            (tmp_path / "src").resolve(): (tmp_path / "tests").resolve(),
        },
    )

    assert map_sources_to_tests([source_directory], config)[
        source_directory.resolve()
    ] == (test_directory.resolve(),)


def test_expand_directory_targets_to_collected_test_files(tmp_path: Path) -> None:
    selected = _touch(tmp_path, "tests/unit/test_one.py")
    nested = _touch(tmp_path, "tests/unit/nested/test_two.py")
    unrelated = _touch(tmp_path, "tests/other/test_three.py")
    uncollected = _touch(tmp_path, "tests/unit/helper.py")

    result = expand_test_targets(
        [tmp_path / "tests/unit"],
        [selected, nested, unrelated],
        tmp_path,
    )

    assert result == tuple(sorted((selected, nested)))
    assert uncollected not in result


def test_expand_targets_deduplicates_files_and_directories(tmp_path: Path) -> None:
    test_file = _touch(tmp_path, "tests/test_api.py")

    assert expand_test_targets(
        [tmp_path / "tests", test_file],
        [test_file],
        tmp_path,
    ) == (test_file,)


def test_expand_targets_omits_uncollected_file(tmp_path: Path) -> None:
    target = _touch(tmp_path, "tests/test_api.py")

    assert expand_test_targets([target], [], tmp_path) == ()


def test_expand_targets_rejects_collected_file_outside_project(
    tmp_path: Path,
) -> None:
    outside = tmp_path.parent / "test_outside.py"
    outside.touch()

    with pytest.raises(MappingError, match="outside the project root"):
        expand_test_targets([], [outside], tmp_path)


def test_expand_targets_rejects_collected_directory(tmp_path: Path) -> None:
    directory = tmp_path / "tests"
    directory.mkdir()

    with pytest.raises(MappingError, match="Collected Test path is not a file"):
        expand_test_targets([], [directory], tmp_path)


def test_reports_missing_source_root_and_configuration(tmp_path: Path) -> None:
    source = _touch(tmp_path, "package/api.py")

    with pytest.raises(MappingError, match="No source root configured") as error:
        map_sources_to_tests([source], _config(tmp_path))

    assert "coverage run:source" in str(error.value)


def test_uses_default_src_root_when_coverage_source_does_not_match(
    tmp_path: Path,
) -> None:
    source = _touch(tmp_path, "src/example.py")
    target = _touch(tmp_path, "tests/test_example.py")

    assert map_sources_to_tests([source], _config(tmp_path, source=("other",)))[
        source
    ] == (target,)


def test_reports_unmatched_coverage_source_root(tmp_path: Path) -> None:
    source = _touch(tmp_path, "package/api.py")

    with pytest.raises(MappingError, match="No source root configured"):
        map_sources_to_tests([source], _config(tmp_path, source=("other",)))


def test_rejects_unsupported_source_file(tmp_path: Path) -> None:
    source = _touch(tmp_path, "src/data.txt")

    with pytest.raises(MappingError, match="not a Python file"):
        map_sources_to_tests([source], _config(tmp_path, source=("src",)))


def test_rejects_special_file_as_test_target(tmp_path: Path) -> None:
    source = _touch(tmp_path, "src/example.py")
    target = tmp_path / "tests/test_example.py"
    target.parent.mkdir()
    os.mkfifo(target)

    with pytest.raises(MappingError, match="not a file nor directory"):
        map_sources_to_tests([source], _config(tmp_path, paths={source: (target,)}))


@pytest.mark.parametrize("invalid", ["missing.py", "outside.py"])
def test_explicit_mapping_rejects_invalid_targets(tmp_path: Path, invalid: str) -> None:
    source = _touch(tmp_path, "pkg/api.py")
    target = (tmp_path / invalid) if invalid == "missing.py" else Path("/outside.py")
    config = _config(tmp_path, paths={source: (target,)})

    with pytest.raises(MappingError):
        map_sources_to_tests([source], config)


def test_rejects_source_outside_project(tmp_path: Path) -> None:
    source = _touch(tmp_path, "pkg/api.py")
    outside = tmp_path.parent / "outside.py"
    outside.touch()

    with pytest.raises(MappingError, match="outside the project root"):
        map_sources_to_tests([outside], _config(tmp_path))
    assert source.exists()


def test_conventional_mapping_does_not_mask_unsafe_test_root(
    project_tree: Callable[..., tuple[Path, ...]],
) -> None:
    project, source = project_tree("pkg/api.py", directories=("tests",))
    config = _config(
        project,
        roots={(project / "pkg").resolve(): Path("/outside")},
    )

    with pytest.raises(MappingError, match="outside the project root"):
        map_sources_to_tests([source], config)
