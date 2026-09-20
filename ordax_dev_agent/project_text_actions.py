"""Project-scoped UTF-8 text inspection and optimistic-concurrency writes.

These actions deliberately do not provide shell access. Reads/writes stay inside
an already registered local project, reject generated/cache directories, bound
file sizes, and require an exact SHA-256 precondition before replacing an
existing file.
"""
from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import Any

from .models import ActionResult


_READABLE_SUFFIXES = {
    ".asmdef", ".asmref", ".cginc", ".compute", ".cs", ".css", ".glsl",
    ".hlsl", ".html", ".json", ".md", ".shader", ".txt", ".uss", ".uxml",
    ".xml", ".yaml", ".yml",
    # Serialized Unity text may be inspected, but is intentionally not writable
    # through this generic action.
    ".unity", ".prefab", ".meta",
}
_WRITABLE_SUFFIXES = _READABLE_SUFFIXES - {".unity", ".prefab", ".meta"}
_ALLOWED_TOP_LEVEL = {"Assets", "Packages", "ProjectSettings", "automation", "docs"}
_BLOCKED_PARTS = {"Library", "Temp", "Logs", "Builds", "obj", ".git"}
_MAX_READ_BYTES = 2 * 1024 * 1024
_MAX_WRITE_BYTES = 1024 * 1024


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _relative_project_path(project, raw: str, *, must_exist: bool) -> tuple[Path, Path]:
    if not raw.strip():
        raise ValueError("path is required")
    path = project.path(raw.strip(), must_exist=must_exist)
    relative = path.relative_to(project.root.resolve())
    if not relative.parts:
        raise ValueError("path must identify a file inside the project")
    if relative.parts[0] not in _ALLOWED_TOP_LEVEL:
        raise ValueError(
            "text actions are limited to Assets, Packages, ProjectSettings, automation, or docs"
        )
    if any(part in _BLOCKED_PARTS for part in relative.parts):
        raise ValueError("path is inside a generated, build, cache, or repository-control directory")
    return path, relative


class ProjectTextActions:
    def project_text_read(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project(payload)
        raw = str(payload.get("path") or "")
        path, relative = _relative_project_path(project, raw, must_exist=True)

        if path.suffix.lower() not in _READABLE_SUFFIXES:
            return ActionResult(False, f"text file extension is not readable: {path.suffix or '<none>'}")
        if not path.is_file():
            return ActionResult(False, f"path is not a file: {relative.as_posix()}")

        data = path.read_bytes()
        if len(data) > _MAX_READ_BYTES:
            return ActionResult(
                False,
                f"text file is too large to read inline: {len(data)} > {_MAX_READ_BYTES}",
                {"path": relative.as_posix(), "size_bytes": len(data)},
            )

        has_bom = data.startswith(b"\xef\xbb\xbf")
        try:
            content = data.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            return ActionResult(False, f"file is not valid UTF-8 text: {error}")

        return ActionResult(
            True,
            "project text file ready",
            {
                "project": project.slug,
                "path": relative.as_posix(),
                "size_bytes": len(data),
                "sha256": _sha256(data),
                "encoding": "utf-8-sig" if has_bom else "utf-8",
                "content": content,
            },
        )

    def project_text_write(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project(payload)
        raw = str(payload.get("path") or "")
        content = payload.get("content")
        if not isinstance(content, str):
            return ActionResult(False, "content must be a string")

        path, relative = _relative_project_path(project, raw, must_exist=False)
        if path.suffix.lower() not in _WRITABLE_SUFFIXES:
            return ActionResult(
                False,
                f"text file extension is not writable: {path.suffix or '<none>'}",
            )

        existing = path.is_file()
        if path.exists() and not existing:
            return ActionResult(False, f"path exists and is not a file: {relative.as_posix()}")

        before_bytes = path.read_bytes() if existing else None
        before_sha = _sha256(before_bytes) if before_bytes is not None else None
        expected = str(payload.get("expected_sha256") or "").strip().lower()
        create = bool(payload.get("create", False))

        if existing:
            if not expected:
                return ActionResult(
                    False,
                    "expected_sha256 is required when replacing an existing file",
                    {"path": relative.as_posix(), "current_sha256": before_sha},
                )
            if expected != before_sha:
                return ActionResult(
                    False,
                    "text file changed since it was read; refusing stale overwrite",
                    {"path": relative.as_posix(), "expected_sha256": expected, "current_sha256": before_sha},
                )
        elif not create:
            return ActionResult(
                False,
                "file does not exist; set create=true to create a new text file",
                {"path": relative.as_posix()},
            )

        keep_bom = bool(before_bytes and before_bytes.startswith(b"\xef\xbb\xbf"))
        encoded = content.encode("utf-8-sig" if keep_bom else "utf-8")
        if len(encoded) > _MAX_WRITE_BYTES:
            return ActionResult(
                False,
                f"text content is too large to write: {len(encoded)} > {_MAX_WRITE_BYTES}",
                {"path": relative.as_posix(), "size_bytes": len(encoded)},
            )

        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(path.name + f".ordax-{uuid.uuid4().hex}.tmp")
        try:
            temp.write_bytes(encoded)
            if temp.read_bytes() != encoded:
                raise IOError("temporary file verification failed")
            temp.replace(path)
        finally:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass

        after_bytes = path.read_bytes()
        return ActionResult(
            True,
            "project text file written",
            {
                "project": project.slug,
                "path": relative.as_posix(),
                "created": not existing,
                "before_sha256": before_sha,
                "sha256": _sha256(after_bytes),
                "size_bytes": len(after_bytes),
                "encoding": "utf-8-sig" if keep_bom else "utf-8",
            },
        )
