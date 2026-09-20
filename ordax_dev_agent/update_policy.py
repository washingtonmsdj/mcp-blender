"""Helpers for safe managed-agent Git preflight checks."""
from __future__ import annotations

import argparse
import json
import subprocess
import os
from pathlib import Path
from typing import Any


def staged_index_check(
    repo: str | Path,
    *,
    timeout: int = 30,
) -> dict[str, Any]:
    """Compare the staged index tree with HEAD without scanning the worktree."""
    root = Path(repo).resolve()
    git = ["git", "-c", "core.fsmonitor=false", "-C", str(root)]

    try:
        index_tree = subprocess.run(
            [*git, "write-tree"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            shell=False,
        )
    except subprocess.TimeoutExpired as error:
        return {
            "ok": False,
            "clean": False,
            "error": f"git write-tree timed out after {error.timeout} seconds",
        }

    if index_tree.returncode != 0:
        return {
            "ok": False,
            "clean": False,
            "returncode": index_tree.returncode,
            "error": index_tree.stderr[-4000:],
        }

    try:
        head_tree = subprocess.run(
            [*git, "rev-parse", "HEAD^{tree}"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            shell=False,
        )
    except subprocess.TimeoutExpired as error:
        return {
            "ok": False,
            "clean": False,
            "error": f"HEAD tree lookup timed out after {error.timeout} seconds",
        }

    if head_tree.returncode != 0:
        return {
            "ok": False,
            "clean": False,
            "returncode": head_tree.returncode,
            "error": head_tree.stderr[-4000:],
        }

    index_sha = index_tree.stdout.strip().lower()
    head_sha = head_tree.stdout.strip().lower()
    if not index_sha or not head_sha:
        return {
            "ok": False,
            "clean": False,
            "error": "Git returned an empty tree hash",
        }

    return {
        "ok": True,
        "clean": index_sha == head_sha,
        "index_tree": index_sha,
        "head_tree": head_sha,
        "method": "index-tree-hash",
    }

def tracked_worktree_check(
    repo: str | Path,
    *,
    timeout: int = 60,
) -> dict[str, Any]:
    """Compare tracked worktree content with the index without refreshing it."""
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
            "returncode": listed.returncode,
            "error": listed.stderr.decode("utf-8", errors="replace")[-4000:],
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
            "returncode": hashed.returncode,
            "error": hashed.stderr.decode("utf-8", errors="replace")[-4000:],
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


def managed_repo_clean_check(
    repo: str | Path,
    *,
    worktree_timeout: int = 60,
    staged_timeout: int = 30,
) -> dict[str, Any]:
    worktree = tracked_worktree_check(repo, timeout=worktree_timeout)
    staged = staged_index_check(repo, timeout=staged_timeout)
    ok = bool(worktree.get("ok")) and bool(staged.get("ok"))
    clean = ok and bool(worktree.get("clean")) and bool(staged.get("clean"))
    return {
        "ok": ok,
        "clean": clean,
        "worktree": worktree,
        "staged": staged,
        "method": "index-object-hash+index-tree-hash",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-clean", metavar="REPO")
    args = parser.parse_args(argv)

    if not args.check_clean:
        parser.error("--check-clean is required")

    result = managed_repo_clean_check(args.check_clean)
    print(json.dumps(result, separators=(",", ":")))
    if not result.get("ok"):
        return 2
    return 0 if result.get("clean") else 1


if __name__ == "__main__":
    raise SystemExit(main())
