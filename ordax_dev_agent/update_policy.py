"""Semantic install-contract comparison for managed agent updates."""
from __future__ import annotations

import tomllib
from typing import Any


_PROJECT_INSTALL_KEYS = (
    "requires-python",
    "dependencies",
    "optional-dependencies",
    "scripts",
    "gui-scripts",
    "entry-points",
    "dynamic",
)
_SETUPTOOLS_INSTALL_KEYS = (
    "package-dir",
    "packages",
    "py-modules",
)


def install_contract(pyproject_text: str) -> dict[str, Any]:
    try:
        data = tomllib.loads(pyproject_text)
    except (tomllib.TOMLDecodeError, TypeError) as error:
        raise ValueError(f"invalid pyproject.toml: {error}") from error

    project = data.get("project") or {}
    build_system = data.get("build-system") or {}
    setuptools = ((data.get("tool") or {}).get("setuptools") or {})

    return {
        "build-system": build_system,
        "project": {
            key: project[key]
            for key in _PROJECT_INSTALL_KEYS
            if key in project
        },
        "tool.setuptools": {
            key: setuptools[key]
            for key in _SETUPTOOLS_INSTALL_KEYS
            if key in setuptools
        },
    }


def install_contract_changed(before_text: str, after_text: str) -> bool:
    return install_contract(before_text) != install_contract(after_text)
