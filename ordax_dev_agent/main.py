from __future__ import annotations

import json
import signal
import sys
import time
from pathlib import Path

from .actions import ActionRegistry
from .config import AgentConfig
from .control_plane import ControlPlane


def main() -> int:
    config = AgentConfig.from_env()
    config.write_public_status()
    registry = ActionRegistry(config)

    print(json.dumps(registry.agent_status({}).data, indent=2))

    if not config.supabase_url or not config.supabase_key:
        print(
            "Supabase is not configured yet. Local action registry is ready; "
            "set ORDAX_SUPABASE_URL and ORDAX_SUPABASE_KEY to enable the control plane."
        )
        return 0

    control = ControlPlane(config)
    stop = False

    def _stop(*_args):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, _stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _stop)

    next_heartbeat = 0.0
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

            control.append_event(job.id, "info", f"starting {job.action}")
            try:
                result = registry.execute(job.action, job.payload)
            except Exception as error:
                from .models import ActionResult
                result = ActionResult(False, f"{type(error).__name__}: {error}")

            control.append_event(
                job.id,
                "info" if result.ok else "error",
                result.summary,
            )
            control.complete(job, result)
        except Exception as error:
            print(f"control-plane error: {error}", file=sys.stderr)
            time.sleep(max(5.0, config.poll_seconds))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
