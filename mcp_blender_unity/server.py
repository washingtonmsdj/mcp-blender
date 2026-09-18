from __future__ import annotations

import re
import shlex
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


def _unity_result(command: list[str], project: Path, log_file: Path, timeout_seconds: int) -> dict:
    result = run_process(
        command,
        cwd=project,
        timeout_seconds=max(1, timeout_seconds),
    )

    log_text = _read_tail(log_file)
    detected_errors: list[str] = []

    for pattern in _UNITY_ERROR_PATTERNS:
        if pattern.search(log_text):
            detected_errors.append(pattern.pattern)

    result["log_file"] = str(log_file)
    result["unity_log"] = log_text
    result["detected_error_patterns"] = detected_errors
    result["ok"] = bool(result.get("ok")) and not detected_errors
    return result


def _unity_command(project: Path, log_file: Path, execute_method: str | None = None) -> list[str]:
    unity = _required_file(find_unity(project), "Unity")

    command = [
        str(unity),
        "-batchmode",
        "-quit",
        "-projectPath",
        str(project),
        "-logFile",
        str(log_file),
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

    command = _unity_command(project, log_file)
    return _unity_result(command, project, log_file, timeout_seconds)


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

    command = _unity_command(project, log_file, execute_method)
    return _unity_result(command, project, log_file, timeout_seconds)


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

    command = _unity_command(project, log_file, execute_method)

    if extra_args.strip():
        command.extend(shlex.split(extra_args, posix=False))

    return _unity_result(command, project, log_file, timeout_seconds)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
