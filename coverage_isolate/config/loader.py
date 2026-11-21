"""Load project configuration from ``pyproject.toml``."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from coverage_isolate.config.types import CoverageIsolateConfig

from coverage import Coverage
from coverage.exceptions import CoverageException

import coverage_isolate.exceptions as exc
from coverage_isolate.config.parsing import parse_config


def load_config(project_root: Path) -> CoverageIsolateConfig:
    """Load coverage-isolate settings from a project's ``pyproject.toml``.

    Args:
        project_root: Directory containing the consuming project's pyproject.toml.

    Returns:
        Validated settings with all configured paths resolved from project_root.

    Raises:
        ConfigurationError: If configuration values are invalid.

    """
    root = project_root.resolve()
    pyproject_path = root / "pyproject.toml"
    if not pyproject_path.is_file():
        msg = f"Project configuration not found: {pyproject_path}"
        raise exc.ConfigurationError(msg)

    try:
        with pyproject_path.open("rb") as file:
            document = tomllib.load(file)
    except (OSError, tomllib.TOMLDecodeError) as error:
        msg = f"Could not read {pyproject_path}: {error}"
        raise exc.ConfigurationError(msg) from error

    try:
        coverage = Coverage(config_file=str(pyproject_path))
        source = coverage.get_option("run:source")
        run_omit = coverage.get_option("run:omit")
        report_omit = coverage.get_option("report:omit")
    except (CoverageException, TypeError) as error:
        msg = f"Could not read coverage configuration from {pyproject_path}: {error}"
        raise exc.ConfigurationError(msg) from error

    return parse_config(root, document, source, run_omit, report_omit)
