"""Persistent multi-agent orchestration for ORDAX Chat App.

The orchestrator owns durable agent identity, goals, model-session chains,
checkpoints and coordinator/worker messaging. It deliberately does not call a
model provider itself. Provider adapters consume the continuation bundles and
report token usage back to this store.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from .memory import resolve_memory_db


_AGENT_STATES = {"active", "sleeping", "waiting", "stopped"}
_GOAL_STATES = {"queued", "active", "blocked", "done", "cancelled"}
_SESSION_STATES = {"active", "rotated", "finished", "failed", "cancelled"}


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _uuid() -> str:
    return str(uuid.uuid4())


def _json_list(value: list[Any] | tuple[Any, ...] | None) -> str:
    return json.dumps(list(value or []), ensure_ascii=False, separators=(",", ":"))


def _decode_json(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


class OrchestratorStore:
    """Durable coordinator/worker state stored beside ORDAX project memory."""

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
                CREATE TABLE IF NOT EXISTS agent_profiles(
                  id TEXT PRIMARY KEY,
                  project_slug TEXT NOT NULL,
                  name TEXT NOT NULL,
                  role TEXT NOT NULL,
                  parent_agent_id TEXT,
                  state TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  FOREIGN KEY(parent_agent_id) REFERENCES agent_profiles(id)
                );
                CREATE INDEX IF NOT EXISTS idx_agent_profiles_project
                  ON agent_profiles(project_slug, created_at);

                CREATE TABLE IF NOT EXISTS agent_goals(
                  id TEXT PRIMARY KEY,
                  project_slug TEXT NOT NULL,
                  owner_agent_id TEXT NOT NULL,
                  title TEXT NOT NULL,
                  description TEXT NOT NULL,
                  state TEXT NOT NULL,
                  priority INTEGER NOT NULL,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  FOREIGN KEY(owner_agent_id) REFERENCES agent_profiles(id)
                );
                CREATE INDEX IF NOT EXISTS idx_agent_goals_owner
                  ON agent_goals(owner_agent_id, state, priority);

                CREATE TABLE IF NOT EXISTS agent_sessions(
                  id TEXT PRIMARY KEY,
                  agent_id TEXT NOT NULL,
                  goal_id TEXT,
                  provider TEXT NOT NULL,
                  model TEXT NOT NULL,
                  context_window_tokens INTEGER NOT NULL,
                  rollover_ratio REAL NOT NULL,
                  estimated_tokens INTEGER NOT NULL DEFAULT 0,
                  state TEXT NOT NULL,
                  predecessor_session_id TEXT,
                  started_at TEXT NOT NULL,
                  ended_at TEXT,
                  end_reason TEXT,
                  FOREIGN KEY(agent_id) REFERENCES agent_profiles(id),
                  FOREIGN KEY(goal_id) REFERENCES agent_goals(id),
                  FOREIGN KEY(predecessor_session_id) REFERENCES agent_sessions(id)
                );
                CREATE INDEX IF NOT EXISTS idx_agent_sessions_agent
                  ON agent_sessions(agent_id, started_at);

                CREATE TABLE IF NOT EXISTS agent_checkpoints(
                  id TEXT PRIMARY KEY,
                  session_id TEXT NOT NULL,
                  agent_id TEXT NOT NULL,
                  goal_id TEXT,
                  summary TEXT NOT NULL,
                  next_action TEXT NOT NULL,
                  completed_json TEXT NOT NULL,
                  blockers_json TEXT NOT NULL,
                  changed_paths_json TEXT NOT NULL,
                  git_state_json TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  FOREIGN KEY(session_id) REFERENCES agent_sessions(id),
                  FOREIGN KEY(agent_id) REFERENCES agent_profiles(id),
                  FOREIGN KEY(goal_id) REFERENCES agent_goals(id)
                );
                CREATE INDEX IF NOT EXISTS idx_agent_checkpoints_session
                  ON agent_checkpoints(session_id, created_at);

                CREATE TABLE IF NOT EXISTS agent_messages(
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  project_slug TEXT NOT NULL,
                  sender_agent_id TEXT NOT NULL,
                  recipient_agent_id TEXT NOT NULL,
                  kind TEXT NOT NULL,
                  content TEXT NOT NULL,
                  correlation_id TEXT,
                  created_at TEXT NOT NULL,
                  read_at TEXT,
                  FOREIGN KEY(sender_agent_id) REFERENCES agent_profiles(id),
                  FOREIGN KEY(recipient_agent_id) REFERENCES agent_profiles(id)
                );
                CREATE INDEX IF NOT EXISTS idx_agent_messages_recipient
                  ON agent_messages(recipient_agent_id, read_at, id);
                """
            )

    @staticmethod
    def _agent(row: sqlite3.Row) -> dict[str, Any]:
        return dict(row)

    @staticmethod
    def _goal(row: sqlite3.Row) -> dict[str, Any]:
        return dict(row)

    @staticmethod
    def _session(row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        threshold = int(data["context_window_tokens"] * data["rollover_ratio"])
        data["rollover_at_tokens"] = threshold
        data["remaining_before_rollover"] = max(0, threshold - data["estimated_tokens"])
        data["should_rollover"] = data["estimated_tokens"] >= threshold
        return data

    @staticmethod
    def _checkpoint(row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        data["completed"] = _decode_json(data.pop("completed_json"), [])
        data["blockers"] = _decode_json(data.pop("blockers_json"), [])
        data["changed_paths"] = _decode_json(data.pop("changed_paths_json"), [])
        data["git_state"] = _decode_json(data.pop("git_state_json"), {})
        return data

    def get_agent(self, agent_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM agent_profiles WHERE id=?", (agent_id,)).fetchone()
        if not row:
            raise ValueError(f"agent not found: {agent_id}")
        return self._agent(row)

    def create_agent(
        self,
        project_slug: str,
        name: str,
        role: str,
        *,
        parent_agent_id: str | None = None,
    ) -> dict[str, Any]:
        name = name.strip()
        role = role.strip()
        if not name or not role:
            raise ValueError("agent name and role are required")
        if len(name) > 120 or len(role) > 240:
            raise ValueError("agent name or role is too long")

        if parent_agent_id is not None:
            parent = self.get_agent(parent_agent_id)
            if parent["project_slug"] != project_slug:
                raise ValueError("worker and coordinator must belong to the same project")
            if parent["parent_agent_id"] is not None:
                raise ValueError("workers cannot own other workers")

        agent_id = _uuid()
        created = _now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO agent_profiles(
                  id,project_slug,name,role,parent_agent_id,state,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?)
                """,
                (agent_id, project_slug, name, role, parent_agent_id, "active", created, created),
            )
            row = connection.execute("SELECT * FROM agent_profiles WHERE id=?", (agent_id,)).fetchone()
        return self._agent(row)

    def set_agent_state(self, agent_id: str, state: str) -> dict[str, Any]:
        if state not in _AGENT_STATES:
            raise ValueError(f"invalid agent state: {state}")
        self.get_agent(agent_id)
        with self._connect() as connection:
            connection.execute(
                "UPDATE agent_profiles SET state=?, updated_at=? WHERE id=?",
                (state, _now(), agent_id),
            )
            row = connection.execute("SELECT * FROM agent_profiles WHERE id=?", (agent_id,)).fetchone()
        return self._agent(row)

    def create_goal(
        self,
        agent_id: str,
        title: str,
        description: str = "",
        *,
        priority: int = 50,
    ) -> dict[str, Any]:
        agent = self.get_agent(agent_id)
        title = title.strip()
        description = description.strip()
        if not title:
            raise ValueError("goal title is required")
        if not 0 <= int(priority) <= 100:
            raise ValueError("goal priority must be between 0 and 100")
        goal_id = _uuid()
        created = _now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO agent_goals(
                  id,project_slug,owner_agent_id,title,description,state,priority,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (goal_id, agent["project_slug"], agent_id, title, description, "queued", int(priority), created, created),
            )
            row = connection.execute("SELECT * FROM agent_goals WHERE id=?", (goal_id,)).fetchone()
        return self._goal(row)

    def update_goal(self, goal_id: str, *, state: str) -> dict[str, Any]:
        if state not in _GOAL_STATES:
            raise ValueError(f"invalid goal state: {state}")
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM agent_goals WHERE id=?", (goal_id,)).fetchone()
            if not row:
                raise ValueError(f"goal not found: {goal_id}")
            connection.execute(
                "UPDATE agent_goals SET state=?, updated_at=? WHERE id=?",
                (state, _now(), goal_id),
            )
            row = connection.execute("SELECT * FROM agent_goals WHERE id=?", (goal_id,)).fetchone()
        return self._goal(row)

    def start_session(
        self,
        agent_id: str,
        *,
        goal_id: str | None,
        provider: str,
        model: str,
        context_window_tokens: int,
        rollover_ratio: float = 0.80,
        predecessor_session_id: str | None = None,
    ) -> dict[str, Any]:
        agent = self.get_agent(agent_id)
        provider = provider.strip()
        model = model.strip()
        if not provider or not model:
            raise ValueError("provider and model are required")
        if not 4096 <= int(context_window_tokens) <= 10_000_000:
            raise ValueError("context_window_tokens must be between 4096 and 10000000")
        if not 0.50 <= float(rollover_ratio) <= 0.95:
            raise ValueError("rollover_ratio must be between 0.50 and 0.95")

        if goal_id is not None:
            with self._connect() as connection:
                goal = connection.execute("SELECT * FROM agent_goals WHERE id=?", (goal_id,)).fetchone()
            if not goal or goal["owner_agent_id"] != agent_id:
                raise ValueError("goal does not belong to this agent")

        if predecessor_session_id is not None:
            previous = self.session(predecessor_session_id)
            if previous["agent_id"] != agent_id:
                raise ValueError("predecessor session belongs to another agent")

        session_id = _uuid()
        started = _now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO agent_sessions(
                  id,agent_id,goal_id,provider,model,context_window_tokens,rollover_ratio,
                  estimated_tokens,state,predecessor_session_id,started_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    session_id, agent_id, goal_id, provider, model, int(context_window_tokens),
                    float(rollover_ratio), 0, "active", predecessor_session_id, started,
                ),
            )
            row = connection.execute("SELECT * FROM agent_sessions WHERE id=?", (session_id,)).fetchone()
        return self._session(row)

    def session(self, session_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM agent_sessions WHERE id=?", (session_id,)).fetchone()
        if not row:
            raise ValueError(f"agent session not found: {session_id}")
        return self._session(row)

    def record_usage(self, session_id: str, *, input_tokens: int, output_tokens: int) -> dict[str, Any]:
        current = self.session(session_id)
        if current["state"] != "active":
            raise ValueError("usage can only be recorded on an active session")
        input_tokens = int(input_tokens)
        output_tokens = int(output_tokens)
        if input_tokens < 0 or output_tokens < 0:
            raise ValueError("token counts cannot be negative")
        added = input_tokens + output_tokens
        with self._connect() as connection:
            connection.execute(
                "UPDATE agent_sessions SET estimated_tokens=estimated_tokens+? WHERE id=?",
                (added, session_id),
            )
            row = connection.execute("SELECT * FROM agent_sessions WHERE id=?", (session_id,)).fetchone()
        data = self._session(row)
        data["added_tokens"] = added
        return data

    def checkpoint(
        self,
        session_id: str,
        *,
        summary: str,
        next_action: str = "",
        completed: list[str] | None = None,
        blockers: list[str] | None = None,
        changed_paths: list[str] | None = None,
        git_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        session = self.session(session_id)
        summary = summary.strip()
        if not summary:
            raise ValueError("checkpoint summary is required")
        checkpoint_id = _uuid()
        created = _now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO agent_checkpoints(
                  id,session_id,agent_id,goal_id,summary,next_action,completed_json,
                  blockers_json,changed_paths_json,git_state_json,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    checkpoint_id,
                    session_id,
                    session["agent_id"],
                    session["goal_id"],
                    summary,
                    next_action.strip(),
                    _json_list(completed),
                    _json_list(blockers),
                    _json_list(changed_paths),
                    json.dumps(git_state or {}, ensure_ascii=False, separators=(",", ":")),
                    created,
                ),
            )
            row = connection.execute("SELECT * FROM agent_checkpoints WHERE id=?", (checkpoint_id,)).fetchone()
        return self._checkpoint(row)

    def finish_session(self, session_id: str, *, state: str = "finished", reason: str = "") -> dict[str, Any]:
        if state not in _SESSION_STATES - {"active"}:
            raise ValueError(f"invalid terminal session state: {state}")
        current = self.session(session_id)
        if current["state"] != "active":
            raise ValueError("session is already closed")
        with self._connect() as connection:
            connection.execute(
                "UPDATE agent_sessions SET state=?, ended_at=?, end_reason=? WHERE id=?",
                (state, _now(), reason.strip() or None, session_id),
            )
            row = connection.execute("SELECT * FROM agent_sessions WHERE id=?", (session_id,)).fetchone()
        return self._session(row)

    def rotate_session(
        self,
        session_id: str,
        *,
        summary: str,
        next_action: str,
        completed: list[str] | None = None,
        blockers: list[str] | None = None,
        changed_paths: list[str] | None = None,
        git_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        current = self.session(session_id)
        if current["state"] != "active":
            raise ValueError("only an active session can rotate")
        checkpoint = self.checkpoint(
            session_id,
            summary=summary,
            next_action=next_action,
            completed=completed,
            blockers=blockers,
            changed_paths=changed_paths,
            git_state=git_state,
        )
        self.finish_session(session_id, state="rotated", reason="context_rollover")
        successor = self.start_session(
            current["agent_id"],
            goal_id=current["goal_id"],
            provider=current["provider"],
            model=current["model"],
            context_window_tokens=current["context_window_tokens"],
            rollover_ratio=current["rollover_ratio"],
            predecessor_session_id=session_id,
        )
        return {
            "previous_session_id": session_id,
            "checkpoint": checkpoint,
            "session": successor,
            "continuation": self.continuation_bundle(successor["id"]),
        }

    def _message_allowed(self, sender: dict[str, Any], recipient: dict[str, Any]) -> bool:
        if sender["project_slug"] != recipient["project_slug"]:
            return False
        if sender["id"] == recipient["id"]:
            return True
        return (
            sender["parent_agent_id"] == recipient["id"]
            or recipient["parent_agent_id"] == sender["id"]
        )

    def send_message(
        self,
        sender_agent_id: str,
        recipient_agent_id: str,
        content: str,
        *,
        kind: str = "report",
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        sender = self.get_agent(sender_agent_id)
        recipient = self.get_agent(recipient_agent_id)
        if not self._message_allowed(sender, recipient):
            raise ValueError("worker-to-worker messaging is not allowed; route through the coordinator")
        content = content.strip()
        kind = kind.strip() or "report"
        if not content:
            raise ValueError("message content is required")
        if len(content) > 100_000:
            raise ValueError("message content is too large")
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO agent_messages(
                  project_slug,sender_agent_id,recipient_agent_id,kind,content,
                  correlation_id,created_at
                ) VALUES(?,?,?,?,?,?,?)
                """,
                (
                    sender["project_slug"], sender_agent_id, recipient_agent_id, kind,
                    content, correlation_id, _now(),
                ),
            )
            row = connection.execute("SELECT * FROM agent_messages WHERE id=?", (cursor.lastrowid,)).fetchone()
        return dict(row)

    def inbox(self, agent_id: str, *, unread_only: bool = True, limit: int = 100) -> list[dict[str, Any]]:
        self.get_agent(agent_id)
        limit = max(1, min(500, int(limit)))
        sql = "SELECT * FROM agent_messages WHERE recipient_agent_id=?"
        params: list[Any] = [agent_id]
        if unread_only:
            sql += " AND read_at IS NULL"
        sql += " ORDER BY id ASC LIMIT ?"
        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(sql, tuple(params)).fetchall()
        return [dict(row) for row in rows]

    def mark_message_read(self, agent_id: str, message_id: int) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE agent_messages SET read_at=?
                WHERE id=? AND recipient_agent_id=? AND read_at IS NULL
                """,
                (_now(), int(message_id), agent_id),
            )
            return cursor.rowcount > 0

    def continuation_bundle(self, session_id: str) -> dict[str, Any]:
        session = self.session(session_id)
        agent = self.get_agent(session["agent_id"])
        goal = None
        latest_checkpoint = None
        with self._connect() as connection:
            if session["goal_id"]:
                row = connection.execute("SELECT * FROM agent_goals WHERE id=?", (session["goal_id"],)).fetchone()
                goal = self._goal(row) if row else None

            predecessor = session["predecessor_session_id"]
            if predecessor:
                row = connection.execute(
                    """
                    SELECT * FROM agent_checkpoints
                    WHERE session_id=?
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    (predecessor,),
                ).fetchone()
                latest_checkpoint = self._checkpoint(row) if row else None

            rows = connection.execute(
                """
                SELECT * FROM agent_messages
                WHERE project_slug=? AND (
                  sender_agent_id=? OR recipient_agent_id=?
                )
                ORDER BY id DESC LIMIT 20
                """,
                (agent["project_slug"], agent["id"], agent["id"]),
            ).fetchall()
        messages = [dict(row) for row in reversed(rows)]
        return {
            "agent": agent,
            "goal": goal,
            "session": session,
            "latest_checkpoint": latest_checkpoint,
            "recent_messages": messages,
        }

    def status(self, project_slug: str) -> dict[str, Any]:
        with self._connect() as connection:
            agents = [self._agent(row) for row in connection.execute(
                "SELECT * FROM agent_profiles WHERE project_slug=? ORDER BY created_at ASC",
                (project_slug,),
            ).fetchall()]
            goals = [self._goal(row) for row in connection.execute(
                "SELECT * FROM agent_goals WHERE project_slug=? ORDER BY priority DESC, created_at ASC",
                (project_slug,),
            ).fetchall()]
            active_sessions = [self._session(row) for row in connection.execute(
                """
                SELECT s.* FROM agent_sessions s
                JOIN agent_profiles a ON a.id=s.agent_id
                WHERE a.project_slug=? AND s.state='active'
                ORDER BY s.started_at ASC
                """,
                (project_slug,),
            ).fetchall()]
            unread = int(connection.execute(
                """
                SELECT COUNT(*) FROM agent_messages
                WHERE project_slug=? AND read_at IS NULL
                """,
                (project_slug,),
            ).fetchone()[0])
        return {
            "project": project_slug,
            "agents": agents,
            "goals": goals,
            "active_sessions": active_sessions,
            "unread_messages": unread,
        }
