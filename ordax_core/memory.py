from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def resolve_memory_db() -> Path:
    override = os.environ.get("ORDAX_MEMORY_DB")
    if override:
        return Path(override).expanduser().resolve()
    legacy = Path.home() / "Apps" / "OrdaxLocalAI" / "data" / "state.db"
    if legacy.is_file():
        return legacy.resolve()
    local_app_data = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return (local_app_data / "OrdaX" / "Studio" / "state.db").resolve()


class MemoryStore:
    """Project-scoped persistent memory compatible with the original Local AI database."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path).expanduser().resolve() if db_path else resolve_memory_db()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.context_dir = self.db_path.parent / "contexts"
        self.context_dir.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
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
            connection.executescript("""
            CREATE TABLE IF NOT EXISTS projects(
              id INTEGER PRIMARY KEY, name TEXT NOT NULL, path TEXT NOT NULL UNIQUE,
              active INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS memories(
              id INTEGER PRIMARY KEY, project_id INTEGER, kind TEXT NOT NULL DEFAULT 'note',
              content TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS tasks(
              id INTEGER PRIMARY KEY, project_id INTEGER, title TEXT NOT NULL,
              done INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS checkpoints(
              id INTEGER PRIMARY KEY, project_id INTEGER, summary TEXT NOT NULL,
              git_state TEXT, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events(
              id INTEGER PRIMARY KEY, event TEXT NOT NULL, payload TEXT, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions(
              id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL,
              started_at TEXT NOT NULL, ended_at TEXT, resumed_from_checkpoint_id INTEGER);
            CREATE TABLE IF NOT EXISTS handoffs(
              id TEXT PRIMARY KEY, project_id INTEGER NOT NULL,
              summary TEXT NOT NULL, next_action TEXT,
              completed_json TEXT NOT NULL, blockers_json TEXT NOT NULL,
              changed_paths_json TEXT NOT NULL, git_state TEXT NOT NULL,
              created_at TEXT NOT NULL, expires_at TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_handoffs_project_expiry
              ON handoffs(project_id, expires_at);
            """)

    def _project_id(self, slug: str, path: str | Path) -> int:
        resolved = str(Path(path).expanduser().resolve())
        with self._connect() as connection:
            row = connection.execute("SELECT id FROM projects WHERE path=?", (resolved,)).fetchone()
            if row:
                connection.execute("UPDATE projects SET name=? WHERE id=?", (slug, row["id"]))
                return int(row["id"])
            cursor = connection.execute(
                "INSERT INTO projects(name,path,active,created_at) VALUES(?,?,0,?)",
                (slug, resolved, now()),
            )
            return int(cursor.lastrowid)

    def set_active_project(self, slug: str, path: str | Path) -> dict[str, Any]:
        project_id = self._project_id(slug, path)
        with self._connect() as connection:
            connection.execute("UPDATE projects SET active=0")
            connection.execute("UPDATE projects SET active=1 WHERE id=?", (project_id,))
            connection.execute("INSERT INTO events(event,payload,created_at) VALUES(?,?,?)",
                ("active_project", json.dumps({"project": slug, "project_id": project_id}, ensure_ascii=False), now()))
            row = connection.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        self.write_context(slug, path)
        self.write_boot_context(slug, path)
        return dict(row)

    def active_project(self) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM projects WHERE active=1 ORDER BY id DESC LIMIT 1").fetchone()
        return dict(row) if row else None

    def remember(self, slug: str, path: str | Path, content: str, kind: str = "note") -> int:
        text = content.strip()
        if not text:
            raise ValueError("memory content cannot be empty")
        project_id = self._project_id(slug, path)
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO memories(project_id,kind,content,created_at) VALUES(?,?,?,?)",
                (project_id, kind.strip() or "note", text, now()),
            )
            memory_id = int(cursor.lastrowid)
        self.write_context(slug, path)
        return memory_id

    def add_task(self, slug: str, path: str | Path, title: str) -> int:
        text = title.strip()
        if not text:
            raise ValueError("task title cannot be empty")
        project_id = self._project_id(slug, path)
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO tasks(project_id,title,created_at) VALUES(?,?,?)",
                (project_id, text, now()),
            )
            task_id = int(cursor.lastrowid)
        self.write_context(slug, path)
        return task_id

    def toggle_task(self, slug: str, path: str | Path, task_id: int) -> bool:
        project_id = self._project_id(slug, path)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT done FROM tasks WHERE id=? AND project_id=?", (task_id, project_id)
            ).fetchone()
            if not row:
                raise ValueError(f"task not found for project: {task_id}")
            done = not bool(row["done"])
            connection.execute("UPDATE tasks SET done=? WHERE id=?", (int(done), task_id))
        self.write_context(slug, path)
        return done

    @staticmethod
    def git_state(path: str | Path) -> dict[str, Any]:
        root_path = Path(path).resolve()
        if not (root_path / ".git").exists():
            return {"repository": False, "branch": "", "head": "", "status": ""}
        root = str(root_path)
        try:
            def run(*args: str) -> str:
                return subprocess.run(
                    ["git", "-C", root, *args], capture_output=True, text=True,
                    timeout=5, check=False,
                ).stdout.strip()
            return {
                "branch": run("branch", "--show-current"),
                "head": run("rev-parse", "--short", "HEAD"),
                "status": run("status", "--short"),
            }
        except Exception as error:
            return {"error": f"{type(error).__name__}: {error}"}

    def checkpoint(self, slug: str, path: str | Path, summary: str) -> int:
        text = summary.strip() or "Checkpoint salvo"
        project_id = self._project_id(slug, path)
        state = self.git_state(path)
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO checkpoints(project_id,summary,git_state,created_at) VALUES(?,?,?,?)",
                (project_id, text, json.dumps(state, ensure_ascii=False), now()),
            )
            connection.execute(
                "INSERT INTO events(event,payload,created_at) VALUES(?,?,?)"
                ,("checkpoint", json.dumps({"project": slug, "summary": text}, ensure_ascii=False), now()),
            )
            checkpoint_id = int(cursor.lastrowid)
        self.write_context(slug, path)
        return checkpoint_id

    def start_session(self, slug: str, path: str | Path) -> dict[str, Any]:
        project = self.set_active_project(slug, path)
        project_id = int(project["id"])
        with self._connect() as connection:
            connection.execute(
                "UPDATE sessions SET ended_at=? WHERE ended_at IS NULL",
                (now(),),
            )
            checkpoint = connection.execute("SELECT id FROM checkpoints WHERE project_id=? ORDER BY id DESC LIMIT 1", (project_id,)).fetchone()
            resumed_from = int(checkpoint["id"]) if checkpoint else None
            cursor = connection.execute("INSERT INTO sessions(project_id,started_at,resumed_from_checkpoint_id) VALUES(?,?,?)", (project_id, now(), resumed_from))
            session_id = int(cursor.lastrowid)
            connection.execute("INSERT INTO events(event,payload,created_at) VALUES(?,?,?)",
                ("session_started", json.dumps({"project": slug, "session_id": session_id}, ensure_ascii=False), now()))
        data = self.context(slug, path)
        data["session_id"] = session_id
        data["resumed_from_checkpoint_id"] = resumed_from
        data["git"] = self.git_state(path)
        data["boot_context_path"] = str(self.write_boot_context(slug, path))
        return data

    def finish_session(self, session_id: int) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("UPDATE sessions SET ended_at=? WHERE id=? AND ended_at IS NULL", (now(), int(session_id)))
            return cursor.rowcount > 0

    def create_handoff(
        self,
        slug: str,
        path: str | Path,
        summary: str,
        *,
        next_action: str = "",
        completed: list[str] | None = None,
        blockers: list[str] | None = None,
        changed_paths: list[str] | None = None,
        ttl_hours: int = 24,
    ) -> dict[str, Any]:
        text = summary.strip()
        if not text:
            raise ValueError("handoff summary cannot be empty")
        if len(text) > 20000:
            raise ValueError("handoff summary is too long")
        ttl_hours = int(ttl_hours)
        if ttl_hours < 1 or ttl_hours > 168:
            raise ValueError("ttl_hours must be between 1 and 168")

        project_id = self._project_id(slug, path)
        handoff_id = f"hof_{uuid.uuid4().hex}"
        created_dt = datetime.now().astimezone()
        expires_dt = created_dt + timedelta(hours=ttl_hours)
        git_state = self.git_state(path)
        payloads = {
            "completed": list(completed or []),
            "blockers": list(blockers or []),
            "changed_paths": list(changed_paths or []),
        }
        for key, values in payloads.items():
            if len(values) > 100:
                raise ValueError(f"handoff {key} has too many items")
            payloads[key] = [str(item)[:2000] for item in values]

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO handoffs(
                  id,project_id,summary,next_action,completed_json,blockers_json,
                  changed_paths_json,git_state,created_at,expires_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    handoff_id,
                    project_id,
                    text,
                    next_action.strip()[:5000],
                    json.dumps(payloads["completed"], ensure_ascii=False),
                    json.dumps(payloads["blockers"], ensure_ascii=False),
                    json.dumps(payloads["changed_paths"], ensure_ascii=False),
                    json.dumps(git_state, ensure_ascii=False),
                    created_dt.isoformat(timespec="seconds"),
                    expires_dt.isoformat(timespec="seconds"),
                ),
            )
            connection.execute(
                "DELETE FROM handoffs WHERE expires_at < ?",
                (created_dt.isoformat(timespec="seconds"),),
            )
        return {
            "handoff_id": handoff_id,
            "project": slug,
            "expires_at": expires_dt.isoformat(timespec="seconds"),
            "summary": text,
            "next_action": next_action.strip()[:5000],
            "git": git_state,
        }

    def get_handoff(self, slug: str, path: str | Path, handoff_id: str) -> dict[str, Any]:
        token = str(handoff_id or "").strip()
        if not token.startswith("hof_") or len(token) != 36:
            raise ValueError("invalid handoff id")
        project_id = self._project_id(slug, path)
        current = datetime.now().astimezone()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM handoffs WHERE id=? AND project_id=?",
                (token, project_id),
            ).fetchone()
            if not row:
                raise ValueError("handoff not found for project")
            expires = datetime.fromisoformat(str(row["expires_at"]))
            if expires <= current:
                connection.execute("DELETE FROM handoffs WHERE id=?", (token,))
                raise ValueError("handoff expired")

        def load_list(raw: str) -> list[str]:
            try:
                value = json.loads(raw)
            except json.JSONDecodeError:
                return []
            return [str(item) for item in value] if isinstance(value, list) else []

        try:
            git_state = json.loads(str(row["git_state"]))
        except json.JSONDecodeError:
            git_state = {}
        return {
            "handoff_id": str(row["id"]),
            "project": slug,
            "summary": str(row["summary"]),
            "next_action": str(row["next_action"] or ""),
            "completed": load_list(str(row["completed_json"])),
            "blockers": load_list(str(row["blockers_json"])),
            "changed_paths": load_list(str(row["changed_paths_json"])),
            "git": git_state if isinstance(git_state, dict) else {},
            "created_at": str(row["created_at"]),
            "expires_at": str(row["expires_at"]),
        }

    def _recent(self, table: str, project_id: int, limit: int) -> list[sqlite3.Row]:
        if table not in {"memories", "tasks", "checkpoints"}:
            raise ValueError(f"unsupported memory table: {table}")
        with self._connect() as connection:
            return connection.execute(
                f"SELECT * FROM {table} WHERE project_id=? ORDER BY id DESC LIMIT ?",
                (project_id, limit),
            ).fetchall()

    def context(self, slug: str, path: str | Path) -> dict[str, Any]:
        project_id = self._project_id(slug, path)
        memories = [dict(row) for row in reversed(self._recent("memories", project_id, 20))]
        tasks = [dict(row) for row in reversed(self._recent("tasks", project_id, 30))]
        checkpoints = [dict(row) for row in reversed(self._recent("checkpoints", project_id, 10))]
        for item in checkpoints:
            if item.get("git_state"):
                try:
                    item["git_state"] = json.loads(item["git_state"])
                except json.JSONDecodeError:
                    pass
        return {
            "project": {"slug": slug, "path": str(Path(path).resolve())},
            "memory_db": str(self.db_path),
            "legacy_local_ai_db": "OrdaxLocalAI" in str(self.db_path),
            "memories": memories,
            "tasks": tasks,
            "checkpoints": checkpoints,
            "generated_at": now(),
        }

    def context_text(self, slug: str, path: str | Path) -> str:
        data = self.context(slug, path)
        lines = [
            "# ORDAX Studio — contexto persistente",
            "",
            f"Atualizado: {data['generated_at']}",
            "",
            "## Projeto",
            f"- Slug: {slug}",
            f"- Caminho: {data['project']['path']}",
            "",
            "## Memórias recentes",
      ]
        lines += [f"- [{item['kind']}] {item['content']}" for item in data["memories"]] or ["- Nenhuma."]
        lines += ["", "## Tarefas"]
        lines += [f"- [{'x' if item['done'] else ' '}] #{item['id']} {item['title']}" for item in data["tasks"]] or ["- Nenhuma."]
        lines += ["", "## Checkpoints recentes"]
        for item in data["checkpoints"]:
            lines.append(f"- {item['created_at']}: {item['summary']}")
            if item.get("git_state"):
                lines.append(f"  Git: {json.dumps(item['git_state'], ensure_ascii=False)}")
        if not data["checkpoints"]:
            lines.append("- Nenhum.")
        return "\n".join(lines) + "\n"

    def write_context(self, slug: str, path: str | Path) -> Path:
        safe_slug = "".join(ch for ch in slug if ch.isalnum() or ch in "-_") or "project"
        target = self.context_dir / f"{safe_slug}.md"
        target.write_text(self.context_text(slug, path), encoding="utf-8")
        return target

    def write_boot_context(self, slug: str, path: str | Path) -> Path:
        target = self.db_path.parent / "BOOT_CONTEXT.md"
        target.write_text(self.context_text(slug, path), encoding="utf-8")
        return target

    def status(self) -> dict[str, Any]:
        with self._connect() as connection:
            counts = {
                table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
                for table in ("projects", "memories", "tasks", "checkpoints", "events", "sessions", "handoffs")
            }
        return {
            "ok": True,
            "db_path": str(self.db_path),
            "context_dir": str(self.context_dir),
            "legacy_local_ai_db": "OrdaxLocalAI" in str(self.db_path),
            "counts": counts,
        }
