from __future__ import annotations

import os
from pathlib import Path


_TOKEN_FILES = {
    "development-v2": "device-token.development-v2.txt",
    "cloudflare-v3": "device-token.cloudflare-v3.txt",
}
_LEGACY_TOKEN_FILE = "device-token.txt"


def token_path(state_dir: Path, protocol: str) -> Path:
    normalized = str(protocol or "").strip().lower()
    try:
        name = _TOKEN_FILES[normalized]
    except KeyError as error:
        raise ValueError(f"unsupported credential protocol: {protocol}") from error
    return state_dir / name


def pending_token_path(state_dir: Path, protocol: str) -> Path:
    path = token_path(state_dir, protocol)
    return path.with_name(path.name + ".pending-setup")


def legacy_token_path(state_dir: Path) -> Path:
    return state_dir / _LEGACY_TOKEN_FILE


def resolve_token_path(
    state_dir: Path,
    protocol: str,
    *,
    migrate_legacy: bool = True,
) -> Path:
    """Return the provider-scoped credential path.

    development-v2 installations created before provider-scoped credentials used
    device-token.txt. Move that file atomically once so future v2/v3 credentials
    can coexist without copying a secret or weakening ACLs.
    """
    path = token_path(state_dir, protocol)
    if (
        migrate_legacy
        and str(protocol).strip().lower() == "development-v2"
        and not path.exists()
    ):
        legacy = legacy_token_path(state_dir)
        if legacy.is_file():
            try:
                os.replace(legacy, path)
            except FileNotFoundError:
                if not path.is_file():
                    raise
    return path
