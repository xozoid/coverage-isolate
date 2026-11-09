---
name: release
description: >-
  Prepares and validates releases for this Python package. Use when planning,
  validating, or publishing a release, including version tags, distributions, GitHub
  Releases, or PyPI trusted publishing.
---

# Release preparation and validation

This project derives package versions from Git history and tags through hatch-vcs.
Review the release workflow in `.github/workflows/publish.yml` and current packaging
configuration before preparing a release.

- Confirm the intended source commit and release version. Create a valid version tag
  (optionally prefixed with `v`) only when explicitly authorized; the built package
  version must match the tag after removing that prefix.
- Run the relevant tests and coverage checks documented in `CONTRIBUTING.md`, then build
  distributions with `uv build`.
- Validate the distributions and confirm the version in package metadata matches the
  intended tag. Follow the existing validation in `.github/workflows/publish.yml`.
- Confirm the PyPI trusted publisher and `pypi` GitHub environment are configured for
  this repository and workflow before a release.
- GitHub Release creation, tag creation, package upload, and other publishing are
  external actions. Never create tags, publish releases, or upload packages without
  explicit user authorization.
