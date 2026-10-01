"""Persistent local conversations for ORDAX Chat App."""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from ordax_core.memory import resolve_memory_db


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


class ConversationStore:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path).expanduser().resolve() if db_path else resolve_memory_db()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
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
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS chat_threads(
                  id TEXT PRIMARY KEY,
                  project_slug TEXT NOT NULL,
                  agent_id TEXT NOT NULL,
                  session_id TEXT NOT NULL,
                  provider TEXT NOT NULL,
                  model TEXT NOT NULL,
                  title TEXT NOT NULL,
                  archived INTEGER NOT NULL DEFAULT 0,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_chat_threads_project
                  ON chat_threads(project_slug, archived, updated_at);

                CREATE TABLE IF NOT EXISTS chat_model_items(
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  thread_id TEXT NOT NULL,
                  sequence INTEGER NOT NULL,
                  item_json TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  UNIQUE(thread_id, sequence),
                  FOREIGN KEY(thread_id) REFERENCES chat_threads(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_chat_model_items_thread
                  ON chat_model_items(thread_id, sequence);

                CREATE TABLE IF NOT EXISTS chat_messages(
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  thread_id TEXT NOT NULL,
                  role TEXT NOT NULL,
                  text TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  FOREIGN KEY(thread_id) REFERENCES chat_threads(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_chat_messages_thread
                  ON chat_messages(thread_id, id);
                """
            )

    def create_thread(
        self,
        *,
        project_slug: str,
        agent_id: str,
        session_id: str,
        provider: str,
        model: str,
        title: str = "New chat",
    ) -> dict[str, Any]:
        thread_id = str(uuid.uuid4())
        created = _now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO chat_threads(
                  id,project_slug,agent_id,session_id,provider,model,title,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    thread_id, project_slug, agent_id, session_id, provider,
                    model, title.strip()[:160] or "New chat", created, created,
                ),
            )
            row = connection.execute("SELECT * FROM chat_threads WHERE id=?", (thread_id,)).fetchone()
        return dict(row)

    def thread(self, thread_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM chat_threads WHERE id=?", (thread_id,)).fetchone()
        if not row:
            raise ValueError(f"chat thread not found: {thread_id}")
        return dict(row)

    def list_threads(self, project_slug: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as connection:
            if project_slug:
                rows = connection.execute(
                    """
                    SELECT * FROM chat_threads
                    WHERE project_slug=? AND archived=0
                    ORDER BY updated_at DESC
                    """,
                    (project_slug,),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT * FROM chat_threads
                    WHERE archived=0
                    ORDER BY updated_at DESC
                    """
                ).fetchall()
        return [dict(row) for row in rows]

    def set_title(self, thread_id: str, title: str) -> dict[str, Any]:
        text = title.strip()[:160]
        if not text:
            raise ValueError("thread title cannot be empty")
        with self._connect() as connection:
            connection.execute(
                "UPDATE chat_threads SET title=?,updated_at=? WHERE id=?",
                (text, _now(), thread_id),
            )
        return self.thread(thread_id)

    def update_session(self, thread_id: str, session_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE chat_threads SET session_id=?,updated_at=? WHERE id=?",
                (session_id, _now(), thread_id),
            )
            if cursor.rowcount != 1:
                raise ValueError(f"chat thread not found: {thread_id}")
        return self.thread(thread_id)

    def append_items(self, thread_id: str, items: list[dict[str, Any]]) -> None:
        if not items:
            return
        self.thread(thread_id)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COALESCE(MAX(sequence),0) AS seq FROM chat_model_items WHERE thread_id=?",
                (thread_id,),
            ).fetchone()
            sequence = int(row["seq"])
            for item in items:
                sequence += 1
                connection.execute(
                    """
                    INSERT INTO chat_model_items(thread_id,sequence,item_json,created_at)
                    VALUES(?,?,?,?)
                    """,
                    (
                        thread_id,
                        sequence,
                        json.dumps(item, ensure_ascii=False, separators=(",", ":"), default=str),
                        _now(),
                    ),
                )
            connection.execute(
                "UPDATE chat_threads SET updated_at=? WHERE id=?",
                (_now(), thread_id),
            )

    def replace_items(self, thread_id: str, items: list[dict[str, Any]]) -> None:
        self.thread(thread_id)
        with self._connect() as connection:
            connection.execute("DELETE FROM chat_model_items WHERE thread_id=?", (thread_id,))
            for sequence, item in enumerate(items, start=1):
                connection.execute(
                    """
                    INSERT INTO chat_model_items(thread_id,sequence,item_json,created_at)
                    VALUES(?,?,?,?)
                    """,
                    (
                        thread_id,
                        sequence,
                        json.dumps(item, ensure_ascii=False, separators=(",", ":"), default=str),
                        _now(),
                    ),
                )
            connection.execute(
                "UPDATE chat_threads SET updated_at=? WHERE id=?",
                (_now(), thread_id),
            )

    def items(self, thread_id: str) -> list[dict[str, Any]]:
        self.thread(thread_id)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT item_json FROM chat_model_items WHERE thread_id=? ORDER BY sequence ASC",
                (thread_id,),
            ).fetchall()
        return [json.loads(row["item_json"]) for row in rows]

    def append_message(self, thread_id: str, role: str, text: str) -> dict[str, Any]:
        role = role.strip()
        if role not in {"user", "assistant", "system"}:
            raise ValueError(f"invalid chat role: {role}")
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO chat_messages(thread_id,role,text,created_at) VALUES(?,?,?,?)",
                (thread_id, role, text, _now()),
            )
            connection.execute("UPDATE chat_threads SET updated_at=? WHERE id=?", (_now(), thread_id))
            row = connection.execute("SELECT * FROM chat_messages WHERE id=?", (cursor.lastrowid,)).fetchone()
        return dict(row)

    def messages(self, thread_id: str, *, limit: int = 500) -> list[dict[str, Any]]:
        self.thread(thread_id)
        limit = max(1, min(5000, int(limit)))
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM (
                  SELECT * FROM chat_messages WHERE thread_id=? ORDER BY id DESC LIMIT ?
                ) ORDER BY id ASC
                """,
                (thread_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]
