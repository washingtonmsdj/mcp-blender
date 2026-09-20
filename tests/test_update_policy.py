import subprocess
import tempfile
import unittest
from pathlib import Path

from ordax_dev_agent.update_policy import (
    install_contract,
    install_contract_changed,
    tracked_worktree_check,
)


BASE = """
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "mcp-blender-unity"
version = "0.3.0"
requires-python = ">=3.11"
dependencies = [
  "mcp>=1.0.0,<2.0.0",
  "supabase>=2.18.0,<3.0.0",
]

[project.scripts]
ordax-dev-agent = "ordax_dev_agent.main:main"

[tool.setuptools.packages.find]
include = ["mcp_blender_unity*", "ordax_dev_agent*"]

[tool.setuptools.package-data]
ordax_dev_agent = ["assets/*.py", "assets/*.cs", "assets/*.json"]
"""


class AgentUpdatePolicyTests(unittest.TestCase):
    def git(self, root: Path, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            capture_output=True,
            text=True,
        )

    def make_repo(self, root: Path) -> Path:
        repo = root / "repo"
        repo.mkdir()
        self.git(repo, "init", "-q")
        self.git(repo, "config", "user.email", "tests@example.invalid")
        self.git(repo, "config", "user.name", "OrdaX Tests")
        self.git(repo, "config", "core.autocrlf", "false")
        (repo / "tracked.txt").write_text("alpha\n", encoding="utf-8")
        self.git(repo, "add", "tracked.txt")
        self.git(repo, "commit", "-q", "-m", "initial")
        return repo

    def test_version_and_package_data_do_not_force_reinstall(self) -> None:
        changed = BASE.replace('version = "0.3.0"', 'version = "0.4.0"').replace(
            '["assets/*.py", "assets/*.cs", "assets/*.json"]',
            '["assets/*.py", "assets/*.cs", "assets/*.json", "assets/*.toml"]',
        )
        self.assertFalse(install_contract_changed(BASE, changed))

    def test_dependency_change_requires_reinstall(self) -> None:
        changed = BASE.replace(
            '"supabase>=2.18.0,<3.0.0",',
            '"supabase>=2.18.0,<3.0.0",\n  "Pillow>=10,<12",',
        )
        self.assertTrue(install_contract_changed(BASE, changed))

    def test_entry_point_change_requires_reinstall(self) -> None:
        changed = BASE.replace(
            'ordax-dev-agent = "ordax_dev_agent.main:main"',
            'ordax-dev-agent = "ordax_dev_agent.bootstrap:main"',
        )
        self.assertTrue(install_contract_changed(BASE, changed))

    def test_build_backend_change_requires_reinstall(self) -> None:
        changed = BASE.replace(
            'build-backend = "setuptools.build_meta"',
            'build-backend = "other.backend"',
        )
        self.assertTrue(install_contract_changed(BASE, changed))

    def test_invalid_toml_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid pyproject"):
            install_contract("[project")

    def test_clean_tracked_worktree_matches_index(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = self.make_repo(Path(raw))
            result = tracked_worktree_check(repo)
        self.assertTrue(result["ok"])
        self.assertTrue(result["clean"])
        self.assertEqual([], result["changed_paths"])
        self.assertEqual("index-object-hash", result["method"])

    def test_modified_tracked_file_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = self.make_repo(Path(raw))
            (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
            result = tracked_worktree_check(repo)
        self.assertTrue(result["ok"])
        self.assertFalse(result["clean"])
        self.assertEqual(["tracked.txt"], result["changed_paths"])

    def test_deleted_tracked_file_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = self.make_repo(Path(raw))
            (repo / "tracked.txt").unlink()
            result = tracked_worktree_check(repo)
        self.assertTrue(result["ok"])
        self.assertFalse(result["clean"])
        self.assertEqual(["tracked.txt"], result["changed_paths"])

    def test_staged_change_matches_index_and_is_left_for_staged_check(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = self.make_repo(Path(raw))
            (repo / "tracked.txt").write_text("staged\n", encoding="utf-8")
            self.git(repo, "add", "tracked.txt")
            result = tracked_worktree_check(repo)
            staged = subprocess.run(
                ["git", "-C", str(repo), "diff-index", "--cached", "--quiet", "HEAD", "--"],
                check=False,
            )
        self.assertTrue(result["ok"])
        self.assertTrue(result["clean"])
        self.assertEqual(1, staged.returncode)

    def test_clean_filters_avoid_false_dirty_line_endings(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = root / "repo"
            repo.mkdir()
            self.git(repo, "init", "-q")
            self.git(repo, "config", "user.email", "tests@example.invalid")
            self.git(repo, "config", "user.name", "OrdaX Tests")
            (repo / ".gitattributes").write_text("*.txt text eol=lf\n", encoding="utf-8")
            (repo / "tracked.txt").write_bytes(b"alpha\r\n")
            self.git(repo, "add", ".gitattributes", "tracked.txt")
            self.git(repo, "commit", "-q", "-m", "line endings")
            (repo / "tracked.txt").write_bytes(b"alpha\r\n")
            result = tracked_worktree_check(repo)
        self.assertTrue(result["ok"])
        self.assertTrue(result["clean"])


if __name__ == "__main__":
    unittest.main()
