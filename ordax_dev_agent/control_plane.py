from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import httpx
from pathlib import Path
from typing import Any

from supabase import create_client

from .config import AgentConfig
from .identity import machine_id
from .models import ActionResult, AgentJob


class ControlPlane:
    """Authenticated client for the OrdaX Supabase Edge Function."""

    def __init__(self, config: AgentConfig):
        if not config.supabase_url or not config.publishable_key:
            raise RuntimeError(
                "Supabase URL and publishable key are required for the control plane."
            )

        self.config = config
        self.endpoint = (
            config.supabase_url.rstrip("/") + "/functions/v1/ordax-dev-agent"
        )
        self.publishable_key = config.publishable_key
        self.token_path = config.state_dir / "agent-token.txt"
        self.pairing_path = config.state_dir / "pairing-code.txt"
        self.agent_token = self._read_secret(self.token_path)
        self.storage = create_client(config.supabase_url, config.publishable_key)
        self.http = httpx.Client(
            timeout=httpx.Timeout(45.0),
            limits=httpx.Limits(
                max_connections=8,
                max_keepalive_connections=4,
                keepalive_expiry=30.0,
            ),
            headers={
                "apikey": self.publishable_key,
                "Authorization": f"Bearer {self.publishable_key}",
                "content-type": "application/json",
                "user-agent": "OrdaX-Dev-Agent/0.1",
            },
        )

    @staticmethod
    def _read_secret(path: Path) -> str | None:
        if not path.is_file():
            return None
        value = path.read_text(encoding="utf-8").strip()
        return value or None

    def _write_token(self, token: str) -> None:
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        self.token_path.write_text(token.strip() + "\n", encoding="utf-8")
        try:
            os.chmod(self.token_path, 0o600)
        except OSError:
            pass
        self.agent_token = token.strip()

    def _call(
        self,
        op: str,
        payload: dict[str, Any] | None = None,
        *,
        authenticated: bool = True,
    ) -> dict[str, Any]:
        body = {"op": op, **(payload or {})}
        headers: dict[str, str] = {}
        if authenticated:
            if not self.agent_token:
                raise RuntimeError("OrdaX Dev Agent is not paired.")
            headers["x-ordax-agent-token"] = self.agent_token

        try:
            response = self.http.post(
                self.endpoint,
                json=body,
                headers=headers,
            )
        except httpx.HTTPError as error:
            raise RuntimeError(
                f"control-plane request failed: {type(error).__name__}: {error}"
            ) from error

        raw = response.text
        if response.status_code >= 400:
            raise RuntimeError(
                f"control-plane HTTP {response.status_code}: {raw[-4000:]}"
            )

        result = response.json() if raw else {}
        if isinstance(result, dict) and result.get("error"):
            raise RuntimeError(
                f"control-plane error: {result['error']}: "
                f"{result.get('detail', '')}"
            )
        return result

    @property
    def is_paired(self) -> bool:
        return bool(self.agent_token)

    def pair_if_needed(
        self,
        capabilities: list[str],
        *,
        agent_version: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        if self.agent_token:
            return False

        pairing_code = self._read_secret(self.pairing_path)
        if not pairing_code:
            raise RuntimeError(
                f"Agent is unpaired and pairing code is missing: {self.pairing_path}"
            )

        response = self._call(
            "register",
            {
                "pairing_code": pairing_code,
                "agent_name": self.config.agent_name,
                "machine_id": machine_id(),
                "capabilities": capabilities,
                "agent_version": agent_version,
                "metadata": metadata or {},
            },
            authenticated=False,
        )

        token = str(response.get("agent_token") or "")
        if not token:
            raise RuntimeError("Pairing succeeded without returning an agent token.")

        self._write_token(token)
        try:
            self.pairing_path.unlink()
        except OSError:
            pass
        return True

    def heartbeat(
        self,
        actions: list[str],
        *,
        agent_version: str,
        metadata: dict[str, Any] | None = None,
        status: str = "online",
        last_error: str | None = None,
    ) -> None:
        self._call(
            "heartbeat",
            {
                "status": status,
                "capabilities": actions,
                "agent_version": agent_version,
                "metadata": metadata or {},
                "last_error": last_error,
            },
        )

    def claim_next_job(self) -> AgentJob | None:
        response = self._call("claim")
        row = response.get("job")
        if not row:
            return None

        return AgentJob(
            id=str(row["id"]),
            action=str(row["action"]),
            payload=row.get("payload") or {},
            project_slug=row.get("project_slug"),
            lease_token=str(row.get("lease_token") or ""),
        )

    def append_event(
        self,
        job_id: str,
        level: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        self._call(
            "event",
            {
                "job_id": job_id,
                "level": level,
                "message": message,
                "data": data or {},
            },
        )

    def renew(self, job: AgentJob) -> dict[str, Any]:
        if not job.lease_token:
            raise RuntimeError("Cannot renew a job without a lease token.")

        return self._call(
            "renew",
            {
                "job_id": job.id,
                "lease_token": job.lease_token,
            },
        )

    def complete(self, job: AgentJob, result: ActionResult) -> None:
        self._call(
            "complete",
            {
                "job_id": job.id,
                "lease_token": job.lease_token,
                "ok": result.ok,
                "result": {
                    "ok": result.ok,
                    "summary": result.summary,
                    "data": result.data,
                },
            },
        )

    def upload_artifact(
        self,
        job: AgentJob,
        path: str | Path,
        *,
        kind: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        file_path = Path(path).expanduser().resolve()
        if not file_path.is_file():
            raise FileNotFoundError(file_path)

        ticket = self._call(
            "upload_ticket",
            {
                "job_id": job.id,
                "file_name": file_path.name,
                "kind": kind,
            },
        )

        bucket = str(ticket["bucket"])
        storage_path = str(ticket["path"])
        token = str(ticket["token"])
        artifact_id = str(ticket["artifact_id"])

        with file_path.open("rb") as stream:
            self.storage.storage.from_(bucket).upload_to_signed_url(
                path=storage_path,
                token=token,
                file=stream,
            )

        digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
        size = file_path.stat().st_size
        content_type = mimetypes.guess_type(file_path.name)[0]

        artifact_metadata = {
            "state": "uploaded",
            "local_name": file_path.name,
            "content_type": content_type,
            **(metadata or {}),
        }

        finalized = self._call(
            "artifact_done",
            {
                "job_id": job.id,
                "artifact_id": artifact_id,
                "sha256": digest,
                "size_bytes": size,
                "metadata": artifact_metadata,
            },
        )

        return {
            "artifact_id": artifact_id,
            "bucket": bucket,
            "storage_path": storage_path,
            "sha256": digest,
            "size_bytes": size,
            "signed_url": finalized.get("signed_url"),
        }



def build_control_plane(config: AgentConfig):
    """Select the configured remote transport without weakening either authority."""

    protocol = str(config.control_plane_protocol or "legacy-v1").strip().lower()
    if protocol == "legacy-v1":
        return ControlPlane(config)
    if protocol == "development-v2":
        from .development_control_plane import DevelopmentControlPlane

        return DevelopmentControlPlane(config)
    raise ValueError(f"Unsupported control-plane protocol: {protocol}")
