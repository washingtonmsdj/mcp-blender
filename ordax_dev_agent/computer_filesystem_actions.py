"""Device-scoped filesystem capabilities with local allow-root policy.

These actions intentionally complement project-scoped workspace tools. Remote callers
still require per-action Product grants, while the local policy decides which parts of
this computer can ever be reached through the device boundary.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import ActionResult


_MAX_TEXT_BYTES = 8 * 1024 * 1024
_MAX_INLINE_BYTES = 512 * 1024
_MAX_WRITE_BYTES = 8 * 1024 * 1024
_MAX_LIST_ENTRIES = 5000
_MAX_SEARCH_RESULTS = 500
_SKIP_SEARCH_DIRS = frozenset(
    {
        ".git",
        ".svn",
        ".hg",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".venv",
        "venv",
        "node_modules",
        "site-packages",
        "AppData",
        "$Recycle.Bin",
        "System Volume Information",
    }
)


@dataclass(frozen=True)
class ComputerAccessPolicy:
    enabled: bool
    full_filesystem: bool
    allowed_roots: tuple[Path, ...]

    def public(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "full_filesystem": self.full_filesystem,
            "allowed_roots": [str(root) for root in self.allowed_roots],
            "relative_paths_base": str(Path.home().resolve()),
        }


def _bool_env(name: str) -> bool | None:
    raw = os.environ.get(name)
    if raw is None:
        return None
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean")


def load_computer_access_policy(config) -> ComputerAccessPolicy:
    settings_path = config.state_dir / "agent-settings.json"
    settings: dict[str, Any] = {}
    if settings_path.is_file():
        loaded = json.loads(settings_path.read_text(encoding="utf-8-sig"))
        if not isinstance(loaded, dict):
            raise ValueError("agent settings must be a JSON object")
        settings = loaded

    section = settings.get("computer_access", {})
    if section is None:
        section = {}
    if not isinstance(section, dict):
        raise ValueError("computer_access must be an object")

    enabled = section.get("enabled", True)
    full_filesystem = section.get("full_filesystem", False)
    if not isinstance(enabled, bool):
        raise ValueError("computer_access.enabled must be boolean")
    if not isinstance(full_filesystem, bool):
        raise ValueError("computer_access.full_filesystem must be boolean")

    env_enabled = _bool_env("ORDAX_COMPUTER_ACCESS_ENABLED")
    env_full = _bool_env("ORDAX_COMPUTER_FULL_FILESYSTEM")
    if env_enabled is not None:
        enabled = env_enabled
    if env_full is not None:
        full_filesystem = env_full

    raw_roots = section.get("allowed_roots")
    env_roots = os.environ.get("ORDAX_COMPUTER_ALLOWED_ROOTS")
    if env_roots is not None:
        raw_roots = [item for item in env_roots.split(os.pathsep) if item.strip()]
    if raw_roots is None:
        raw_roots = [str(Path.home())]
    if (
        not isinstance(raw_roots, list)
        or len(raw_roots) > 32
        or not all(isinstance(item, str) and item.strip() for item in raw_roots)
    ):
        raise ValueError("computer_access.allowed_roots must be a list of at most 32 paths")

    roots: list[Path] = []
    seen: set[str] = set()
    for raw in raw_roots:
        root = Path(raw).expanduser()
        if not root.is_absolute():
            raise ValueError(f"computer access root must be absolute: {raw}")
        resolved = root.resolve()
        key = os.path.normcase(str(resolved))
        if key not in seen:
            seen.add(key)
            roots.append(resolved)

    if enabled and not full_filesystem and not roots:
        raise ValueError("computer access needs at least one allowed root unless full_filesystem=true")

    return ComputerAccessPolicy(
        enabled=enabled,
        full_filesystem=full_filesystem,
        allowed_roots=tuple(roots),
    )


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _bounded_int(
    value: Any,
    *,
    default: int,
    minimum: int,
    maximum: int,
    name: str,
) -> int:
    try:
        parsed = int(default if value is None else value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be an integer") from error
    if not minimum <= parsed <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return parsed


def _path_allowed(path: Path, policy: ComputerAccessPolicy) -> bool:
    if policy.full_filesystem:
        return True
    for root in policy.allowed_roots:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            continue
    return False


class ComputerFilesystemActions:
    def _computer_access_policy(self) -> ComputerAccessPolicy:
        return load_computer_access_policy(self.config)

    def _computer_path(
        self,
        raw: Any,
        *,
        must_exist: bool,
    ) -> tuple[Path, ComputerAccessPolicy]:
        if not isinstance(raw, str) or not raw.strip() or "\x00" in raw:
            raise ValueError("path is required")
        if len(raw) > 32768:
            raise ValueError("path is too long")

        policy = self._computer_access_policy()
        if not policy.enabled:
            raise PermissionError("computer access is disabled in local ORDAX settings")

        candidate = Path(raw.strip()).expanduser()
        if not candidate.is_absolute():
            candidate = Path.home() / candidate
        resolved = candidate.resolve(strict=False)
        if not _path_allowed(resolved, policy):
            raise PermissionError("path is outside local ORDAX computer access roots")
        if must_exist and not resolved.exists():
            raise FileNotFoundError(resolved)
        return resolved, policy

    @staticmethod
    def _is_policy_root(path: Path, policy: ComputerAccessPolicy) -> bool:
        if policy.full_filesystem:
            anchor = Path(path.anchor).resolve(strict=False) if path.anchor else None
            return bool(anchor and path == anchor)
        return any(path == root for root in policy.allowed_roots)

    def computer_access_status(self, payload: dict[str, Any]) -> ActionResult:
        if payload:
            return ActionResult(False, "computer.access_status does not accept fields")
        policy = self._computer_access_policy()
        return ActionResult(True, "computer access policy ready", policy.public())

    def computer_file_stat(self, payload: dict[str, Any]) -> ActionResult:
        path, _ = self._computer_path(payload.get("path"), must_exist=True)
        stat = path.stat()
        data: dict[str, Any] = {
            "path": str(path),
            "name": path.name or str(path),
            "kind": "directory" if path.is_dir() else "file" if path.is_file() else "other",
            "size_bytes": stat.st_size,
            "modified_at_ns": stat.st_mtime_ns,
        }
        if path.is_file() and stat.st_size <= _MAX_TEXT_BYTES:
            try:
                data["sha256"] = _sha256(path.read_bytes())
            except OSError:
                pass
        return ActionResult(True, "computer path inspected", data)

    def computer_directory_list(self, payload: dict[str, Any]) -> ActionResult:
        path, policy = self._computer_path(payload.get("path"), must_exist=True)
        if not path.is_dir():
            return ActionResult(False, "path is not a directory")

        max_depth = _bounded_int(
            payload.get("max_depth"),
            default=2,
            minimum=1,
            maximum=12,
            name="max_depth",
        )
        max_entries = _bounded_int(
            payload.get("max_entries"),
            default=500,
            minimum=1,
            maximum=_MAX_LIST_ENTRIES,
            name="max_entries",
        )
        include_hidden = bool(payload.get("include_hidden", False))
        entries: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []
        queue: list[tuple[Path, int]] = [(path, 0)]

        while queue and len(entries) < max_entries:
            directory, depth = queue.pop(0)
            if depth >= max_depth:
                continue
            try:
                children = sorted(
                    directory.iterdir(),
                    key=lambda item: (not item.is_dir(), item.name.casefold()),
                )
            except OSError as error:
                errors.append({"path": str(directory), "error": str(error)[:500]})
                continue

            for child in children:
                if not include_hidden and child.name.startswith("."):
                    continue
                try:
                    resolved = child.resolve(strict=False)
                except OSError:
                    resolved = child.absolute()
                allowed = _path_allowed(resolved, policy)
                kind = "directory" if child.is_dir() else "file" if child.is_file() else "other"
                item: dict[str, Any] = {
                    "path": str(child),
                    "name": child.name,
                    "kind": kind,
                    "depth": depth + 1,
                    "allowed": allowed,
                }
                try:
                    stat = child.stat()
                    item["size_bytes"] = stat.st_size
                    item["modified_at_ns"] = stat.st_mtime_ns
                except OSError:
                    pass
                entries.append(item)
                if len(entries) >= max_entries:
                    break
                if allowed and kind == "directory" and not child.is_symlink():
                    queue.append((resolved, depth + 1))

        return ActionResult(
            True,
            "computer directory listed",
            {
                "path": str(path),
                "max_depth": max_depth,
                "max_entries": max_entries,
                "truncated": len(entries) >= max_entries,
                "entries": entries,
                "errors": errors[:100],
            },
        )

    def computer_text_read(self, payload: dict[str, Any]) -> ActionResult:
        path, _ = self._computer_path(payload.get("path"), must_exist=True)
        if not path.is_file():
            return ActionResult(False, "path is not a file")
        size = path.stat().st_size
        if size > _MAX_TEXT_BYTES:
            return ActionResult(
                False,
                f"file is too large for text inspection: {size} > {_MAX_TEXT_BYTES}",
                {"path": str(path), "size_bytes": size},
            )
        raw = path.read_bytes()
        try:
            content = raw.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            return ActionResult(False, f"file is not valid UTF-8 text: {error}")

        start_line = _bounded_int(
            payload.get("start_line"),
            default=1,
            minimum=1,
            maximum=2_000_000,
            name="start_line",
        )
        end_value = payload.get("end_line")
        end_line = None
        if end_value is not None:
            end_line = _bounded_int(
                end_value,
                default=start_line,
                minimum=start_line,
                maximum=2_000_000,
                name="end_line",
            )
        lines = content.splitlines(keepends=True)
        selected = "".join(lines[start_line - 1 : end_line])
        if len(selected.encode("utf-8")) > _MAX_INLINE_BYTES:
            return ActionResult(
                False,
                "selected text range is too large; request a smaller line range",
                {
                    "path": str(path),
                    "sha256": _sha256(raw),
                    "line_count": len(lines),
                    "max_inline_bytes": _MAX_INLINE_BYTES,
                },
            )
        return ActionResult(
            True,
            "computer text ready",
            {
                "path": str(path),
                "size_bytes": len(raw),
                "sha256": _sha256(raw),
                "line_count": len(lines),
                "start_line": start_line,
                "end_line": min(end_line or len(lines), len(lines)),
                "content": selected,
            },
        )

    def computer_text_write(self, payload: dict[str, Any]) -> ActionResult:
        path, _ = self._computer_path(payload.get("path"), must_exist=False)
        content = payload.get("content")
        if not isinstance(content, str):
            return ActionResult(False, "content must be a string")
        encoded = content.encode("utf-8")
        if len(encoded) > _MAX_WRITE_BYTES:
            return ActionResult(False, f"content exceeds {_MAX_WRITE_BYTES} bytes")

        if path.exists() and not path.is_file():
            return ActionResult(False, "path exists and is not a file")
        exists = path.is_file()
        current = path.read_bytes() if exists else None
        current_sha = _sha256(current) if current is not None else None
        expected = str(payload.get("expected_sha256") or "").strip().lower()
        create = bool(payload.get("create", False))

        if exists:
            if not expected:
                return ActionResult(
                    False,
                    "expected_sha256 is required when replacing an existing file",
                    {"path": str(path), "current_sha256": current_sha},
                )
            if expected != current_sha:
                return ActionResult(
                    False,
                    "file changed since it was read; refusing stale overwrite",
                    {
                        "path": str(path),
                        "expected_sha256": expected,
                        "current_sha256": current_sha,
                    },
                )
        elif not create:
            return ActionResult(False, "file does not exist; set create=true to create it")

        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(f".{path.name}.ordax-{uuid.uuid4().hex}.tmp")
        try:
            temp.write_bytes(encoded)
            if temp.read_bytes() != encoded:
                raise OSError("temporary write verification failed")
            os.replace(temp, path)
        finally:
            try:
                temp.unlink()
            except FileNotFoundError:
                pass

        return ActionResult(
            True,
            "computer text written",
            {
                "path": str(path),
                "created": not exists,
                "size_bytes": len(encoded),
                "sha256": _sha256(encoded),
                "previous_sha256": current_sha,
            },
        )

    def computer_text_patch(self, payload: dict[str, Any]) -> ActionResult:
        path, _ = self._computer_path(payload.get("path"), must_exist=True)
        if not path.is_file():
            return ActionResult(False, "path is not a file")
        raw = path.read_bytes()
        if len(raw) > _MAX_TEXT_BYTES:
            return ActionResult(False, f"file exceeds {_MAX_TEXT_BYTES} bytes")
        expected = str(payload.get("expected_sha256") or "").strip().lower()
        current_sha = _sha256(raw)
        if not expected or expected != current_sha:
            return ActionResult(
                False,
                "expected_sha256 is required and must match current file",
                {"path": str(path), "current_sha256": current_sha},
            )
        try:
            content = raw.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            return ActionResult(False, f"file is not valid UTF-8 text: {error}")

        replacements = payload.get("replacements")
        if (
            not isinstance(replacements, list)
            or not replacements
            or len(replacements) > 100
        ):
            return ActionResult(False, "replacements must contain 1..100 entries")

        updated = content
        counts: list[int] = []
        for item in replacements:
            if not isinstance(item, dict):
                return ActionResult(False, "replacement entries must be objects")
            old = item.get("old")
            new = item.get("new")
            expected_count = item.get("expected_count", 1)
            if not isinstance(old, str) or not old:
                return ActionResult(False, "replacement old must be a non-empty string")
            if not isinstance(new, str):
                return ActionResult(False, "replacement new must be a string")
            count = updated.count(old)
            if not isinstance(expected_count, int) or expected_count < 1 or expected_count > 10000:
                return ActionResult(False, "expected_count must be an integer between 1 and 10000")
            if count != expected_count:
                return ActionResult(
                    False,
                    f"replacement match count differs: expected {expected_count}, found {count}",
                    {"path": str(path), "current_sha256": current_sha},
                )
            updated = updated.replace(old, new)
            counts.append(count)

        encoded = updated.encode("utf-8")
        if len(encoded) > _MAX_WRITE_BYTES:
            return ActionResult(False, f"patched content exceeds {_MAX_WRITE_BYTES} bytes")
        temp = path.with_name(f".{path.name}.ordax-{uuid.uuid4().hex}.tmp")
        try:
            temp.write_bytes(encoded)
            os.replace(temp, path)
        finally:
            try:
                temp.unlink()
            except FileNotFoundError:
                pass
        return ActionResult(
            True,
            "computer text patched",
            {
                "path": str(path),
                "previous_sha256": current_sha,
                "sha256": _sha256(encoded),
                "replacement_counts": counts,
                "size_bytes": len(encoded),
            },
        )

    def computer_directory_create(self, payload: dict[str, Any]) -> ActionResult:
        path, _ = self._computer_path(payload.get("path"), must_exist=False)
        parents = bool(payload.get("parents", True))
        if path.exists():
            if path.is_dir():
                return ActionResult(True, "computer directory already exists", {"path": str(path)})
            return ActionResult(False, "path exists and is not a directory")
        path.mkdir(parents=parents, exist_ok=False)
        return ActionResult(True, "computer directory created", {"path": str(path)})

    def computer_path_move(self, payload: dict[str, Any]) -> ActionResult:
        source, source_policy = self._computer_path(payload.get("source"), must_exist=True)
        destination, _ = self._computer_path(payload.get("destination"), must_exist=False)
        if self._is_policy_root(source, source_policy):
            return ActionResult(False, "refusing to move a configured computer access root")
        if source == destination:
            return ActionResult(False, "source and destination are the same path")
        if destination.exists():
            if not bool(payload.get("overwrite", False)):
                return ActionResult(False, "destination exists; set overwrite=true to replace a file")
            if destination.is_dir():
                return ActionResult(False, "overwriting an existing directory is not supported")
            destination.unlink()
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
        return ActionResult(
            True,
            "computer path moved",
            {"source": str(source), "destination": str(destination)},
        )

    def computer_path_remove(self, payload: dict[str, Any]) -> ActionResult:
        path, policy = self._computer_path(payload.get("path"), must_exist=True)
        if self._is_policy_root(path, policy):
            return ActionResult(False, "refusing to remove a configured computer access root")
        recursive = bool(payload.get("recursive", False))
        if path.is_symlink() or path.is_file():
            path.unlink()
            kind = "file"
        elif path.is_dir():
            if recursive:
                shutil.rmtree(path)
            else:
                try:
                    path.rmdir()
                except OSError:
                    return ActionResult(False, "directory is not empty; set recursive=true")
            kind = "directory"
        else:
            return ActionResult(False, "unsupported path type")
        return ActionResult(True, "computer path removed", {"path": str(path), "kind": kind})

    def computer_search(self, payload: dict[str, Any]) -> ActionResult:
        root, policy = self._computer_path(payload.get("root"), must_exist=True)
        if not root.is_dir():
            return ActionResult(False, "search root is not a directory")

        query = str(payload.get("query") or "").strip()
        if not query or len(query) > 200:
            return ActionResult(False, "query must contain 1..200 characters")
        mode = str(payload.get("mode") or "name").strip().lower()
        if mode not in {"name", "content", "both"}:
            return ActionResult(False, "mode must be name, content or both")
        max_results = _bounded_int(
            payload.get("max_results"),
            default=100,
            minimum=1,
            maximum=_MAX_SEARCH_RESULTS,
            name="max_results",
        )
        max_depth = _bounded_int(
            payload.get("max_depth"),
            default=6,
            minimum=1,
            maximum=12,
            name="max_depth",
        )
        include_hidden = bool(payload.get("include_hidden", False))
        deadline = time.monotonic() + 8.0
        needle = query.casefold()
        results: list[dict[str, Any]] = []
        scanned = 0
        timed_out = False
        queue: list[tuple[Path, int]] = [(root, 0)]

        while queue and len(results) < max_results:
            if time.monotonic() >= deadline:
                timed_out = True
                break
            directory, depth = queue.pop(0)
            if depth >= max_depth:
                continue
            try:
                children = list(directory.iterdir())
            except OSError:
                continue

            for child in children:
                if time.monotonic() >= deadline:
                    timed_out = True
                    break
                if not include_hidden and child.name.startswith("."):
                    continue
                if child.is_dir() and child.name in _SKIP_SEARCH_DIRS:
                    continue
                scanned += 1
                try:
                    resolved = child.resolve(strict=False)
                except OSError:
                    continue
                if not _path_allowed(resolved, policy):
                    continue

                matched_name = needle in child.name.casefold()
                if matched_name and mode in {"name", "both"}:
                    results.append(
                        {
                            "path": str(child),
                            "kind": "directory" if child.is_dir() else "file" if child.is_file() else "other",
                            "matched_by": "name",
                        }
                    )
                    if len(results) >= max_results:
                        break

                if child.is_file() and mode in {"content", "both"}:
                    try:
                        size = child.stat().st_size
                        if size <= 1024 * 1024:
                            text = child.read_text(encoding="utf-8-sig", errors="ignore")
                            position = text.casefold().find(needle)
                            if position >= 0:
                                line = text.count("\n", 0, position) + 1
                                snippet = text[max(0, position - 120) : position + len(query) + 240]
                                results.append(
                                    {
                                        "path": str(child),
                                        "kind": "file",
                                        "matched_by": "content",
                                        "line": line,
                                        "snippet": snippet.replace("\x00", "")[:500],
                                    }
                                )
                                if len(results) >= max_results:
                                    break
                    except OSError:
                        pass

                if child.is_dir() and not child.is_symlink():
                    queue.append((resolved, depth + 1))

        return ActionResult(
            True,
            "computer search complete",
            {
                "root": str(root),
                "query": query,
                "mode": mode,
                "results": results,
                "scanned_entries": scanned,
                "truncated": len(results) >= max_results,
                "timed_out": timed_out,
            },
        )
