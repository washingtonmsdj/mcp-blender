"""Protected local state for the ORDAX Chat App."""
from __future__ import annotations

import ctypes
import json
import os
import stat
import tempfile
import uuid
from ctypes import wintypes
from pathlib import Path
from typing import Any, Callable


def resolve_chat_app_state_dir() -> Path:
    override = os.environ.get("ORDAX_CHAT_APP_STATE_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return (base / "OrdaX" / "ChatApp").resolve()
    xdg = os.environ.get("XDG_STATE_HOME")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".local" / "state"
    return (base / "ordax-chat-app").resolve()


class HostIdentityStore:
    def __init__(self, state_dir: str | Path | None = None):
        self.state_dir = Path(state_dir).expanduser().resolve() if state_dir else resolve_chat_app_state_dir()
        self.path = self.state_dir / "host.json"

    def get_or_create(self) -> str:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        if self.path.is_file():
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
                host_id = str(payload.get("ext_agent_host_id") or "")
                if host_id.startswith("urn:uuid:") and len(host_id) > len("urn:uuid:"):
                    return host_id
            except (OSError, ValueError, json.JSONDecodeError):
                pass
        host_id = f"urn:uuid:{uuid.uuid4()}"
        _atomic_write(self.path, json.dumps({"ext_agent_host_id": host_id}, indent=2).encode("utf-8"), mode=0o600)
        return host_id


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _blob(data: bytes) -> tuple[_DATA_BLOB, Any]:
    if not data:
        buffer = ctypes.create_string_buffer(1)
        return _DATA_BLOB(0, ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))), buffer
    buffer = ctypes.create_string_buffer(data, len(data))
    return _DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))), buffer


def _windows_protect(data: bytes) -> bytes:
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    source, source_buffer = _blob(data)
    result = _DATA_BLOB()
    CRYPTPROTECT_UI_FORBIDDEN = 0x1
    description = "OrdaX Chat App credentials"
    if not crypt32.CryptProtectData(
        ctypes.byref(source),
        description,
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(result),
    ):
        raise OSError(ctypes.get_last_error(), "CryptProtectData failed")
    try:
        return ctypes.string_at(result.pbData, result.cbData)
    finally:
        kernel32.LocalFree(result.pbData)
        del source_buffer


def _windows_unprotect(data: bytes) -> bytes:
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    source, source_buffer = _blob(data)
    result = _DATA_BLOB()
    description = wintypes.LPWSTR()
    CRYPTPROTECT_UI_FORBIDDEN = 0x1
    if not crypt32.CryptUnprotectData(
        ctypes.byref(source),
        ctypes.byref(description),
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(result),
    ):
        raise OSError(ctypes.get_last_error(), "CryptUnprotectData failed")
    try:
        return ctypes.string_at(result.pbData, result.cbData)
    finally:
        kernel32.LocalFree(result.pbData)
        del source_buffer


def _identity(data: bytes) -> bytes:
    return data


class ProtectedJsonStore:
    """Atomic credential storage; DPAPI on Windows and owner-only files elsewhere."""

    def __init__(
        self,
        path: str | Path | None = None,
        *,
        protect: Callable[[bytes], bytes] | None = None,
        unprotect: Callable[[bytes], bytes] | None = None,
    ):
        state_dir = resolve_chat_app_state_dir()
        self.path = Path(path).expanduser().resolve() if path else state_dir / "accounts.dat"
        if protect is None or unprotect is None:
            if os.name == "nt":
                protect = _windows_protect
                unprotect = _windows_unprotect
            else:
                protect = _identity
                unprotect = _identity
        self._protect = protect
        self._unprotect = unprotect

    def load(self) -> dict[str, Any]:
        if not self.path.is_file():
            return {"version": 1, "selected_account": None, "accounts": []}
        raw = self._unprotect(self.path.read_bytes())
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict) or payload.get("version") != 1:
            raise ValueError("unsupported ORDAX account-store format")
        if not isinstance(payload.get("accounts"), list):
            raise ValueError("invalid ORDAX account-store accounts")
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        protected = self._protect(encoded)
        _atomic_write(self.path, protected, mode=0o600)


def _atomic_write(path: Path, data: bytes, *, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.chmod(temp, mode)
        except OSError:
            pass
        os.replace(temp, path)
        try:
            current = stat.S_IMODE(path.stat().st_mode)
            if os.name != "nt" and current & 0o077:
                os.chmod(path, mode)
        except OSError:
            pass
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass
