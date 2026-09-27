from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import uuid
from pathlib import Path

import httpx

from ordax_dev_agent.cloudflare_control_plane import CloudflareControlPlane
from ordax_dev_agent.config import AgentConfig
from ordax_dev_agent.models import ActionResult


def _operator_headers(token: str) -> dict[str, str]:
    return {"authorization": f"Bearer {token}"}


def run(base_url: str, operator_token: str) -> None:
    base_url = base_url.rstrip("/")
    operator = httpx.Client(
        base_url=base_url,
        timeout=httpx.Timeout(20.0),
        headers=_operator_headers(operator_token),
    )
    control: CloudflareControlPlane | None = None
    device_id: str | None = None
    try:
        health = operator.get("/health")
        health.raise_for_status()
        if health.json().get("service") != "ordax-control-plane-v3":
            raise RuntimeError("unexpected control-plane health response")

        provision = operator.post("/v3/devices", json={"name": "ci-e2e-device"})
        provision.raise_for_status()
        provisioned = provision.json()
        device_id = str(provisioned["device_id"])
        device_token = str(provisioned["device_token"])

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            state = root / "state"
            state.mkdir(parents=True)
            (state / "device-token.cloudflare-v3.txt").write_text(
                device_token + "\n",
                encoding="utf-8",
            )

            config = AgentConfig(
                agent_name="cloudflare-v3-ci",
                supabase_url=None,
                poll_seconds=1.0,
                state_dir=state,
                agent_repo_path=root / "agent",
                hordax_path=root / "hordax",
                bridge_path=root / "bridge",
                control_plane_protocol="cloudflare-v3",
                development_device_id=device_id,
                control_plane_url=base_url,
            )
            control = CloudflareControlPlane(config)

            control.heartbeat(
                ["agent.status"],
                agent_version="ci-e2e",
                metadata={"test": "cloudflare-v3"},
            )

            queued = operator.post(
                "/v3/jobs",
                json={
                    "device_id": device_id,
                    "action": "agent.status",
                    "payload": {"probe": True},
                },
            )
            queued.raise_for_status()
            job_id = str(queued.json()["job_id"])

            job = control.claim_next_job()
            if job is None:
                raise RuntimeError("device did not receive queued job")
            if job.id != job_id or job.action != "agent.status":
                raise RuntimeError("received job does not match queued job")
            if job.payload != {"probe": True}:
                raise RuntimeError("job payload changed in transport")

            control.append_event(
                job.id,
                "info",
                "cloudflare-v3 e2e progress",
                {"progress_percent": 50},
            )
            control.renew(job)

            artifact_path = root / "probe.txt"
            artifact_bytes = b"ordax-cloudflare-v3-e2e\n"
            artifact_path.write_bytes(artifact_bytes)
            artifact = control.upload_artifact(
                job,
                artifact_path,
                kind="ci-probe",
                metadata={"source": "verify_cloudflare_v3"},
            )
            signed_url = str(artifact.get("signed_url") or "")
            if not signed_url:
                raise RuntimeError("artifact upload did not return signed URL")

            downloaded = httpx.get(signed_url, timeout=20.0)
            downloaded.raise_for_status()
            if downloaded.content != artifact_bytes:
                raise RuntimeError("artifact round-trip changed bytes")

            bad_artifact_id = str(uuid.uuid4())
            bad_upload = httpx.put(
                f"{base_url}/v3/artifacts/{job.id}/{bad_artifact_id}",
                headers={
                    "X-Ordax-Device-Id": device_id,
                    "X-Ordax-Device-Token": device_token,
                    "X-Ordax-Artifact-Name": "bad-probe.txt",
                    "X-Ordax-Artifact-Kind": "ci-negative-integrity-probe",
                    "X-Ordax-Artifact-Sha256": "0" * 64,
                    "X-Ordax-Artifact-Size": str(len(artifact_bytes)),
                    "X-Ordax-Artifact-Metadata": "{}",
                    "content-type": "text/plain",
                },
                content=artifact_bytes,
                timeout=20.0,
            )
            if bad_upload.status_code != 422:
                raise RuntimeError(
                    "artifact checksum mismatch was not rejected: "
                    f"{bad_upload.status_code} {bad_upload.text}"
                )

            control.complete(
                job,
                ActionResult(
                    True,
                    "cloudflare-v3 e2e complete",
                    {"transport": "cloudflare-v3"},
                ),
            )

            status = operator.get(f"/v3/jobs/{job_id}")
            status.raise_for_status()
            body = status.json()
            row = body.get("job") or {}
            if row.get("status") != "succeeded":
                raise RuntimeError(f"job did not finish successfully: {json.dumps(body)}")
            result = row.get("result") or {}
            if result.get("data", {}).get("transport") != "cloudflare-v3":
                raise RuntimeError("terminal result was not persisted")
            events = body.get("events") or []
            if not any(event.get("progress_percent") == 50 for event in events):
                raise RuntimeError("progress event was not persisted")
            artifacts = body.get("artifacts") or []
            if not any(item.get("id") == artifact.get("artifact_id") for item in artifacts):
                raise RuntimeError("artifact metadata was not persisted")
            if any(item.get("id") == bad_artifact_id for item in artifacts):
                raise RuntimeError("rejected artifact checksum was persisted")
    finally:
        active_error = sys.exc_info()[0] is not None
        if control is not None:
            control._drop_socket()
            control.http.close()

        cleanup_error: Exception | None = None
        if device_id:
            try:
                cleanup = operator.delete(f"/v3/devices/{device_id}")
                cleanup.raise_for_status()
                payload = cleanup.json()
                if payload.get("ok") is not True or payload.get("deleted") is not True:
                    raise RuntimeError("remote e2e cleanup was not confirmed")
            except Exception as error:
                cleanup_error = error
        operator.close()

        if cleanup_error is not None:
            message = (
                f"cloudflare-v3 e2e cleanup failed for device {device_id}: "
                f"{cleanup_error}"
            )
            if active_error:
                print(message, file=sys.stderr)
            else:
                raise RuntimeError(message) from cleanup_error


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url",
        default=os.environ.get("ORDAX_E2E_CONTROL_PLANE_URL", "http://127.0.0.1:8787"),
    )
    parser.add_argument(
        "--operator-token",
        default=os.environ.get("ORDAX_E2E_OPERATOR_TOKEN"),
    )
    args = parser.parse_args()
    if not args.operator_token:
        parser.error("--operator-token or ORDAX_E2E_OPERATOR_TOKEN is required")

    run(args.base_url, args.operator_token)
    print("cloudflare-v3 end-to-end OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
