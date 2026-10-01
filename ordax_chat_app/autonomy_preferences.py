"""Persistent non-secret autonomy preferences for ORDAX Dev."""
from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

from .auth import resolve_chat_app_state_dir


class AutonomyPreferencesStore:
    def __init__(self, path: str | Path | None = None):
        self.path = (
            Path(path).expanduser().resolve()
            if path
            else resolve_chat_app_state_dir() / "autonomy.json"
        )
        self._lock = threading.RLock()

    def load(self) -> dict[str, Any]:
        with self._lock:
            if not self.path.is_file():
                return {
                    "version": 1,
                    "enabled": False,
                    "model": None,
                    "project_slugs": [],
                    "context_window_tokens": 128000,
                    "idle_sleep_seconds": 5.0,
                }
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or payload.get("version") != 1:
                raise ValueError("unsupported autonomy preferences format")
            projects = payload.get("project_slugs")
            if not isinstance(projects, list):
                raise ValueError("invalid autonomy project scope")
            return {
                "version": 1,
                "enabled": bool(payload.get("enabled", False)),
                "model": str(payload.get("model") or "") or None,
                "project_slugs": [str(item) for item in projects if str(item).strip()],
                "context_window_tokens": int(payload.get("context_window_tokens", 128000)),
                "idle_sleep_seconds": float(payload.get("idle_sleep_seconds", 5.0)),
            }

    def save(
        self,
        *,
        enabled: bool,
        model: str | None,
        project_slugs: list[str] | tuple[str, ...] | set[str],
        context_window_tokens: int,
        idle_sleep_seconds: float,
    ) -> dict[str, Any]:
        payload = {
            "version": 1,
            "enabled": bool(enabled),
            "model": str(model or "") or None,
            "project_slugs": sorted({str(item).strip() for item in project_slugs if str(item).strip()}),
            "context_window_tokens": int(context_window_tokens),
            "idle_sleep_seconds": float(idle_sleep_seconds),
        }
        encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, temp_name = tempfile.mkstemp(
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                dir=str(self.path.parent),
            )
            temp = Path(temp_name)
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(encoded)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp, self.path)
            finally:
                try:
                    temp.unlink()
                except FileNotFoundError:
                    pass
        return payload

    def disable(self) -> dict[str, Any]:
        current = self.load()
        return self.save(
            enabled=False,
            model=current.get("model"),
            project_slugs=current.get("project_slugs", []),
            context_window_tokens=int(current.get("context_window_tokens", 128000)),
            idle_sleep_seconds=float(current.get("idle_sleep_seconds", 5.0)),
        )
