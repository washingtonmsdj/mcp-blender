from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from .openai_tunnel import OpenAITunnelError, OpenAITunnelManager

MUTEX_NAME = "Local\\ORDAX_OpenAI_MCP_Tunnel"
ERROR_ALREADY_EXISTS = 183


def _single_instance_mutex():
    if os.name != "nt":
        raise OpenAITunnelError("OpenAI tunnel runner is supported on Windows only")
    handle = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if not handle:
        raise ctypes.WinError()
    if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        ctypes.windll.kernel32.CloseHandle(handle)
        return None
    return handle


def _write_status(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)


def main() -> int:
    mutex = _single_instance_mutex()
    if mutex is None:
        return 0
    manager = OpenAITunnelManager()
    config = manager._read_config()
    client = manager.tunnel_client()
    if not client or not config.get("tunnel_id"):
        return 2
    try:
        api_key = manager.load_runtime_api_key()
    except Exception as error:
        manager.log_path.parent.mkdir(parents=True, exist_ok=True)
        manager.log_path.write_text(f"credential error: {error}\n", encoding="utf-8")
        return 3

    env = dict(os.environ)
    env["CONTROL_PLANE_API_KEY"] = api_key
    command = [
        str(client),
        "run",
        "--profile",
        str(config.get("profile") or "ordax-studio"),
        "--profile-dir",
        str(manager.profiles_dir),
    ]
    manager.log_path.parent.mkdir(parents=True, exist_ok=True)
    started_at = time.time()
    with manager.log_path.open("a", encoding="utf-8", errors="replace") as log:
        log.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] starting ORDAX OpenAI MCP Tunnel\n")
        log.flush()
        child = subprocess.Popen(
            command,
            cwd=str(manager.state_dir),
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
        )
        _write_status(
            manager.status_path,
            {
                "pid": child.pid,
                "started_at": started_at,
                "profile": config.get("profile"),
                "tunnel_id": config.get("tunnel_id"),
                "exit_code": None,
            },
        )
        exit_code = child.wait()
        _write_status(
            manager.status_path,
            {
                "pid": child.pid,
                "started_at": started_at,
                "stopped_at": time.time(),
                "profile": config.get("profile"),
                "tunnel_id": config.get("tunnel_id"),
                "exit_code": exit_code,
            },
        )
        log.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] tunnel exited code={exit_code}\n")
        log.flush()
    ctypes.windll.kernel32.CloseHandle(mutex)
    return int(exit_code)


if __name__ == "__main__":
    raise SystemExit(main())
