"""Agent lifecycle and self-diagnostic typed actions."""
from __future__ import annotations

import subprocess
import sys
from typing import Any

from .blender_live_bridge import BlenderLiveBridge
from .models import ActionResult
from .process_runner import run_command as _run
from .versioning import component_versions


class AgentActions:
    def agent_status(self, payload: dict[str, Any]) -> ActionResult:
        live_apps: dict[str, dict[str, Any]] = {}
        for slug, project in self.projects.items():
            if not project.root.is_dir():
                continue

            app_state: dict[str, Any] = {}
            if "unity" in project.apps:
                try:
                    app_state["unity"] = self._editor({"project": slug}).status()
                except Exception as error:
                    app_state["unity"] = {"presence_fresh": False, "error": str(error)}

            if "blender" in project.apps:
                try:
                    app_state["blender"] = BlenderLiveBridge(
                        self.config,
                        project,
                    ).status()
                except Exception as error:
                    app_state["blender"] = {"presence_fresh": False, "error": str(error)}

            if app_state:
                live_apps[slug] = app_state

        return ActionResult(
            True,
            "agent ready",
            {
                **self.config.public_status(),
                "actions": self.names,
                "projects": [project.public() for project in self.projects.values()],
                "default_project": self.config.default_project,
                "busy": self._execution_lock.locked(),
                "versions": component_versions(),
                "live_apps": live_apps,
            },
        )

    def agent_self_test(self, payload: dict[str, Any]) -> ActionResult:
        repo = self.config.agent_repo_path.resolve()
        tests_root = repo / "tests"
        if not tests_root.is_dir():
            return ActionResult(False, f"agent test suite not found: {tests_root}")

        compile_result = _run(
            [
                sys.executable,
                "-m",
                "compileall",
                "-q",
                "mcp_blender_unity",
                "ordax_dev_agent",
            ],
            cwd=repo,
            timeout=min(int(payload.get("compile_timeout_seconds", 120)), 300),
        )
        if not compile_result.ok:
            compile_result.summary = "agent Python compile check failed"
            return compile_result

        per_file_timeout = max(
            10,
            min(int(payload.get("per_test_file_timeout_seconds", 120)), 600),
        )
        test_files = sorted(tests_root.glob("test_*.py"))
        if not test_files:
            return ActionResult(False, "agent test suite contains no test_*.py files")

        test_runs: list[dict[str, Any]] = []
        for test_file in test_files:
            try:
                test_result = _run(
                    [
                        sys.executable,
                        "-m",
                        "unittest",
                        "discover",
                        "-s",
                        "tests",
                        "-p",
                        test_file.name,
                        "-v",
                    ],
                    cwd=repo,
                    timeout=per_file_timeout,
                )
            except subprocess.TimeoutExpired as error:
                return ActionResult(
                    False,
                    f"agent test file timed out: {test_file.name}",
                    {
                        "compile": compile_result.data,
                        "test_file": test_file.name,
                        "timeout_seconds": error.timeout,
                        "completed_test_files": test_runs,
                    },
                )

            test_runs.append(
                {
                    "file": test_file.name,
                    "ok": test_result.ok,
                    "returncode": test_result.data.get("returncode"),
                    "stdout": test_result.data.get("stdout", ""),
                    "stderr": test_result.data.get("stderr", ""),
                }
            )
            if not test_result.ok:
                return ActionResult(
                    False,
                    f"agent test file failed: {test_file.name}",
                    {
                        "compile": compile_result.data,
                        "tests": test_runs,
                    },
                )

        data = {
            "compile": compile_result.data,
            "test_files": test_runs,
            "test_file_count": len(test_runs),
        }

        if bool(payload.get("visual", False)):
            visual = _run(
                [sys.executable, "scripts/verify_visual_agent.py"],
                cwd=repo,
                timeout=int(payload.get("visual_timeout_seconds", 600)),
            )
            data["visual"] = visual.data
            if not visual.ok:
                return ActionResult(
                    False,
                    "agent tests passed, but real Blender visual smoke failed",
                    data,
                )

        return ActionResult(
            True,
            "agent compile, per-file tests, and requested visual smoke passed",
            data,
        )


    def agent_update(self, payload: dict[str, Any]) -> ActionResult:
        repo = self.config.agent_repo_path.resolve()
        if not (repo / ".git").is_dir():
            return ActionResult(False, f"managed agent repository not found: {repo}")

        branch = "main"
        git = ["git", "-c", "core.fsmonitor=false", "-C", str(repo)]

        def quiet_check(args: list[str], *, timeout: int = 20) -> tuple[int, str]:
            try:
                completed = subprocess.run(
                    [*git, *args],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=timeout,
                    shell=False,
                )
                return completed.returncode, completed.stderr[-4000:]
            except subprocess.TimeoutExpired as error:
                return 124, f"timed out after {error.timeout} seconds"

        # We only care about tracked edits. Avoid `git status` here: on some
        # Windows worktrees its index refresh can stall behind filesystem
        # monitors for minutes even with untracked scanning disabled.
        unstaged_rc, unstaged_error = quiet_check(["diff-files", "--quiet", "--"])
        staged_rc, staged_error = quiet_check(
            ["diff-index", "--cached", "--quiet", "HEAD", "--"]
        )
        if unstaged_rc not in (0, 1) or staged_rc not in (0, 1):
            return ActionResult(
                False,
                "managed agent tracked-change check failed",
                {
                    "unstaged_returncode": unstaged_rc,
                    "unstaged_error": unstaged_error,
                    "staged_returncode": staged_rc,
                    "staged_error": staged_error,
                },
            )
        if unstaged_rc == 1 or staged_rc == 1:
            changed = _run(
                [*git, "diff", "--name-status", "HEAD", "--"],
                timeout=30,
            )
            return ActionResult(
                False,
                "managed agent has local tracked changes; update refused",
                {
                    "status": changed.data.get("stdout", "") if changed.ok else "",
                    "unstaged": unstaged_rc == 1,
                    "staged": staged_rc == 1,
                },
            )

        before = _run([*git, "rev-parse", "HEAD"], timeout=20)
        if not before.ok:
            return before
        before_head = before.data.get("stdout", "").strip()

        fetch = _run(
            [*git, "fetch", "--quiet", "origin", branch],
            timeout=180,
        )
        if not fetch.ok:
            return fetch

        current = _run(
            [*git, "rev-parse", "--abbrev-ref", "HEAD"],
            timeout=20,
        )
        if not current.ok:
            return current

        if current.data.get("stdout", "").strip() != branch:
            checkout = _run(
                [*git, "checkout", "-B", branch, f"origin/{branch}"],
                timeout=120,
            )
            if not checkout.ok:
                return checkout
        else:
            merge = _run(
                [*git, "merge", "--ff-only", "--quiet", f"origin/{branch}"],
                timeout=120,
            )
            if not merge.ok:
                return merge

        head = _run([*git, "rev-parse", "HEAD"], timeout=20)
        if not head.ok:
            return ActionResult(
                False,
                "agent update completed but HEAD lookup failed",
                head.data,
            )

        after_head = head.data.get("stdout", "").strip()
        dependency_refresh = False

        if before_head and after_head and before_head != after_head:
            dependency_diff = subprocess.run(
                [
                    *git,
                    "diff",
                    "--quiet",
                    before_head,
                    after_head,
                    "--",
                    "pyproject.toml",
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
                shell=False,
            )
            if dependency_diff.returncode == 1:
                dependency_refresh = True
            elif dependency_diff.returncode not in (0, 1):
                return ActionResult(
                    False,
                    "could not determine whether agent dependencies changed",
                    {
                        "returncode": dependency_diff.returncode,
                        "stderr": dependency_diff.stderr[-4000:],
                    },
                )

        if dependency_refresh:
            install = _run(
                [sys.executable, "-m", "pip", "install", "-e", str(repo)],
                timeout=600,
            )
            if not install.ok:
                return install

        return ActionResult(
            True,
            "agent updated; restart required",
            {
                "branch": branch,
                "head": after_head,
                "restart_required": True,
                "dependencies_refreshed": dependency_refresh,
                "tracked_check": "diff-files+diff-index",
            },
        )

