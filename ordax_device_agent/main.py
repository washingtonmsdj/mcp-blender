"""Compatibility entrypoint for the OrdaX Device Agent.

The packaged ORDAX Runtime enters here. Before the canonical agent starts, make
one fail-closed attempt to recover an already-enrolled device identity from its
existing local credential. Recovery never enrolls a new device and failure does
not prevent local-only runtime operation.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from ordax_dev_agent.device_identity_recovery import recover_existing_device_identity
from ordax_dev_agent.main import main as _agent_main

__all__ = ["main"]


def _recovery_log(result: dict) -> None:
    try:
        local_app_data = Path(
            os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
        )
        state = Path(
            os.environ.get(
                "ORDAX_AGENT_STATE_DIR",
                local_app_data / "OrdaX" / "DevAgent",
            )
        )
        state.mkdir(parents=True, exist_ok=True)
        safe = {
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "ok": bool(result.get("ok")),
            "state": str(result.get("state") or "unknown"),
            "changed": bool(result.get("changed")),
            "device_id": result.get("device_id"),
        }
        (state / "packaged-runtime-recovery.json").write_text(
            json.dumps(safe, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def main() -> int:
    try:
        recovery = recover_existing_device_identity()
    except Exception as error:
        recovery = {
            "ok": False,
            "state": f"recovery-error:{type(error).__name__}",
            "changed": False,
        }
    _recovery_log(recovery)
    return _agent_main()


if __name__ == "__main__":
    raise SystemExit(main())
