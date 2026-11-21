"""Configuration types shared by the loader and parser."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class CoverageIsolateConfig:
    """Validated coverage-isolate settings with paths rooted at the project."""

    project_root: Path
    source: tuple[str, ...] | None
    run_omit: tuple[str, ...]
    report_omit: tuple[str, ...] | None
    test_roots: dict[Path, Path]
    test_paths: dict[Path, tuple[Path, ...]]
