"""Helpers for safe managed-agent Git preflight checks."""
from __future__ import annotations

import subprocess
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
