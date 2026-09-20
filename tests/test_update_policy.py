from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from ordax_dev_agent.update_policy import (
    managed_repo_clean_check,
    staged_index_check,
    tracked_worktree_check,
)


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


class StagedIndexCheckTests(unittest.TestCase):
    def make_repo(self, root: Path) -> Path:
        repo = root / "repo"
        repo.mkdir()
        git(repo, "init", "-q", "-b", "main")
        git(repo, "config", "user.email", "tests@example.invalid")
        git(repo, "config", "user.name", "Tests")
        (repo / "tracked.txt").write_text("one\n", encoding="utf-8")
        git(repo, "add", "tracked.txt")
        git(repo, "commit", "-qm", "initial")
        return repo

    def test_clean_index_matches_head_tree(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = self.make_repo(Path(raw))
            result = staged_index_check(repo)
        self.assertTrue(result["ok"])
        self.assertTrue(result["clean"])
        self.assertEqual("index-tree-hash", result["method"])
        self.assertEqual(result["index_tree"], result["head_tree"])

    def test_staged_change_is_detected_without_worktree_diff(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = self.make_repo(Path(raw))
            (repo / "tracked.txt").write_text("two\n", encoding="utf-8")
            git(repo, "add", "tracked.txt")
            result = staged_index_check(repo)
        self.assertTrue(result["ok"])
        self.assertFalse(result["clean"])
        self.assertNotEqual(result["index_tree"], result["head_tree"])

    def test_unstaged_change_does_not_look_staged(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = self.make_repo(Path(raw))
            (repo / "tracked.txt").write_text("two\n", encoding="utf-8")
            result = staged_index_check(repo)
        self.assertTrue(result["ok"])
        self.assertTrue(result["clean"])

    def test_tracked_worktree_hash_detects_unstaged_change(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = self.make_repo(Path(raw))
            clean = tracked_worktree_check(repo)
            self.assertTrue(clean["ok"])
            self.assertTrue(clean["clean"])

            (repo / "tracked.txt").write_text("two\n", encoding="utf-8")
            changed = tracked_worktree_check(repo)

        self.assertTrue(changed["ok"])
        self.assertFalse(changed["clean"])
        self.assertIn("tracked.txt", changed["changed_paths"])
        self.assertEqual("index-object-hash", changed["method"])

    def test_managed_repo_clean_check_combines_both_guards(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = self.make_repo(Path(raw))
            clean = managed_repo_clean_check(repo)
            self.assertTrue(clean["ok"])
            self.assertTrue(clean["clean"])
            self.assertEqual(
                "index-object-hash+index-tree-hash",
                clean["method"],
            )

            (repo / "tracked.txt").write_text("two\n", encoding="utf-8")
            git(repo, "add", "tracked.txt")
            staged = managed_repo_clean_check(repo)

        self.assertTrue(staged["ok"])
        self.assertFalse(staged["clean"])
        self.assertTrue(staged["worktree"]["clean"])
        self.assertFalse(staged["staged"]["clean"])

    def test_unmerged_index_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = self.make_repo(Path(raw))
            git(repo, "checkout", "-qb", "other")
            (repo / "tracked.txt").write_text("other\n", encoding="utf-8")
            git(repo, "commit", "-am", "other")
            git(repo, "checkout", "-q", "main")
            (repo / "tracked.txt").write_text("master\n", encoding="utf-8")
            git(repo, "commit", "-am", "master")
            conflict = subprocess.run(
                ["git", "-C", str(repo), "merge", "other"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(0, conflict.returncode)
            result = staged_index_check(repo)
        self.assertFalse(result["ok"])
        self.assertFalse(result["clean"])


if __name__ == "__main__":
    unittest.main()
