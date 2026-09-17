from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Sequence


MAX_CAPTURE_CHARS = 16000


def _tail(value: str | None) -> str:
    if not value:
        return ""
    return value[-MAX_CAPTURE_CHARS:]


def run_process(
    command: Sequence[str],
    *,
    cwd: str | Path | None = None,
    timeout_seconds: int = 1800,
) -> dict:
    completed = subprocess.run(
        list(command),
        cwd=str(cwd) if cwd is not None else None,
        capture_output=True,
        text=True,
        shell=False,
        timeout=timeout_seconds,
        check=False,
    )

    return {
        "command": list(command),
        "returncode": completed.returncode,
        "ok": completed.returncode == 0,
        "stdout": _tail(completed.stdout),
        "stderr": _tail(completed.stderr),
    }
