from __future__ import annotations

import os
import platform
import re
from pathlib import Path


_VERSION_RE = re.compile(r"^m_EditorVersion:\s*(\S+)\s*$", re.MULTILINE)


def _existing(path: str | None) -> Path | None:
    if not path:
        return None
    candidate = Path(path).expanduser()
    return candidate if candidate.is_file() else None


def _newest(candidates: list[Path]) -> Path | None:
    existing = [path for path in candidates if path.is_file()]
    if not existing:
        return None
    return sorted(existing, key=lambda path: str(path).lower(), reverse=True)[0]


def read_unity_project_version(project: str | Path | None) -> str | None:
    if project is None:
        return None

    root = Path(project).expanduser().resolve()
    version_file = root / "ProjectSettings" / "ProjectVersion.txt"
    if not version_file.is_file():
        return None

    text = version_file.read_text(encoding="utf-8", errors="replace")
    match = _VERSION_RE.search(text)
    return match.group(1) if match else None


def find_blender() -> Path | None:
    explicit = _existing(os.getenv("BLENDER_EXE"))
    if explicit:
        return explicit

    system = platform.system()
    if system == "Windows":
        root = Path("C:/Program Files/Blender Foundation")
        return _newest(list(root.glob("Blender */blender.exe"))) if root.exists() else None

    if system == "Darwin":
        path = Path("/Applications/Blender.app/Contents/MacOS/Blender")
        return path if path.is_file() else None

    for path in (Path("/usr/bin/blender"), Path("/usr/local/bin/blender")):
        if path.is_file():
            return path

    return None


def find_unity(project: str | Path | None = None) -> Path | None:
    explicit = _existing(os.getenv("UNITY_EXE"))
    if explicit:
        return explicit

    required_version = read_unity_project_version(project)
    system = platform.system()

    if system == "Windows":
        root = Path("C:/Program Files/Unity/Hub/Editor")
        if required_version:
            exact = root / required_version / "Editor" / "Unity.exe"
            return exact if exact.is_file() else None
        return _newest(list(root.glob("*/Editor/Unity.exe"))) if root.exists() else None

    if system == "Darwin":
        root = Path("/Applications/Unity/Hub/Editor")
        if required_version:
            exact = root / required_version / "Unity.app" / "Contents" / "MacOS" / "Unity"
            return exact if exact.is_file() else None
        return _newest(list(root.glob("*/Unity.app/Contents/MacOS/Unity"))) if root.exists() else None

    roots = [
        Path.home() / "Unity/Hub/Editor",
        Path("/opt/unityhub"),
        Path("/opt/Unity/Hub/Editor"),
    ]

    for root in roots:
        if not root.exists():
            continue

        if required_version:
            exact = root / required_version / "Editor" / "Unity"
            if exact.is_file():
                return exact
            continue

        found = _newest(list(root.glob("*/Editor/Unity")))
        if found:
            return found

    return None


def default_unity_project() -> Path | None:
    raw = os.getenv("DEFAULT_UNITY_PROJECT")
    if not raw:
        return None

    path = Path(raw).expanduser().resolve()
    return path if path.is_dir() else None
