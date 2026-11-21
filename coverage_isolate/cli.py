# PYTHON_ARGCOMPLETE_OK
"""Command-line argument parsing for coverage-isolate."""

from __future__ import annotations

import argparse
import sys
from importlib import import_module
from pathlib import Path

import coverage_isolate.exceptions as exc
from coverage_isolate import __version__
from coverage_isolate.config import load_config


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser.

    Returns:
        The configured argument parser.
    """
    parser = argparse.ArgumentParser(
        prog="coverage-isolate",
        description="Run pytest and report coverage for selected source files.",
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "sources",
        metavar="SOURCE",
        nargs="*",
        help="source file or directory to measure",
    )
    parser.add_argument(
        "--per-file",
        action="store_true",
        help="attribute coverage to individual test files",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and report when coverage execution is unavailable.

    Args:
        argv: Arguments to parse, or None to use the process arguments.

    Returns:
        Exit status, where 2 indicates execution is unavailable or config is invalid.

    Raises:
        ModuleNotFoundError: If an installed completion dependency is missing.
    """
    parser = build_parser()
    try:
        argcomplete = import_module("argcomplete")
    except ModuleNotFoundError as error:
        if error.name != "argcomplete":
            raise
    else:
        argcomplete.autocomplete(parser)
    _ = parser.parse_args(argv)

    try:
        load_config(Path.cwd())
    except exc.ConfigurationError as error:
        sys.stderr.write(f"coverage-isolate: {error}\n")
        return 2

    sys.stderr.write("coverage-isolate execution is not implemented yet\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
