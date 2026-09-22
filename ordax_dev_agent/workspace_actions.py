"""Safe workspace binding and HORDAX project archiving actions."""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from .models import ActionResult
from .process_runner import run_command as _run


_SLUG_RE = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")
_FAMILY_RE = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")
_ALLOWED_APPS = frozenset({"blender", "unity"})
_SKIP_NAMES = frozenset({
    ".git",
    ".vs",
    ".idea",
    ".vscode",
    "__pycache__",
    "Library",
    "Temp",
    "Obj",
    "obj",
    "Build",
    "Builds",
    "Logs",
    "UserSettings",
    "MemoryCaptures",
    "Recordings",
    ".cache",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
})
_SKIP_SUFFIXES = (".blend1", ".blend2", ".blend@", ".tmp", ".temp")


def _load_settings(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("agent settings must be a JSON object")
    return data


def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(path)


def _copy_ignore(_directory: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    for name in names:
        if name in _SKIP_NAMES or name.endswith(_SKIP_SUFFIXES):
            ignored.add(name)
    return ignored


class WorkspaceActions:
    def workspace_list_projects(self, payload: dict[str, Any]) -> ActionResult:
        allowed = {"query", "max_depth", "max_entries"}
        unsupported = sorted(set(payload) - allowed)
        if unsupported:
            return ActionResult(False, "unsupported field(s): " + ", ".join(unsupported))

        query = str(payload.get("query") or "").strip().lower()
        max_depth = payload.get("max_depth", 3)
        max_entries = payload.get("max_entries", 200)
        if isinstance(max_depth, bool) or not isinstance(max_depth, int) or not (1 <= max_depth <= 5):
            return ActionResult(False, "max_depth must be an integer between 1 and 5")
        if isinstance(max_entries, bool) or not isinstance(max_entries, int) or not (1 <= max_entries <= 500):
            return ActionResult(False, "max_entries must be an integer between 1 and 500")

        root = self.config.hordax_path.resolve().parent
        if not root.is_dir():
            return ActionResult(False, f"GitHub workspace not found: {root}")

        entries: list[dict[str, Any]] = []
        queue: list[tuple[Path, int]] = [(root, 0)]
        while queue and len(entries) < max_entries:
            directory, depth = queue.pop(0)
            if depth >= max_depth:
                continue
            try:
                children = sorted(
                    (item for item in directory.iterdir() if item.is_dir()),
                    key=lambda item: item.name.lower(),
                )
            except OSError:
                continue
            for child in children:
                if child.name in _SKIP_NAMES or child.name.startswith("."):
                    continue
                rel = child.relative_to(root).as_posix()
                if query and query not in rel.lower() and query not in child.name.lower():
                    if depth + 1 < max_depth:
                        queue.append((child, depth + 1))
                    continue
                try:
                    blend_count = sum(1 for _ in child.glob("*.blend"))
                except OSError:
                    blend_count = 0
                entries.append(
                    {
                        "relative_path": rel,
                        "name": child.name,
                        "depth": depth + 1,
                        "is_git_repo": (child / ".git").exists(),
                        "blend_files_at_root": blend_count,
                    }
                )
                if len(entries) >= max_entries:
                    break
                if depth + 1 < max_depth:
                    queue.append((child, depth + 1))
            else:
                continue
            break

        return ActionResult(
            True,
            "GitHub workspace projects discovered",
            {
                "workspace_root": str(root),
                "query": query,
                "max_depth": max_depth,
                "entries": entries,
                "truncated": len(entries) >= max_entries,
            },
        )

    def workspace_bind_project(self, payload: dict[str, Any]) -> ActionResult:
        allowed = {
            "slug",
            "relative_path",
            "apps",
            "set_default",
            "blender_scripts_dir",
            "blend_file",
        }
        unsupported = sorted(set(payload) - allowed)
        if unsupported:
            return ActionResult(False, "unsupported field(s): " + ", ".join(unsupported))

        slug = str(payload.get("slug") or "").strip().lower()
        if not _SLUG_RE.fullmatch(slug):
            return ActionResult(False, "slug must match [a-z0-9][a-z0-9_-]{0,63}")

        raw_relative = payload.get("relative_path")
        if not isinstance(raw_relative, str) or not raw_relative.strip():
            return ActionResult(False, "relative_path is required")
        relative = Path(raw_relative.strip())
        if relative.is_absolute() or ".." in relative.parts:
            return ActionResult(False, "relative_path must stay inside the GitHub workspace")

        workspace_root = self.config.hordax_path.resolve().parent
        target = (workspace_root / relative).resolve()
        try:
            target.relative_to(workspace_root)
        except ValueError:
            return ActionResult(False, "project path escapes the GitHub workspace")
        if not target.is_dir():
            return ActionResult(False, f"project directory not found: {target}")

        apps = payload.get("apps", ["blender"])
        if (
            not isinstance(apps, list)
            or not apps
            or not all(isinstance(app, str) and app in _ALLOWED_APPS for app in apps)
        ):
            return ActionResult(False, "apps must be a non-empty list containing only blender/unity")

        set_default = payload.get("set_default", False)
        if not isinstance(set_default, bool):
            return ActionResult(False, "set_default must be boolean")

        blender_scripts_dir = payload.get("blender_scripts_dir", "automation/blender")
        if not isinstance(blender_scripts_dir, str) or not blender_scripts_dir.strip():
            return ActionResult(False, "blender_scripts_dir must be a non-empty string")
        scripts_rel = Path(blender_scripts_dir.strip())
        if scripts_rel.is_absolute() or ".." in scripts_rel.parts:
            return ActionResult(False, "blender_scripts_dir must stay inside the project")
        if "blender" in apps:
            (target / scripts_rel).mkdir(parents=True, exist_ok=True)

        blend_file = payload.get("blend_file")
        blender_config: dict[str, Any] = {"scripts_dir": scripts_rel.as_posix()}
        if blend_file is not None:
            if not isinstance(blend_file, str) or not blend_file.strip():
                return ActionResult(False, "blend_file must be a non-empty string")
            blend_rel = Path(blend_file.strip())
            if blend_rel.is_absolute() or ".." in blend_rel.parts:
                return ActionResult(False, "blend_file must stay inside the project")
            blend_path = (target / blend_rel).resolve()
            try:
                blend_path.relative_to(target)
            except ValueError:
                return ActionResult(False, "blend_file escapes the project")
            if not blend_path.is_file():
                return ActionResult(False, f"blend_file not found: {blend_path}")
            blender_config["blend_file"] = blend_rel.as_posix()

        settings_path = self.config.state_dir / "agent-settings.json"
        try:
            settings = _load_settings(settings_path)
        except Exception as error:
            return ActionResult(False, f"cannot read agent settings: {error}")

        projects = settings.get("projects")
        if projects is None:
            projects = {}
        if not isinstance(projects, dict):
            return ActionResult(False, "existing projects setting must be an object")

        projects[slug] = {
            "path": str(target),
            "apps": list(dict.fromkeys(apps)),
            "allowed_branches": [],
            "blender": blender_config if "blender" in apps else {},
            "unity": {},
        }
        settings["projects"] = projects
        if set_default:
            settings["default_project"] = slug

        try:
            _atomic_json_write(settings_path, settings)
        except Exception as error:
            return ActionResult(False, f"cannot write agent settings: {error}")

        return ActionResult(
            True,
            "GitHub workspace project bound",
            {
                "slug": slug,
                "project_path": str(target),
                "workspace_root": str(workspace_root),
                "apps": apps,
                "set_default": set_default,
                "restart_required": True,
            },
        )

    def project_archive_to_hordax(self, payload: dict[str, Any]) -> ActionResult:
        allowed = {"project", "family", "archive_slug", "message", "push"}
        unsupported = sorted(set(payload) - allowed)
        if unsupported:
            return ActionResult(False, "unsupported field(s): " + ", ".join(unsupported))

        project = self._project(payload)
        family = str(payload.get("family") or "projects").strip().lower()
        archive_slug = str(payload.get("archive_slug") or project.slug).strip().lower()
        if not _FAMILY_RE.fullmatch(family):
            return ActionResult(False, "family has invalid characters")
        if not _SLUG_RE.fullmatch(archive_slug):
            return ActionResult(False, "archive_slug has invalid characters")

        push = payload.get("push", True)
        if not isinstance(push, bool):
            return ActionResult(False, "push must be boolean")

        source = project.root.resolve()
        if source == self.config.hordax_path.resolve() or source.is_relative_to(self.config.hordax_path.resolve()):
            return ActionResult(False, "refusing to archive HORDAX-game into itself")

        archive_clone = self.config.state_dir / "project-archive" / "HORDAX-game"
        origin = _run(
            ["git", "-C", str(self.config.hordax_path), "remote", "get-url", "origin"],
            timeout=30,
        )
        if not origin.ok:
            return origin
        origin_url = origin.data.get("stdout", "").strip()
        if not origin_url:
            return ActionResult(False, "HORDAX-game origin URL is empty")

        if not (archive_clone / ".git").is_dir():
            archive_clone.parent.mkdir(parents=True, exist_ok=True)
            cloned = _run(
                ["git", "clone", "--branch", "main", "--single-branch", origin_url, str(archive_clone)],
                timeout=900,
            )
            if not cloned.ok:
                return cloned
        else:
            dirty = _run(["git", "-C", str(archive_clone), "status", "--porcelain"], timeout=60)
            if not dirty.ok:
                return dirty
            if dirty.data.get("stdout", "").strip():
                return ActionResult(
                    False,
                    "dedicated HORDAX archive clone is dirty; manual recovery required",
                    {"status": dirty.data.get("stdout", "")[-4000:]},
                )
            fetch = _run(["git", "-C", str(archive_clone), "fetch", "--quiet", "origin", "main"], timeout=300)
            if not fetch.ok:
                return fetch
            merge = _run(
                ["git", "-C", str(archive_clone), "merge", "--ff-only", "--quiet", "origin/main"],
                timeout=300,
            )
            if not merge.ok:
                return merge

        lfs = _run(["git", "lfs", "version"], timeout=30)
        if not lfs.ok:
            return ActionResult(False, "Git LFS is required for project archiving")

        destination_rel = Path("Projects") / family / archive_slug / "source"
        destination = archive_clone / destination_rel
        if destination.exists():
            shutil.rmtree(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copytree(source, destination, ignore=_copy_ignore)
        except Exception as error:
            return ActionResult(False, f"project archive copy failed: {type(error).__name__}: {error}")

        add = _run(
            ["git", "-C", str(archive_clone), "add", "--all", "--", destination_rel.as_posix()],
            timeout=600,
        )
        if not add.ok:
            return add

        staged = _run(
            ["git", "-C", str(archive_clone), "diff", "--cached", "--quiet", "--", destination_rel.as_posix()],
            timeout=120,
        )
        if staged.ok:
            return ActionResult(
                True,
                "project archive already current",
                {
                    "project": project.slug,
                    "archive_path": destination_rel.as_posix(),
                    "pushed": False,
                    "changed": False,
                },
            )

        message = payload.get("message")
        if not isinstance(message, str) or not message.strip():
            message = f"backup({archive_slug}): update project snapshot"

        commit = _run(
            ["git", "-C", str(archive_clone), "commit", "-m", message.strip(), "--", destination_rel.as_posix()],
            timeout=600,
        )
        if not commit.ok:
            return commit

        head = _run(["git", "-C", str(archive_clone), "rev-parse", "HEAD"], timeout=30)
        if not head.ok:
            return head

        if push:
            pushed = _run(["git", "-C", str(archive_clone), "push", "origin", "main"], timeout=1800)
            if not pushed.ok:
                return ActionResult(
                    False,
                    "project archive committed locally but push failed",
                    {
                        "commit": head.data.get("stdout", "").strip(),
                        "archive_path": destination_rel.as_posix(),
                        "push_error": pushed.data,
                    },
                )

        return ActionResult(
            True,
            "project archived to HORDAX-game",
            {
                "project": project.slug,
                "archive_path": destination_rel.as_posix(),
                "commit": head.data.get("stdout", "").strip(),
                "pushed": push,
                "changed": True,
            },
        )
