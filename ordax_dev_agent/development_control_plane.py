from __future__ import annotations

import base64
import hashlib
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

from .config import AgentConfig
from .models import ActionResult, AgentJob


class DeviceAuthorizationError(RuntimeError):
    """The supervisor must reauthenticate this device before restarting."""


class TransientDeliveryError(RuntimeError):
    """Transport failure eligible for an identical terminal-report retry."""


class DevelopmentControlPlane:
    """Client for the OrdaX development-device protocol v2.

    This transport is deliberately engineering-only. It authenticates with a
    device-scoped credential and never reuses product/account credentials.
    """

    uses_long_poll = True

    def __init__(self, config: AgentConfig):
        if not config.supabase_url:
            raise RuntimeError("Supabase URL is required for development control plane v2.")
        if not config.development_device_id:
            raise RuntimeError("ORDAX_DEVICE_ID is required for development control plane v2.")

        self.config = config
        self.endpoint = (
            config.supabase_url.rstrip("/") + "/functions/v1/ordax-development-device"
        )
        self.device_id = str(config.development_device_id)
        try:
            uuid.UUID(self.device_id)
        except ValueError as error:
            raise RuntimeError("ORDAX_DEVICE_ID must be a UUID.") from error

        token_path = config.state_dir / "device-token.txt"
        self.device_token = (
            os.environ.get("ORDAX_DEVICE_TOKEN")
            or self._read_secret(token_path)
        )
        if not self.device_token:
            raise RuntimeError(
                "Development device token is missing. Set ORDAX_DEVICE_TOKEN or "
                f"provision {token_path} with mode 0600/owner-only ACL."
            )
        if not 32 <= len(self.device_token) <= 512:
            raise RuntimeError("Development device token length is invalid.")

        self.agent_instance_id = str(uuid.uuid4())
        self.boot_id = str(uuid.uuid4())
        self._jobs: dict[str, AgentJob] = {}
        self.http = httpx.Client(
            timeout=httpx.Timeout(45.0),
            limits=httpx.Limits(
                max_connections=8,
                max_keepalive_connections=4,
                keepalive_expiry=30.0,
            ),
            headers={
                "content-type": "application/json",
                "user-agent": "OrdaX-Device-Agent/1.20",
                "X-Ordax-Device-Token": self.device_token,
            },
        )

    @staticmethod
    def _read_secret(path: Path) -> str | None:
        if not path.is_file():
            return None
        value = path.read_text(encoding="utf-8").strip()
        return value or None

    def _call(self, operation: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = {
            "device_id": self.device_id,
            "operation": operation,
            **(payload or {}),
        }
        try:
            response = self.http.post(self.endpoint, json=body)
        except httpx.HTTPError as error:
            raise TransientDeliveryError(
                f"development control-plane request failed: {type(error).__name__}: {error}"
            ) from error
        raw = response.text
        if response.status_code == 401:
            raise DeviceAuthorizationError("DEVICE_CREDENTIAL_REJECTED")
        if response.status_code in {408, 429, 500, 502, 503, 504}:
            raise TransientDeliveryError(f"development control-plane HTTP {response.status_code}")
        if response.status_code >= 400:
            raise RuntimeError(
                f"development control-plane HTTP {response.status_code}: {raw[-4000:]}"
            )
        result = response.json() if raw else {}
        if not isinstance(result, dict):
            raise RuntimeError("development control-plane returned a non-object response")
        if result.get("ok") is False:
            raise RuntimeError(
                f"development control-plane error: {result.get('error', 'unknown')}"
            )
        return result

    @property
    def is_paired(self) -> bool:
        return True

    def pair_if_needed(
        self,
        capabilities: list[str],
        *,
        agent_version: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        del capabilities, agent_version, metadata
        return False

    def heartbeat(
        self,
        actions: list[str],
        *,
        agent_version: str,
        metadata: dict[str, Any] | None = None,
        status: str = "online",
        last_error: str | None = None,
    ) -> None:
        del actions, agent_version, metadata, last_error
        if status == "offline":
            return
        self._call(
            "heartbeat",
            {
                "boot_id": self.boot_id,
                "runtime_mode": "developer",
            },
        )

    @staticmethod
    def _decode_payload(row: dict[str, Any]) -> dict[str, Any]:
        encoded = row.get("payload_canonical_b64")
        expected = str(row.get("payload_sha256") or "").lower()
        if not isinstance(encoded, str) or len(expected) != 64:
            raise RuntimeError("development job payload envelope is incomplete")
        try:
            raw = base64.b64decode(encoded, validate=True)
        except Exception as error:
            raise RuntimeError("development job payload is not valid base64") from error
        observed = hashlib.sha256(raw).hexdigest()
        if observed != expected:
            raise RuntimeError("development job payload digest mismatch")
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RuntimeError("development job payload is not valid UTF-8 JSON") from error
        if not isinstance(payload, dict):
            raise RuntimeError("development job payload must be an object")
        return payload

    @staticmethod
    def _dispatch(row: dict[str, Any], payload: dict[str, Any]) -> tuple[str, dict[str, Any], str | None]:
        capability = str(row.get("capability") or row.get("operation") or "")
        if capability == "ordax.dev.adapter.invoke":
            allowed = {"adapter", "action", "payload", "project"}
            if set(payload) - allowed:
                raise RuntimeError("adapter invocation contains unsupported fields")
            adapter = payload.get("adapter")
            action = payload.get("action")
            action_payload = payload.get("payload", {})
            project = payload.get("project")
            if not isinstance(action_payload, dict):
                raise RuntimeError("adapter invocation payload must be an object")
            if project is not None and not isinstance(project, str):
                raise RuntimeError("adapter invocation project must be a string")

            if adapter == "blender":
                if not isinstance(action, str) or not action.startswith("blender."):
                    raise RuntimeError("adapter invocation action is not a Blender action")
                return action, action_payload, project

            if adapter == "workspace":
                if action != "workspace.bind_project":
                    raise RuntimeError("adapter invocation workspace action is not allowed")
                if project is not None:
                    raise RuntimeError("workspace binding must not target an existing project")
                return action, action_payload, None

            raise RuntimeError("adapter invocation is not an allowed capability")

        if capability.startswith(("blender.", "unity.", "git.", "project.", "projects.", "artifact.", "observation.", "game_assets.", "geo.", "visual.", "agent.")):
            return capability, payload, payload.get("project") if isinstance(payload.get("project"), str) else None

        raise RuntimeError(f"development capability is not owned by Device Agent: {capability}")

    def _execution_context(self, job: AgentJob) -> dict[str, Any]:
        required = {
            "effect_id": job.effect_id,
            "attempt_id": job.attempt_id,
            "lease_id": job.lease_token,
            "execution_epoch": job.execution_epoch,
            "agent_instance_id": job.agent_instance_id,
            "boot_id": job.boot_id,
        }
        if any(value in (None, "") for value in required.values()):
            raise RuntimeError("development job execution context is incomplete")
        return {
            "job_id": job.id,
            **required,
        }

    def claim_next_job(self) -> AgentJob | None:
        response = self._call(
            "wait",
            {
                "agent_instance_id": self.agent_instance_id,
                "boot_id": self.boot_id,
                "wait_ms": 20_000,
            },
        )
        row = response.get("job")
        if not row:
            return None
        if not isinstance(row, dict):
            raise RuntimeError("development job envelope must be an object")

        payload = self._decode_payload(row)
        action, action_payload, project = self._dispatch(row, payload)
        job = AgentJob(
            id=str(row["job_id"]),
            action=action,
            payload=action_payload,
            project_slug=project,
            lease_token=str(row.get("lease_id") or ""),
            effect_id=str(row.get("effect_id") or ""),
            attempt_id=str(row.get("attempt_id") or ""),
            execution_epoch=int(row.get("execution_epoch") or 0),
            agent_instance_id=self.agent_instance_id,
            boot_id=self.boot_id,
            payload_sha256=str(row.get("payload_sha256") or ""),
        )
        self._call("start", self._execution_context(job))
        self._jobs[job.id] = job
        return job

    def append_event(
        self,
        job_id: str,
        level: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        job = self._jobs.get(job_id)
        if job is None:
            return
        progress_percent = None
        if isinstance(data, dict) and isinstance(data.get("progress_percent"), int):
            progress_percent = max(0, min(100, int(data["progress_percent"])))
        self._call(
            "progress",
            {
                **self._execution_context(job),
                "progress_percent": progress_percent,
                "stage": str(level)[:96],
                "message": str(message)[:512],
            },
        )

    def renew(self, job: AgentJob) -> dict[str, Any]:
        return self._call("lease_heartbeat", self._execution_context(job))

    @staticmethod
    def _canonical_result(result: ActionResult) -> tuple[dict[str, Any], str]:
        body = {
            "ok": bool(result.ok),
            "summary": str(result.summary),
            "data": result.data if isinstance(result.data, dict) else {},
        }
        encoded = json.dumps(
            body,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return body, hashlib.sha256(encoded).hexdigest()

    def complete(self, job: AgentJob, result: ActionResult) -> None:
        body, digest = self._canonical_result(result)
        status = "succeeded" if result.ok else "failed"
        report = {
                **self._execution_context(job),
                "report_id": str(uuid.uuid4()),
                "status": status,
                "exit_code": 0 if result.ok else 1,
                "result": body,
                "result_sha256": digest,
                "error_code": None if result.ok else "device_agent_action_failed",
            }
        # Reuse both report id and payload when an accepted response was lost.
        # Never retry the Blender action or a permanent rejection/auth failure.
        for attempt in range(3):
            try:
                self._call("report", report)
                break
            except TransientDeliveryError:
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
        self._jobs.pop(job.id, None)

    def upload_artifact(
        self,
        job: AgentJob,
        path: str | Path,
        *,
        kind: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        del job
        file_path = Path(path).expanduser().resolve()
        if not file_path.is_file():
            raise FileNotFoundError(file_path)
        with file_path.open("rb") as handle:
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
        return {
            "delivery": "local-only-v2-artifact-gateway-pending",
            "kind": kind,
            "local_name": file_path.name,
            "sha256": digest,
            "size_bytes": file_path.stat().st_size,
            "metadata": metadata or {},
        }
