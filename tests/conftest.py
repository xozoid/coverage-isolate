from __future__ import annotations

import datetime as dt
import shutil
from collections.abc import Callable, Iterable
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest

if TYPE_CHECKING:
    from _pytest.fixtures import FixtureRequest


def pytest_make_parametrize_id(
    config: pytest.Config,
    val: Iterable[object] | Decimal | Path | object,
    argname: str,
) -> str | None:
    if isinstance(val, dt.date):
        return val.isoformat()
    if isinstance(val, Iterable):
        return str(cast("Iterable[object]", val))
    if isinstance(val, Decimal | Path):
        return str(val)
    if callable(val):
        return val.__name__
    return None


@pytest.fixture(scope="session")
def data_dir() -> Path:
    """Return the directory containing test data."""
    return Path(__file__).parent / "data"


@pytest.fixture
def project(tmp_path: Path, request: FixtureRequest, data_dir: Path) -> Path:
    """Copy the selected test data into a temporary project.

    Returns:
        The temporary project directory.
    """
    topic = request.path.stem.removeprefix("test_")
    default = request.node.name.removeprefix("test_")
    if topic == "config":
        default = default.removeprefix("load_config_")
    case = cast("str", getattr(request, "param", default))
    source = data_dir / topic / case
    if source.is_dir():
        shutil.copytree(source, tmp_path, dirs_exist_ok=True)
    else:
        shutil.copyfile(source.with_suffix(".toml"), tmp_path / "pyproject.toml")
    return tmp_path


@pytest.fixture
def project_tree(tmp_path: Path) -> Callable[..., tuple[Path, ...]]:
    """Create a project containing the requested files and directories.

    Returns:
        A factory for temporary project trees.
    """

    def create(
        *files: str,
        directories: tuple[str, ...] = (),
        root: Path | None = None,
    ) -> tuple[Path, ...]:
        project = root if root is not None else tmp_path / "project"
        project.mkdir(exist_ok=True)
        for directory in directories:
            (project / directory).mkdir(parents=True, exist_ok=True)
        for file in files:
            path = project / file
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
        return (project, *(project / file for file in files))

    return create
