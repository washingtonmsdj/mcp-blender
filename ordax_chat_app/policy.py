"""Persistent local capability policy for ORDAX Chat App."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from ordax_core.memory import resolve_memory_db


KNOWN_CAPABILITIES = frozenset({
    "computer.observe",
    "computer.interact",
})


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


class CapabilityPolicyStore:
    """Project-scoped capability grants. Sensitive capabilities default denied."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path).expanduser().resolve() if db_path else resolve_memory_db()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _init_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_capability_grants(
                  project_slug TEXT NOT NULL,
                  capability TEXT NOT NULL,
                  enabled INTEGER NOT NULL,
                  updated_at TEXT NOT NULL,
                  PRIMARY KEY(project_slug, capability)
                )
                """
            )

    @staticmethod
    def _validate_capability(capability: str) -> str:
        capability = str(capability or "").strip()
        if capability not in KNOWN_CAPABILITIES:
            raise ValueError(f"unknown capability: {capability}")
        return capability

    def set(self, project_slug: str, capability: str, enabled: bool) -> dict[str, Any]:
        project_slug = str(project_slug or "").strip()
        if not project_slug:
            raise ValueError("project_slug is required")
        capability = self._validate_capability(capability)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO chat_capability_grants(project_slug,capability,enabled,updated_at)
                VALUES(?,?,?,?)
                ON CONFLICT(project_slug,capability)
                DO UPDATE SET enabled=excluded.enabled,updated_at=excluded.updated_at
                """,
                (project_slug, capability, int(bool(enabled)), _now()),
            )
        return {
            "project_slug": project_slug,
            "capability": capability,
            "enabled": bool(enabled),
        }

    def enabled(self, project_slug: str, capability: str) -> bool:
        capability = self._validate_capability(capability)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT enabled FROM chat_capability_grants
                WHERE project_slug=? AND capability=?
                """,
                (str(project_slug), capability),
            ).fetchone()
        return bool(row["enabled"]) if row else False

    def project(self, project_slug: str) -> dict[str, bool]:
        slug = str(project_slug or "").strip()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT capability,enabled FROM chat_capability_grants
                WHERE project_slug=?
                """,
                (slug,),
            ).fetchall()
        configured = {str(row["capability"]): bool(row["enabled"]) for row in rows}
        return {name: configured.get(name, False) for name in sorted(KNOWN_CAPABILITIES)}
