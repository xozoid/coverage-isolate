# coverage-isolate

[![CI][ci-badge]][ci] [![PyPI publishing][pypi-badge]][pypi-url]

## Overview

`coverage-isolate` is a Python package for reporting test coverage for selected source
files. The package implementation is still in progress.

## Development setup

Install Git, Python 3.12 or later, [uv](https://docs.astral.sh/uv/), Node.js 24 or later
with npm, and Vale. From the repository root, run:

```sh
tools/env.sh
```

The script synchronizes the locked Python dependencies, installs `prek` Git hooks,
installs Vale if it's missing (using a supported system package manager), downloads Vale
styles, installs npm dependencies with `npm ci`, and creates `.env` and `.env.leave` if
absent. They're for [`autoenv`](https://github.com/hyperupcall/autoenv): `.env`
activates the project virtual environment when you enter the repository, and
`.env.leave` deactivates it when you leave. Existing files stay in place.
`tools/env.sh --upgrade` first upgrades the Python lockfile, then syncs and performs the
same setup.

Common commands:

```sh
uv run pytest
uv run coverage run -m pytest
uv run coverage report
tools/linters.sh
tools/formatters.sh
uv run prek run --all-files
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for dependency updates, checks, and release
steps.

The project records the full upstream template commit used during adoption in
`.agents/skills/update-from-template/HISTORY.md`. Use the `update-from-template` skill
for later template updates; it preserves project-specific changes and updates the
history only after the migration and checks succeed. That file tracks the template
source, applied revision, and intentionally skipped changes.

## Releases

`hatch-vcs` uses setuptools-scm to derive versions from Git tags and history, including
development versions when a commit isn't exactly tagged. The configured `0.1.0` fallback
applies only if version detection fails. Publish a GitHub Release whose tag is a valid
version tag, optionally prefixed with `v` (for example, `v1.2.3`). Publishing the
release starts the publish workflow, which runs the CI workflow, builds the package, and
checks that the tag version matches the built package version. After validation, GitHub
Actions publishes to PyPI using trusted publishing. The workflow expects the
`coverage-isolate` PyPI project and a GitHub environment named `pypi`.

[ci]:
  https://github.com/xozoid/coverage-isolate/actions/workflows/ci.yml?query=branch%3Amain
[ci-badge]:
  https://github.com/xozoid/coverage-isolate/actions/workflows/ci.yml/badge.svg?branch=main
[pypi-badge]: https://img.shields.io/pypi/v/coverage-isolate.svg
[pypi-url]: https://pypi.org/project/coverage-isolate/
