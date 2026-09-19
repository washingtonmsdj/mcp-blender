from __future__ import annotations

import json
import signal
import sys
import threading
import time
from pathlib import Path

from . import __version__
from .actions import ActionRegistry
from .config import AgentConfig
from .control_plane import ControlPlane
from .models import ActionResult
from .status_server import start_status_server
from .projects import load_projects


def _agent_metadata(config: AgentConfig) -> dict:
    return {
        "hordax_path": str(config.hordax_path),
        "bridge_path": str(config.bridge_path),
        "platform": sys.platform,
        "projects": [project.public() for project in load_projects(config).values()],
    }


def _upload_result_artifacts(
    control: ControlPlane,
    job,
    result: ActionResult,
    cache: dict | None = None,
) -> list[dict]:
    uploaded: list[dict] = []
    if cache is None:
        cache = {}

    candidates: list[tuple[str, str]] = []
    artifact = result.data.get("artifact")
    if isinstance(artifact, str) and artifact:
        candidates.append((artifact, "visual-image"))

    snapshot_path = result.data.get("snapshot_path")
    if isinstance(snapshot_path, str) and snapshot_path:
        candidates.append((snapshot_path, "scene-snapshot"))

    for artifact in result.data.get("artifacts", []):
        candidates.append((artifact["path"], artifact.get("kind", "artifact")))

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
        if key not in cache:
            cache[key] = control.upload_artifact(
                job,
                path,
                kind=kind,
                metadata={"action": job.action},
            )
        uploaded.append(cache[key])

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
    runtime["state"] = (
        "pairing"
        if config.supabase_url and config.publishable_key
        else "local-ready"
    )
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

    while not stop and not runtime["paired"]:
        try:
            paired_now = control.pair_if_needed(
                registry.names,
                agent_version=__version__,
                metadata=_agent_metadata(config),
            )
            runtime["paired"] = True
            runtime["state"] = "ready"
            runtime["last_result"] = {
                "ok": True,
                "summary": "agent paired" if paired_now else "agent token loaded",
            }
            if paired_now:
                print("OrdaX Dev Agent paired with Supabase control plane.")
        except Exception as error:
            runtime["state"] = "pairing-error"
            runtime["last_result"] = {"ok": False, "summary": str(error)}
            print(f"pairing error: {error}", file=sys.stderr)
            time.sleep(max(5.0, config.poll_seconds))

    if stop:
        status_server.shutdown()
        return 0

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
                runtime["progress"] = None
                control.append_event(job.id, "info", f"starting {job.action}")
                artifact_cache = {}

                def publish_observation(observation: dict) -> None:
                    progress = {"index": observation["index"], "ok": observation["ok"],
                                "observed_at": observation["observed_at"],
                                "duration_seconds": observation["duration_seconds"]}
                    runtime["progress"] = progress
                    try:
                        progress["artifacts"] = _upload_result_artifacts(
                            control, job, ActionResult(observation["ok"], observation["summary"], observation),
                            artifact_cache,
                        )
                        control.append_event(job.id, "info", "visual observation available", progress)
                    except Exception as error:
                        progress["delivery_error"] = str(error)
                        # Final upload retries missing artifacts without repeating app actions.
                    runtime["progress"] = progress

                registry.on_observation = publish_observation

                keepalive_stop = threading.Event()

                def _keep_job_alive() -> None:
                    while not keepalive_stop.wait(20.0):
                        try:
                            control.renew(job)
                        except Exception as error:
                            print(
                                f"job keepalive error for {job.id}: {error}",
                                file=sys.stderr,
                            )

                keepalive_thread = threading.Thread(
                    target=_keep_job_alive,
                    name=f"ordax-job-{job.id[:8]}-keepalive",
                    daemon=True,
                )
                keepalive_thread.start()

                try:
                    try:
                        result = registry.execute(job.action, job.action_payload())
                    except Exception as error:
                        result = ActionResult(False, f"{type(error).__name__}: {error}")
                    try:
                        uploaded = _upload_result_artifacts(control, job, result, artifact_cache)
                        if uploaded:
                            result.data["uploaded_artifacts"] = uploaded
                    except Exception as error:
                        result.data["upload_error"] = str(error)
                        result.ok = False
                        result.summary += "; artifact upload failed"
                finally:
                    registry.on_observation = None
                    keepalive_stop.set()
                    keepalive_thread.join(timeout=2.0)

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

                if (
                    job.action == "agent.update"
                    and result.ok
                    and result.data.get("restart_required")
                ):
                    runtime["state"] = "restarting"
                    return 42

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
