from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from .config import AgentConfig
from .models import ActionResult, AgentJob


class ControlPlane:
    """Small REST client for the Supabase control-plane schema.

    Realtime wake-up can be added without changing the job protocol; polling is
    retained as a resilient fallback.
    """

    def __init__(self, config: AgentConfig):
        if not config.supabase_url or not config.supabase_key:
            raise RuntimeError("ORDAX_SUPABASE_URL and ORDAX_SUPABASE_KEY are required")
        self.config = config
        self.base = config.supabase_url.rstrip("/") + "/rest/v1"
        self.key = config.supabase_key

    def _request(
        self,
        method: str,
        path: str,
        body: Any | None = None,
        *,
        prefer: str | None = None,
    ) -> Any:
        data = None
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        if body is not None:
            data = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            self.base + path,
            data=data,
            headers=headers,
            method=method,
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None

    def heartbeat(self, actions: list[str]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        payload = {
            "agent_name": self.config.agent_name,
            "status": "online",
            "last_seen_at": now,
            "capabilities": actions,
        }
        query_name = urllib.parse.quote(self.config.agent_name)
        rows = self._request("GET", f"/ordax_dev_agents?agent_name=eq.{query_name}&select=id")
        if rows:
            self._request(
                "PATCH",
                f"/ordax_dev_agents?agent_name=eq.{query_name}",
                payload,
            )
        else:
            self._request("POST", "/ordax_dev_agents", payload)

    def claim_next_job(self) -> AgentJob | None:
        agent = urllib.parse.quote(self.config.agent_name)
        rows = self._request(
            "GET",
            (
                "/ordax_dev_jobs?"
                f"agent_name=eq.{agent}&status=eq.queued"
                "&select=id,action,payload,project_slug"
                "&order=created_at.asc&limit=1"
            ),
        )
        if not rows:
            return None
        row = rows[0]
        job = AgentJob(
            id=str(row["id"]),
            action=row["action"],
            payload=row.get("payload") or {},
            project_slug=row.get("project_slug"),
        )
        claimed = self._request(
            "PATCH",
            f"/ordax_dev_jobs?id=eq.{urllib.parse.quote(job.id)}&status=eq.queued",
            {
                "status": "running",
                "started_at": datetime.now(timezone.utc).isoformat(),
            },
            prefer="return=representation",
        )
        if not claimed:
            return None
        return job

    def complete(self, job: AgentJob, result: ActionResult) -> None:
        self._request(
            "PATCH",
            f"/ordax_dev_jobs?id=eq.{urllib.parse.quote(job.id)}",
            {
                "status": "succeeded" if result.ok else "failed",
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "result": {
                    "ok": result.ok,
                    "summary": result.summary,
                    "data": result.data,
                },
            },
        )

    def append_event(self, job_id: str, level: str, message: str, data: dict | None = None) -> None:
        self._request(
            "POST",
            "/ordax_dev_job_events",
            {
                "job_id": job_id,
                "level": level,
                "message": message,
                "data": data or {},
            },
        )
