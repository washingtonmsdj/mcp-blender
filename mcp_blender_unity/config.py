from __future__ import annotations

import os
import platform
import re
from pathlib import Path


_VERSION_RE = re.compile(r"^m_EditorVersion:\s*(\S+)\s*$", re.MULTILINE)
_API_COMPATIBILITY_RE = re.compile(r"^\s*apiCompatibilityLevel:\s*(\d+)\s*$", re.MULTILINE)


def _unity_editor_roots() -> list[Path]:
    """Return supported Unity Hub editor roots in deterministic order."""
    roots: list[Path] = []

    configured = os.getenv("UNITY_EDITOR_ROOTS", "")
    if configured:
        roots.extend(Path(item).expanduser() for item in configured.split(os.pathsep) if item)

    if platform.system() == "Windows":
        roots.append(Path("C:/Program Files/Unity/Hub/Editor"))
        local_app_data = os.getenv("LOCALAPPDATA")
        user_profile = os.getenv("USERPROFILE")
        if local_app_data:
            roots.append(Path(local_app_data) / "Unity/Hub/Editor")
        if user_profile:
            roots.append(Path(user_profile) / "Unity/Hub/Editor")
    elif platform.system() == "Darwin":
        roots.append(Path("/Applications/Unity/Hub/Editor"))
    else:
        roots.extend(
            [
                Path.home() / "Unity/Hub/Editor",
                Path("/opt/unityhub"),
                Path("/opt/Unity/Hub/Editor"),
            ]
        )

    unique: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        if not str(root):
            continue
        key = str(root).lower()
        if key not in seen:
            seen.add(key)
            unique.append(root)
    return unique


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


def read_unity_api_compatibility_level(project: str | Path | None) -> int | None:
    """Read Unity's serialized API compatibility level from ProjectSettings."""
    if project is None:
        return None

    root = Path(project).expanduser().resolve()
    settings_file = root / "ProjectSettings" / "ProjectSettings.asset"
    if not settings_file.is_file():
        return None

    text = settings_file.read_text(encoding="utf-8", errors="replace")
    match = _API_COMPATIBILITY_RE.search(text)
    return int(match.group(1)) if match else None


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
        roots = _unity_editor_roots()
        if required_version:
            for root in roots:
                exact = root / required_version / "Editor" / "Unity.exe"
                if exact.is_file():
                    return exact
            return None

        candidates: list[Path] = []
        for root in roots:
            if root.exists():
                candidates.extend(root.glob("*/Editor/Unity.exe"))
        return _newest(candidates)

    if system == "Darwin":
        root = Path("/Applications/Unity/Hub/Editor")
        if required_version:
            exact = root / required_version / "Unity.app" / "Contents" / "MacOS" / "Unity"
            return exact if exact.is_file() else None
        return _newest(list(root.glob("*/Unity.app/Contents/MacOS/Unity"))) if root.exists() else None

    roots = _unity_editor_roots()

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


def unity_installation_diagnostics(
    unity: str | Path | None,
    project: str | Path | None = None,
) -> dict:
    """Describe editor files needed by the selected project's compilation profile."""
    if unity is None:
        return {
            "editor_available": False,
            "reference_assemblies_required": None,
            "reference_assemblies_available": None,
            "package_manager_available": None,
            "missing_components": ["Unity.exe"],
            "installation_healthy": False,
        }

    editor = Path(unity).expanduser().resolve()
    editor_dir = editor.parent
    data_dir = editor_dir / "Data"
    api_level = read_unity_api_compatibility_level(project)
    references = data_dir / "UnityReferenceAssemblies" / "unity-4.8-api" / "Facades"
    package_manager = data_dir / "Resources" / "PackageManager" / "Server" / "UnityPackageManager.exe"

    missing: list[str] = []
    if not editor.is_file():
        missing.append(str(editor))
    if not data_dir.is_dir():
        missing.append(str(data_dir))

    references_required = api_level == 6 if api_level is not None else None
    references_available = references.is_dir() if references_required is not False else None
    if references_required and not references_available:
        missing.append(str(references))

    package_manager_available = package_manager.is_file()
    if not package_manager_available:
        missing.append(str(package_manager))

    return {
        "editor_available": editor.is_file(),
        "editor_path": str(editor),
        "editor_data_path": str(data_dir),
        "api_compatibility_level": api_level,
        "reference_assemblies_required": references_required,
        "reference_assemblies_path": str(references),
        "reference_assemblies_available": references_available,
        "package_manager_path": str(package_manager),
        "package_manager_available": package_manager_available,
        "missing_components": missing,
        "installation_healthy": not missing,
    }


def default_unity_project() -> Path | None:
    raw = os.getenv("DEFAULT_UNITY_PROJECT")
    if not raw:
        return None

    path = Path(raw).expanduser().resolve()
    return path if path.is_dir() else None
