from __future__ import annotations

import json
import signal
import sys
import time

from .actions import ActionRegistry
from .config import AgentConfig
from .control_plane import ControlPlane
from .models import ActionResult
from .status_server import start_status_server


def main() -> int:
    config = AgentConfig.from_env()
    config.write_public_status()
    registry = ActionRegistry(config)
    runtime = {
        "state": "starting",
        "last_job_id": None,
        "last_job_action": None,
        "last_result": None,
    }

    def status_payload() -> dict:
        base = registry.agent_status({}).data
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

    if not config.supabase_url or not config.supabase_key:
        print(
            "Supabase is not configured yet. Local action registry is ready; "
            "set ORDAX_SUPABASE_URL and ORDAX_SUPABASE_KEY to enable the control plane."
        )
        try:
            while not stop:
                time.sleep(1)
        finally:
            runtime["state"] = "stopping"
            status_server.shutdown()
        return 0

    control = ControlPlane(config)
    next_heartbeat = 0.0

    try:
        while not stop:
            now = time.monotonic()
            try:
                if now >= next_heartbeat:
                    control.heartbeat(registry.names)
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
                print(f"control-plane error: {error}", file=sys.stderr)
                time.sleep(max(5.0, config.poll_seconds))
                runtime["state"] = "ready"
    finally:
        runtime["state"] = "stopping"
        status_server.shutdown()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
