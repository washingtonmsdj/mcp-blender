from __future__ import annotations

import json
import signal
import sys
import time
from pathlib import Path

from . import __version__
from .actions import ActionRegistry
from .config import AgentConfig
from .control_plane import ControlPlane
from .models import ActionResult
from .status_server import start_status_server


def _agent_metadata(config: AgentConfig) -> dict:
    return {
        "hordax_path": str(config.hordax_path),
        "bridge_path": str(config.bridge_path),
        "platform": sys.platform,
    }


def _upload_result_artifacts(
    control: ControlPlane,
    job,
    result: ActionResult,
) -> list[dict]:
    uploaded: list[dict] = []

    candidates: list[tuple[str, str]] = []
    artifact = result.data.get("artifact")
    if isinstance(artifact, str) and artifact:
        candidates.append((artifact, "unity-gameplay-image"))

    snapshot_path = result.data.get("snapshot_path")
    if isinstance(snapshot_path, str) and snapshot_path:
        candidates.append((snapshot_path, "unity-gameplay-snapshot"))

    for key in ("log_file", "upm_log_file"):
        value = result.data.get(key)
        if isinstance(value, str) and value:
            candidates.append((value, "unity-log"))

    seen: set[str] = set()
    for raw_path, kind in candidates:
        path = Path(raw_path)
        key = str(path).lower()
        if key in seen or not path.is_file():
            continue
        seen.add(key)
        uploaded.append(
            control.upload_artifact(
                job,
                path,
                kind=kind,
                metadata={"action": job.action},
            )
        )

    return uploaded


def main() -> int:
    config = AgentConfig.from_env()
    config.write_public_status()
    registry = ActionRegistry(config)
    runtime = {
        "state": "starting",
        "paired": False,
        "last_job_id": None,
        "last_job_action": None,
        "last_result": None,
    }

    def status_payload() -> dict:
        base = registry.agent_status({}).data
        base["agent_version"] = __version__
        base["runtime"] = dict(runtime)
        return base

    status_server = start_status_server(status_payload)
    runtime["state"] = "ready"
    print(json.dumps(status_payload(), indent=2))

    stop = False

    def _stop(*_args) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, _stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _stop)

    if not config.supabase_url or not config.publishable_key:
        print(
            "Supabase is not configured yet. Local action registry is ready; "
            "configure agent-settings.json to enable the control plane."
        )
        try:
            while not stop:
                time.sleep(1)
        finally:
            runtime["state"] = "stopping"
            status_server.shutdown()
        return 0

    control = ControlPlane(config)

    try:
        paired_now = control.pair_if_needed(
            registry.names,
            agent_version=__version__,
            metadata=_agent_metadata(config),
        )
        runtime["paired"] = True
        if paired_now:
            print("OrdaX Dev Agent paired with Supabase control plane.")
    except Exception as error:
        runtime["state"] = "pairing-error"
        runtime["last_result"] = {"ok": False, "summary": str(error)}
        print(f"pairing error: {error}", file=sys.stderr)
        try:
            while not stop:
                time.sleep(5)
        finally:
            status_server.shutdown()
        return 2

    next_heartbeat = 0.0

    try:
        while not stop:
            now = time.monotonic()
            try:
                if now >= next_heartbeat:
                    control.heartbeat(
                        registry.names,
                        agent_version=__version__,
                        metadata=_agent_metadata(config),
                    )
                    next_heartbeat = now + 20.0

                job = control.claim_next_job()
                if job is None:
                    time.sleep(config.poll_seconds)
                    continue

                runtime["state"] = "busy"
                runtime["last_job_id"] = job.id
                runtime["last_job_action"] = job.action
                control.append_event(job.id, "info", f"starting {job.action}")

                try:
                    result = registry.execute(job.action, job.payload)
                except Exception as error:
                    result = ActionResult(False, f"{type(error).__name__}: {error}")

                if result.ok:
                    try:
                        uploaded = _upload_result_artifacts(control, job, result)
                        if uploaded:
                            result.data["uploaded_artifacts"] = uploaded
                    except Exception as error:
                        result.ok = False
                        result.summary = f"action succeeded but artifact upload failed: {error}"

                control.append_event(
                    job.id,
                    "info" if result.ok else "error",
                    result.summary,
                )
                control.complete(job, result)
                runtime["last_result"] = {
                    "ok": result.ok,
                    "summary": result.summary,
                }
                runtime["state"] = "ready"
            except Exception as error:
                runtime["state"] = "control-plane-error"
                runtime["last_result"] = {"ok": False, "summary": str(error)}
                print(f"control-plane error: {error}", file=sys.stderr)
                time.sleep(max(5.0, config.poll_seconds))
                runtime["state"] = "ready"
    finally:
        runtime["state"] = "stopping"
        try:
            control.heartbeat(
                registry.names,
                agent_version=__version__,
                metadata=_agent_metadata(config),
                status="offline",
            )
        except Exception:
            pass
        status_server.shutdown()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
