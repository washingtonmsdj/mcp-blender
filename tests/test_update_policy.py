from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from ordax_dev_agent.update_policy import (
    install_contract,
    install_contract_changed,
    install_contract_changed_between_refs,
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


BASE_PYPROJECT = """
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


class InstallContractTests(unittest.TestCase):
    def test_version_and_package_data_do_not_force_reinstall(self) -> None:
        changed = BASE_PYPROJECT.replace(
            'version = "0.3.0"',
            'version = "0.4.0"',
        ).replace(
            '["assets/*.py", "assets/*.cs", "assets/*.json"]',
            '["assets/*.py", "assets/*.cs", "assets/*.json", "assets/*.txt"]',
        )
        self.assertFalse(install_contract_changed(BASE_PYPROJECT, changed))

    def test_dependency_change_requires_reinstall(self) -> None:
        changed = BASE_PYPROJECT.replace(
            '"supabase>=2.18.0,<3.0.0",',
            '"supabase>=2.18.0,<3.0.0",\n  "Pillow>=10,<12",',
        )
        self.assertTrue(install_contract_changed(BASE_PYPROJECT, changed))

    def test_entry_point_change_requires_reinstall(self) -> None:
        changed = BASE_PYPROJECT.replace(
            'ordax-dev-agent = "ordax_dev_agent.main:main"',
            'ordax-dev-agent = "ordax_dev_agent.bootstrap:main"',
        )
        self.assertTrue(install_contract_changed(BASE_PYPROJECT, changed))

    def test_build_backend_change_requires_reinstall(self) -> None:
        changed = BASE_PYPROJECT.replace(
            'build-backend = "setuptools.build_meta"',
            'build-backend = "other.backend"',
        )
        self.assertTrue(install_contract_changed(BASE_PYPROJECT, changed))

    def test_install_contract_ignores_release_metadata(self) -> None:
        contract = install_contract(BASE_PYPROJECT)
        self.assertNotIn("version", contract["project"])
        self.assertNotIn("package-data", contract["tool.setuptools"])

    def test_invalid_toml_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid pyproject"):
            install_contract("[project")


    def test_ref_comparison_uses_semantic_install_contract(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw) / "repo"
            repo.mkdir()
            git(repo, "init", "-q", "-b", "main")
            git(repo, "config", "user.email", "tests@example.invalid")
            git(repo, "config", "user.name", "Tests")

            (repo / "pyproject.toml").write_text(
                BASE_PYPROJECT,
                encoding="utf-8",
            )
            git(repo, "add", "pyproject.toml")
            git(repo, "commit", "-qm", "base")
            base = git(repo, "rev-parse", "HEAD").stdout.strip()

            version_only = BASE_PYPROJECT.replace(
                'version = "0.3.0"',
                'version = "0.3.1"',
            )
            (repo / "pyproject.toml").write_text(
                version_only,
                encoding="utf-8",
            )
            git(repo, "commit", "-am", "version")
            version_ref = git(repo, "rev-parse", "HEAD").stdout.strip()

            dependency = version_only.replace(
                '"supabase>=2.18.0,<3.0.0",',
                '"supabase>=2.18.0,<3.0.0",\n  "Pillow>=10,<12",',
            )
            (repo / "pyproject.toml").write_text(
                dependency,
                encoding="utf-8",
            )
            git(repo, "commit", "-am", "dependency")
            dependency_ref = git(repo, "rev-parse", "HEAD").stdout.strip()

            version_result = install_contract_changed_between_refs(
                repo,
                base,
                version_ref,
            )
            dependency_result = install_contract_changed_between_refs(
                repo,
                version_ref,
                dependency_ref,
            )

        self.assertTrue(version_result["ok"])
        self.assertFalse(version_result["changed"])
        self.assertTrue(dependency_result["ok"])
        self.assertTrue(dependency_result["changed"])

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
