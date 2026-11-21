"""Configuration loading and validation."""

from __future__ import annotations

from coverage_isolate.config.loader import load_config
from coverage_isolate.config.types import CoverageIsolateConfig

__all__ = ["CoverageIsolateConfig", "load_config"]
