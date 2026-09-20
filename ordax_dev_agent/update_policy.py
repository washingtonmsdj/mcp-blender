"""Safe managed-agent update policy helpers."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import tomllib
from pathlib import Path
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


def tracked_worktree_check(
    repo: str | Path,
    *,
    timeout: int = 60,
) -> dict[str, Any]:
    """Compare working-tree file content with the index without refreshing it.

    git diff-files can spend a long time refreshing/stat-ing a Windows
    worktree. This check reads index object ids with ls-files --stage and
    asks hash-object --stdin-paths to hash tracked files with normal Git clean
    filters, including line-ending and attribute handling.
    """
    root = Path(repo).resolve()
    git = ["git", "-c", "core.fsmonitor=false", "-C", str(root)]

    try:
        listed = subprocess.run(
            [*git, "ls-files", "--stage", "-z"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            shell=False,
        )
    except subprocess.TimeoutExpired as error:
        return {
            "ok": False,
            "clean": False,
            "error": f"tracked file listing timed out after {error.timeout} seconds",
        }

    if listed.returncode != 0:
        return {
            "ok": False,
            "clean": False,
            "error": listed.stderr.decode("utf-8", errors="replace")[-4000:],
            "returncode": listed.returncode,
        }

    paths: list[bytes] = []
    expected: list[bytes] = []
    changed_paths: list[str] = []
    unsupported_paths: list[str] = []

    for record in listed.stdout.split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode, object_id, stage = metadata.split(b" ", 2)
        except ValueError:
            return {
                "ok": False,
                "clean": False,
                "error": "could not parse git ls-files --stage output",
            }

        display_path = os.fsdecode(raw_path)
        if stage != b"0":
            changed_paths.append(display_path)
            continue
        if mode not in {b"100644", b"100755"}:
            unsupported_paths.append(display_path)
            continue
        if b"\n" in raw_path or b"\r" in raw_path:
            unsupported_paths.append(display_path)
            continue

        candidate = root / display_path
        if not candidate.is_file():
            changed_paths.append(display_path)
            continue

        paths.append(raw_path)
        expected.append(object_id.lower())

    if unsupported_paths:
        return {
            "ok": False,
            "clean": False,
            "error": "tracked worktree contains unsupported path modes/names",
            "unsupported_paths": unsupported_paths[:100],
        }

    if changed_paths:
        return {
            "ok": True,
            "clean": False,
            "changed_paths": sorted(set(changed_paths))[:200],
            "method": "index-object-hash",
        }

    if not paths:
        return {
            "ok": True,
            "clean": True,
            "changed_paths": [],
            "tracked_files": 0,
            "method": "index-object-hash",
        }

    input_paths = b"\n".join(paths) + b"\n"
    try:
        hashed = subprocess.run(
            [*git, "hash-object", "--stdin-paths"],
            input=input_paths,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            shell=False,
        )
    except subprocess.TimeoutExpired as error:
        return {
            "ok": False,
            "clean": False,
            "error": f"tracked file hashing timed out after {error.timeout} seconds",
        }

    if hashed.returncode != 0:
        return {
            "ok": False,
            "clean": False,
            "error": hashed.stderr.decode("utf-8", errors="replace")[-4000:],
            "returncode": hashed.returncode,
        }

    actual = [
        line.strip().lower()
        for line in hashed.stdout.splitlines()
        if line.strip()
    ]
    if len(actual) != len(expected):
        return {
            "ok": False,
            "clean": False,
            "error": "tracked file hash count did not match index entry count",
            "expected_count": len(expected),
            "actual_count": len(actual),
        }

    for raw_path, expected_id, actual_id in zip(paths, expected, actual):
        if expected_id != actual_id:
            changed_paths.append(os.fsdecode(raw_path))

    return {
        "ok": True,
        "clean": not changed_paths,
        "changed_paths": sorted(set(changed_paths))[:200],
        "tracked_files": len(paths),
        "method": "index-object-hash",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-worktree", metavar="REPO")
    args = parser.parse_args(argv)

    if not args.check_worktree:
        parser.error("--check-worktree is required")

    result = tracked_worktree_check(args.check_worktree)
    print(json.dumps(result, separators=(",", ":")))
    if not result.get("ok"):
        return 2
    return 0 if result.get("clean") else 1


if __name__ == "__main__":
    raise SystemExit(main())
