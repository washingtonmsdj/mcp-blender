from __future__ import annotations

import os
import re
import shlex
import subprocess
import time
import uuid
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .config import default_unity_project, find_blender, find_unity, read_unity_project_version
from .process import run_process


mcp = FastMCP("blender-unity")

_UNITY_ERROR_PATTERNS = (
    re.compile(r"\berror CS\d{4}\b", re.IGNORECASE),
    re.compile(r"Scripts have compiler errors", re.IGNORECASE),
    re.compile(r"Compilation failed", re.IGNORECASE),
    re.compile(r"Aborting batchmode due to failure", re.IGNORECASE),
    re.compile(r"executeMethod.*could not be found", re.IGNORECASE),
    re.compile(r"\[Package Manager\].*Failed to start.*local server process", re.IGNORECASE),
    re.compile(r"\[Package Manager\].*Could not connect to IPC stream", re.IGNORECASE),
)


def _required_file(path: Path | None, label: str) -> Path:
    if path is None or not path.is_file():
        raise FileNotFoundError(f"{label} executable was not found.")
    return path


def _required_project(project_path: str | None) -> Path:
    if project_path:
        project = Path(project_path).expanduser().resolve()
    else:
        project = default_unity_project()

    if project is None or not project.is_dir():
        raise FileNotFoundError(
            "Unity project was not found. Pass project_path or set DEFAULT_UNITY_PROJECT."
        )

    if not (project / "Assets").is_dir():
        raise ValueError(f"{project} does not look like a Unity project: Assets/ is missing.")

    return project


def _read_tail(path: Path, max_chars: int = 40000) -> str:
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[-max_chars:]



def _has_upm_startup_failure(log_text: str) -> bool:
    return bool(
        re.search(r"\[Package Manager\].*Failed to start.*local server process", log_text, re.IGNORECASE)
        or re.search(r"\[Package Manager\].*Could not connect to IPC stream", log_text, re.IGNORECASE)
        or re.search(r"\[Package Manager\].*Could not establish a connection", log_text, re.IGNORECASE)
    )


def _managed_upm_executable(unity: Path) -> Path:
    return (
        unity.parent
        / "Data"
        / "Resources"
        / "PackageManager"
        / "Server"
        / "UnityPackageManager.exe"
    )


def _run_with_managed_upm(
    command: list[str],
    project: Path,
    unity_log_file: Path,
    upm_log_file: Path,
    timeout_seconds: int,
) -> dict:
    unity = Path(command[0])
    upm = _managed_upm_executable(unity)

    if os.name != "nt" or not upm.is_file():
        return {
            "ok": False,
            "returncode": None,
            "stdout": "",
            "stderr": f"Managed UPM fallback unavailable: {upm}",
            "command": command,
        }

    token = f"Upm-{os.getpid()}-{uuid.uuid4().hex[:8]}"
    server_path = f"Unity-{token}"
    managed_log = upm_log_file.with_name(upm_log_file.stem + "-managed.log")

    managed_log.parent.mkdir(parents=True, exist_ok=True)
    try:
        managed_log.unlink(missing_ok=True)
    except TypeError:
        if managed_log.exists():
            managed_log.unlink()

    upm_command = [
        str(upm),
        "server",
        "-s",
        str(os.getpid()),
        "--ipc-path",
        server_path,
        "-l",
        "2",
        "--log-file",
        str(managed_log),
    ]

    upm_process = subprocess.Popen(
        upm_command,
        cwd=str(project),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        shell=False,
    )

    try:
        deadline = time.monotonic() + 12.0
        ready = False
        while time.monotonic() < deadline:
            if upm_process.poll() is not None:
                break
            text = _read_tail(managed_log, max_chars=12000)
            if "IPC server started" in text:
                ready = True
                break
            time.sleep(0.2)

        if not ready:
            stderr = ""
            if upm_process.poll() is not None and upm_process.stderr is not None:
                try:
                    stderr = upm_process.stderr.read()[-8000:]
                except Exception:
                    stderr = ""
            return {
                "ok": False,
                "returncode": upm_process.poll(),
                "stdout": "",
                "stderr": "Managed UPM server did not become ready.\n" + stderr,
                "command": upm_command,
                "managed_upm": True,
                "managed_upm_command": upm_command,
                "managed_upm_log_file": str(managed_log),
                "managed_upm_log": _read_tail(managed_log),
            }

        retry_command = list(command) + ["-upmIpcPath", token]
        result = run_process(
            retry_command,
            cwd=project,
            timeout_seconds=max(1, timeout_seconds),
        )
        result["managed_upm"] = True
        result["managed_upm_command"] = upm_command
        result["managed_upm_log_file"] = str(managed_log)
        result["managed_upm_log"] = _read_tail(managed_log)
        return result
    finally:
        if upm_process.poll() is None:
            upm_process.terminate()
            try:
                upm_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                upm_process.kill()
                upm_process.wait(timeout=5)


def _unity_result(
    command: list[str],
    project: Path,
    log_file: Path,
    upm_log_file: Path,
    timeout_seconds: int,
) -> dict:
    result = run_process(
        command,
        cwd=project,
        timeout_seconds=max(1, timeout_seconds),
    )

    log_text = _read_tail(log_file)
    upm_log_text = _read_tail(upm_log_file)

    if _has_upm_startup_failure(log_text):
        first_result = dict(result)
        result = _run_with_managed_upm(
            command,
            project,
            log_file,
            upm_log_file,
            timeout_seconds,
        )
        result["retried_after_upm_startup_failure"] = True
        result["first_attempt_returncode"] = first_result.get("returncode")
        log_text = _read_tail(log_file)
        upm_log_text = _read_tail(upm_log_file)

    detected_errors: list[str] = []

    for pattern in _UNITY_ERROR_PATTERNS:
        if pattern.search(log_text):
            detected_errors.append(pattern.pattern)

    result["log_file"] = str(log_file)
    result["upm_log_file"] = str(upm_log_file)
    result["unity_log"] = log_text
    result["upm_log"] = upm_log_text
    result["detected_error_patterns"] = detected_errors
    result["ok"] = bool(result.get("ok")) and not detected_errors
    return result


def _unity_command(
    project: Path,
    log_file: Path,
    upm_log_file: Path,
    execute_method: str | None = None,
) -> list[str]:
    unity = _required_file(find_unity(project), "Unity")

    command = [
        str(unity),
        "-batchmode",
        "-quit",
        "-projectPath",
        str(project),
        "-logFile",
        str(log_file),
        "-upmLogFile",
        str(upm_log_file),
    ]

    if execute_method:
        command.extend(["-executeMethod", execute_method])

    return command


@mcp.tool()
def toolchain_status() -> dict:
    """Return detected Blender, Unity and default Unity project paths."""
    blender = find_blender()
    project = default_unity_project()
    unity = find_unity(project)
    required_version = read_unity_project_version(project)

    return {
        "blender": str(blender) if blender else None,
        "unity": str(unity) if unity else None,
        "required_unity_version": required_version,
        "default_unity_project": str(project) if project else None,
        "blender_available": blender is not None,
        "unity_available": unity is not None,
    }


@mcp.tool()
def blender_version() -> dict:
    """Run Blender --version."""
    blender = _required_file(find_blender(), "Blender")
    return run_process([str(blender), "--version"], timeout_seconds=60)


@mcp.tool()
def blender_run_python(
    script_path: str,
    blend_file: str | None = None,
    timeout_seconds: int = 1800,
) -> dict:
    """Run a trusted Python script inside Blender in background mode."""
    blender = _required_file(find_blender(), "Blender")
    script = Path(script_path).expanduser().resolve()

    if not script.is_file():
        raise FileNotFoundError(f"Blender Python script not found: {script}")

    command = [str(blender), "--background"]

    if blend_file:
        blend = Path(blend_file).expanduser().resolve()
        if not blend.is_file():
            raise FileNotFoundError(f"Blend file not found: {blend}")
        command.append(str(blend))

    command.extend(["--python", str(script)])
    return run_process(command, timeout_seconds=max(1, timeout_seconds))


@mcp.tool()
def unity_compile_project(
    project_path: str | None = None,
    timeout_seconds: int = 1800,
) -> dict:
    """Open/import a Unity project in batch mode and fail if compiler errors are detected."""
    project = _required_project(project_path)
    logs = project / "Logs"
    logs.mkdir(parents=True, exist_ok=True)
    log_file = logs / "unity-mcp-compile.log"
    upm_log_file = logs / "unity-mcp-upm.log"

    command = _unity_command(project, log_file, upm_log_file)
    return _unity_result(command, project, log_file, upm_log_file, timeout_seconds)


@mcp.tool()
def unity_validate_project(
    project_path: str | None = None,
    execute_method: str = "HORDAX.EditorTools.CiValidation.Run",
    timeout_seconds: int = 1800,
) -> dict:
    """Compile a Unity project and execute its validation entrypoint."""
    if not execute_method or " " in execute_method:
        raise ValueError("execute_method must be a fully-qualified static method name.")

    project = _required_project(project_path)
    logs = project / "Logs"
    logs.mkdir(parents=True, exist_ok=True)
    log_file = logs / "unity-mcp-validation.log"
    upm_log_file = logs / "unity-mcp-validation-upm.log"

    command = _unity_command(project, log_file, upm_log_file, execute_method)
    return _unity_result(command, project, log_file, upm_log_file, timeout_seconds)


@mcp.tool()
def unity_run_method(
    execute_method: str,
    project_path: str | None = None,
    extra_args: str = "",
    timeout_seconds: int = 1800,
) -> dict:
    """Run a trusted static Unity Editor method in batch mode."""
    if not execute_method or " " in execute_method:
        raise ValueError("execute_method must be a fully-qualified static method name.")

    project = _required_project(project_path)
    logs = project / "Logs"
    logs.mkdir(parents=True, exist_ok=True)
    safe_name = execute_method.replace(".", "_")
    log_file = logs / f"unity-{safe_name}.log"
    upm_log_file = logs / f"unity-{safe_name}-upm.log"

    command = _unity_command(project, log_file, upm_log_file, execute_method)

    if extra_args.strip():
        command.extend(shlex.split(extra_args, posix=False))

    return _unity_result(command, project, log_file, upm_log_file, timeout_seconds)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
