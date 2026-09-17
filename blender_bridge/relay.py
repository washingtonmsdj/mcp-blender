#!/usr/bin/env python3
"""GitHub -> Blender relay for the blender-bridge branch.

The relay polls command JSON files committed to this repository, forwards
approved commands to the local Blender MCP addon socket (default 127.0.0.1:9876),
and commits result JSON / preview files back to the same branch.

Only Python's standard library is required.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMMANDS_DIR = ROOT / "blender_bridge" / "commands"
RESULTS_DIR = ROOT / "blender_bridge" / "results"
PREVIEWS_DIR = ROOT / "blender_bridge" / "previews"

HOST = os.environ.get("BLENDER_HOST", "127.0.0.1")
PORT = int(os.environ.get("BLENDER_PORT", "9876"))
BRANCH = os.environ.get("BLENDER_BRIDGE_BRANCH", "blender-bridge")
POLL_SECONDS = float(os.environ.get("BLENDER_BRIDGE_POLL_SECONDS", "3"))
ALLOW_CODE = os.environ.get("BLENDER_BRIDGE_ALLOW_CODE", "0") == "1"

READ_ONLY_COMMANDS = {
    "get_scene_info",
    "get_object_info",
    "get_viewport_screenshot",
    "get_polyhaven_status",
    "get_hyper3d_status",
    "get_sketchfab_status",
}

WRITE_COMMANDS = {
    "execute_code",
    "set_texture",
    "download_polyhaven_asset",
}


def log(message: str) -> None:
    print(f"[blender-bridge] {message}", flush=True)


def run_git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed ({proc.returncode})\n"
            f"stdout: {proc.stdout.strip()}\n"
            f"stderr: {proc.stderr.strip()}"
        )
    return proc


def ensure_repo_ready() -> None:
    if not (ROOT / ".git").exists():
        raise RuntimeError(f"{ROOT} is not a Git repository")
    current = run_git("branch", "--show-current").stdout.strip()
    if current != BRANCH:
        raise RuntimeError(
            f"Checkout branch '{BRANCH}' before starting the relay. Current branch: '{current}'"
        )
    COMMANDS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)


def git_pull() -> None:
    proc = run_git("pull", "--rebase", "origin", BRANCH, check=False)
    if proc.returncode != 0:
        log(f"git pull warning: {proc.stderr.strip() or proc.stdout.strip()}")


def git_publish(message: str) -> None:
    run_git("add", "blender_bridge/results", "blender_bridge/previews")
    status = run_git("status", "--porcelain").stdout.strip()
    if not status:
        return
    run_git("commit", "-m", message)
    run_git("pull", "--rebase", "origin", BRANCH)
    run_git("push", "origin", BRANCH)


def receive_json(sock: socket.socket, timeout: float = 180.0) -> dict[str, Any]:
    sock.settimeout(timeout)
    chunks: list[bytes] = []
    while True:
        chunk = sock.recv(8192)
        if not chunk:
            if not chunks:
                raise ConnectionError("Blender closed the socket without a response")
            break
        chunks.append(chunk)
        data = b"".join(chunks)
        try:
            return json.loads(data.decode("utf-8"))
        except json.JSONDecodeError:
            continue
    return json.loads(b"".join(chunks).decode("utf-8"))


def send_blender_command(command_type: str, params: dict[str, Any]) -> Any:
    payload = {"type": command_type, "params": params}
    with socket.create_connection((HOST, PORT), timeout=8.0) as sock:
        sock.sendall(json.dumps(payload).encode("utf-8"))
        response = receive_json(sock)
    if response.get("status") == "error":
        raise RuntimeError(response.get("message", "Unknown Blender error"))
    return response.get("result", {})


def validate_command(command: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    command_type = command.get("type")
    params = command.get("params", {})
    if not isinstance(command_type, str) or not command_type:
        raise ValueError("Command requires a non-empty string field 'type'")
    if not isinstance(params, dict):
        raise ValueError("Command field 'params' must be a JSON object")
    if command_type in READ_ONLY_COMMANDS:
        return command_type, params
    if command_type in WRITE_COMMANDS:
        if not ALLOW_CODE:
            raise PermissionError(
                f"Write command '{command_type}' is disabled. Start relay with "
                "BLENDER_BRIDGE_ALLOW_CODE=1 after you are ready to allow scene changes."
            )
        return command_type, params
    raise PermissionError(f"Command type '{command_type}' is not in the relay allowlist")


def prepare_params(command_id: str, command_type: str, params: dict[str, Any]) -> dict[str, Any]:
    params = dict(params)
    if command_type == "get_viewport_screenshot":
        preview_path = PREVIEWS_DIR / f"{command_id}.png"
        params.setdefault("max_size", 900)
        params.setdefault("format", "png")
        params["filepath"] = str(preview_path)
    return params


def result_path_for(command_file: Path) -> Path:
    return RESULTS_DIR / f"{command_file.stem}.json"


def process_command(command_file: Path) -> None:
    result_file = result_path_for(command_file)
    if result_file.exists():
        return

    started = time.time()
    command_id = command_file.stem
    try:
        # utf-8-sig transparently accepts both plain UTF-8 and PowerShell's UTF-8 BOM.
        command = json.loads(command_file.read_text(encoding="utf-8-sig"))
        if command.get("enabled", True) is False:
            return
        command_type, params = validate_command(command)
        params = prepare_params(command_id, command_type, params)
        log(f"Executing {command_file.name}: {command_type}")
        result = send_blender_command(command_type, params)
        payload: dict[str, Any] = {
            "id": command.get("id", command_id),
            "command_file": command_file.name,
            "type": command_type,
            "status": "success",
            "duration_seconds": round(time.time() - started, 3),
            "result": result,
        }
        preview = PREVIEWS_DIR / f"{command_id}.png"
        if preview.exists():
            payload["preview"] = str(preview.relative_to(ROOT)).replace("\\", "/")
    except Exception as exc:
        payload = {
            "id": command_id,
            "command_file": command_file.name,
            "status": "error",
            "duration_seconds": round(time.time() - started, 3),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        log(f"Command failed: {exc}")

    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    git_publish(f"bridge: result for {command_id}")
    log(f"Published result: {result_file.relative_to(ROOT)}")


def pending_commands() -> list[Path]:
    return [
        path
        for path in sorted(COMMANDS_DIR.glob("*.json"))
        if not result_path_for(path).exists()
    ]


def main() -> int:
    try:
        ensure_repo_ready()
    except Exception as exc:
        log(str(exc))
        return 2

    log(f"Watching branch '{BRANCH}'")
    log(f"Blender endpoint: {HOST}:{PORT}")
    log(f"Scene-changing commands enabled: {ALLOW_CODE}")
    log("Press Ctrl+C to stop")

    while True:
        try:
            git_pull()
            for command_file in pending_commands():
                process_command(command_file)
        except KeyboardInterrupt:
            log("Stopped")
            return 0
        except Exception as exc:
            log(f"Loop error: {exc}")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    sys.exit(main())
