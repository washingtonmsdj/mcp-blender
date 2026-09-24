"""Agent lifecycle and self-diagnostic typed actions."""
from __future__ import annotations

import json
import subprocess
import sys
from typing import Any

from .blender_live_bridge import BlenderLiveBridge
from .models import ActionResult
from .process_runner import run_command as _run
from .update_policy import install_contract_changed, managed_repo_clean_check
from .versioning import component_versions
from .capability_contracts import capability_contracts
from .component_updates import component_catalog, plan_component_update


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
                "product": {
                    "name": "OrdaX Device Agent",
                    "role": "typed-local-capability-runtime",
                    "legacy_runtime_name": "OrdaX Dev Agent",
                },
                "actions": self.names,
                "projects": [project.public() for project in self.projects.values()],
                "default_project": self.config.default_project,
                "busy": self._execution_lock.locked(),
                "versions": component_versions(),
                "capability_contracts": capability_contracts(),
                "components": component_catalog(),
                "live_apps": live_apps,
            },
        )

    def agent_resilience_status(self, payload: dict[str, Any]) -> ActionResult:
        unsupported = sorted(set(payload) - {"timeout_seconds"})
        if unsupported:
            return ActionResult(
                False,
                "unsupported field(s): " + ", ".join(unsupported),
            )

        if sys.platform != "win32":
            return ActionResult(
                False,
                "agent resilience status is available only on Windows",
            )

        try:
            timeout_seconds = int(payload.get("timeout_seconds", 15))
        except (TypeError, ValueError):
            return ActionResult(False, "timeout_seconds must be an integer")
        if timeout_seconds < 3 or timeout_seconds > 30:
            return ActionResult(
                False,
                "timeout_seconds must be between 3 and 30",
            )

        repo = self.config.agent_repo_path.resolve()
        script = repo / "scripts" / "windows" / "ordax-resilience-status.ps1"
        if not script.is_file():
            return ActionResult(
                False,
                f"resilience status script not found: {script}",
            )

        result = _run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script),
            ],
            cwd=repo,
            timeout=timeout_seconds,
        )
        if not result.ok:
            result.summary = "agent resilience status check failed"
            return result

        raw = result.data.get("stdout", "")
        try:
            status = json.loads(raw)
        except (TypeError, json.JSONDecodeError) as error:
            return ActionResult(
                False,
                "agent resilience status returned invalid JSON",
                {
                    "error": str(error),
                    "stdout_tail": str(raw)[-4000:],
                },
            )

        if not isinstance(status, dict):
            return ActionResult(
                False,
                "agent resilience status must return a JSON object",
            )

        return ActionResult(
            True,
            "agent resilience status ready",
            {"resilience": status},
        )

    def agent_resilience_repair(self, payload: dict[str, Any]) -> ActionResult:
        unsupported = sorted(set(payload) - {"timeout_seconds"})
        if unsupported:
            return ActionResult(
                False,
                "unsupported field(s): " + ", ".join(unsupported),
            )
        if sys.platform != "win32":
            return ActionResult(
                False,
                "agent resilience repair is available only on Windows",
            )

        try:
            timeout_seconds = int(payload.get("timeout_seconds", 30))
        except (TypeError, ValueError):
            return ActionResult(False, "timeout_seconds must be an integer")
        if timeout_seconds < 10 or timeout_seconds > 60:
            return ActionResult(
                False,
                "timeout_seconds must be between 10 and 60",
            )

        repo = self.config.agent_repo_path.resolve()
        installer = (
            repo
            / "scripts"
            / "windows"
            / "ordax-agent-bootstrap-install.ps1"
        )
        if not installer.is_file():
            return ActionResult(
                False,
                f"bootstrap installer not found: {installer}",
            )

        repair = _run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(installer),
                "-RepoRoot",
                str(repo),
                "-TaskName",
                "OrdaX Dev Agent",
                "-RetargetTask",
            ],
            cwd=repo,
            timeout=timeout_seconds,
        )
        if not repair.ok:
            repair.summary = "agent resilience task repair failed"
            return repair

        status = self.agent_resilience_status(
            {"timeout_seconds": min(timeout_seconds, 30)}
        )
        if not status.ok:
            status.summary = (
                "task repair completed, but resilience verification failed"
            )
            status.data["repair"] = repair.data
            return status

        resilience = status.data.get("resilience") or {}
        scheduled = resilience.get("scheduled_task") or {}
        triggers = scheduled.get("triggers") or []
        maintenance = [
            trigger
            for trigger in triggers
            if str(trigger.get("repetition_interval") or "")
        ]
        if not scheduled.get("exists") or len(triggers) < 2 or not maintenance:
            return ActionResult(
                False,
                "task repair did not produce the required recovery triggers",
                {
                    "repair": repair.data,
                    "resilience": resilience,
                },
            )

        return ActionResult(
            True,
            "agent resilience task repaired and verified",
            {
                "repair": repair.data,
                "resilience": resilience,
                "trigger_count": len(triggers),
                "maintenance_trigger_count": len(maintenance),
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

        # Avoid Git index/worktree refresh commands here. On the managed Windows
        # checkout both diff-files and diff-index have been observed to block for
        # tens of seconds. Compare tracked file content to the index and compare
        # the index tree to HEAD instead; both checks fail closed on ambiguity.
        preflight = managed_repo_clean_check(repo)
        if not preflight.get("ok"):
            return ActionResult(
                False,
                "managed agent tracked-change check failed",
                {"preflight": preflight},
            )
        if not preflight.get("clean"):
            worktree = preflight.get("worktree") or {}
            staged = preflight.get("staged") or {}
            return ActionResult(
                False,
                "managed agent has local tracked changes; update refused",
                {
                    "worktree_changed_paths": worktree.get("changed_paths", []),
                    "unstaged": not bool(worktree.get("clean")),
                    "staged": not bool(staged.get("clean")),
                    "preflight": preflight,
                },
            )

        before = _run([*git, "rev-parse", "HEAD"], timeout=20)
        if not before.ok:
            return before
        before_head = before.data.get("stdout", "").strip()

        fetch = _run(
            [
                *git,
                "fetch",
                "--quiet",
                "origin",
                f"refs/heads/{branch}:refs/remotes/origin/{branch}",
            ],
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
            def pyproject_at(commit: str) -> tuple[str | None, str | None]:
                try:
                    completed = subprocess.run(
                        [*git, "show", f"{commit}:pyproject.toml"],
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=30,
                        shell=False,
                    )
                except subprocess.TimeoutExpired as error:
                    return None, f"timed out after {error.timeout} seconds"
                if completed.returncode != 0:
                    return None, completed.stderr[-4000:]
                return completed.stdout, None

            before_pyproject, before_error = pyproject_at(before_head)
            after_pyproject, after_error = pyproject_at(after_head)
            if (
                before_error
                or after_error
                or before_pyproject is None
                or after_pyproject is None
            ):
                return ActionResult(
                    False,
                    "could not inspect agent install contract",
                    {
                        "before_error": before_error,
                        "after_error": after_error,
                    },
                )
            try:
                dependency_refresh = install_contract_changed(
                    before_pyproject,
                    after_pyproject,
                )
            except ValueError as error:
                return ActionResult(
                    False,
                    "could not parse agent install contract",
                    {"error": str(error)},
                )

        changed_paths: list[str] = []
        if before_head and after_head and before_head != after_head:
            changed = _run(
                [*git, "diff", "--name-only", before_head, after_head, "--"],
                timeout=30,
            )
            if not changed.ok:
                return ActionResult(
                    False,
                    "agent update could not classify changed components",
                    changed.data,
                )
            changed_paths = [
                line.strip()
                for line in changed.data.get("stdout", "").splitlines()
                if line.strip()
            ]
        update_plan = plan_component_update(
            changed_paths,
            install_contract_changed=dependency_refresh,
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
                "install_contract_changed": dependency_refresh,
                "tracked_check": "index-object-hash+index-tree-hash",
                "component_update_plan": update_plan,
            },
        )

