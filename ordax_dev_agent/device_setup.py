"""Durable, device-bound setup. No runner, shell commands or backend secrets."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import socket
import subprocess
from pathlib import Path

import httpx

from .identity import machine_id

CONTROL_PLANE = "https://eobcxuyvhkvdmkbaihwh.supabase.co"
ENDPOINT = CONTROL_PLANE + "/functions/v1/ordax-device-setup"


class SetupError(RuntimeError):
    pass


def private_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        # Restrict inheritance before creating files, not after writing a secret.
        sid = subprocess.run(["whoami", "/user", "/fo", "csv", "/nh"],
                             capture_output=True, text=True, check=True).stdout
        import csv
        principal = next(csv.reader([sid.strip()]))[1]
        # Replace the DACL, including old explicit grants. Pass the path through
        # the environment so spaces/metacharacters never become shell syntax.
        script = """
$ErrorActionPreference='Stop'
$current=Get-Acl -LiteralPath $env:ORDAX_SETUP_PRIVATE_PATH
$allowed=@($env:ORDAX_SETUP_SID,'S-1-5-18')
$rules=@($current.GetAccessRules($true,$true,[System.Security.Principal.SecurityIdentifier]))
if ($current.AreAccessRulesProtected -and $rules.Count -eq 2 -and
    @($rules | Where-Object { $_.IdentityReference.Value -notin $allowed -or $_.AccessControlType -ne 'Allow' -or $_.FileSystemRights -ne 'FullControl' }).Count -eq 0) { exit 0 }
$acl=New-Object System.Security.AccessControl.DirectorySecurity
$acl.SetAccessRuleProtection($true,$false)
foreach($id in @($env:ORDAX_SETUP_SID,'S-1-5-18')) {
  $sid=New-Object System.Security.Principal.SecurityIdentifier($id)
  $rule=New-Object System.Security.AccessControl.FileSystemAccessRule($sid,'FullControl','ContainerInherit,ObjectInherit','None','Allow')
  $acl.AddAccessRule($rule)
}
Set-Acl -LiteralPath $env:ORDAX_SETUP_PRIVATE_PATH -AclObject $acl
"""
        env = {k: v for k, v in os.environ.items() if k.lower() != "psmodulepath"}
        result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                                env={**env, "ORDAX_SETUP_SID": principal, "ORDAX_SETUP_PRIVATE_PATH": str(path)},
                                capture_output=True, timeout=120)
        if result.returncode:
            raise SetupError("PRIVATE_ACL_FAILED")
    else:
        path.chmod(0o700)


def atomic_json(path: Path, value: dict) -> None:
    atomic_write(path, json.dumps(value, indent=2))


def atomic_write(path: Path, value: str) -> None:
    temp = path.with_name(path.name + "." + secrets.token_hex(8) + ".tmp")
    try:
        with open(temp, "x", encoding="utf-8") as f:
            if os.name != "nt":
                os.chmod(temp, 0o600)
            f.write(value)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def load_settings(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(value, dict) or not isinstance(value.get("projects", {}), dict):
            raise ValueError()
        return value
    except (ValueError, OSError):
        raise SetupError("SETTINGS_INVALID_PRESERVED") from None


def github_token(interactive: bool) -> str:
    try:
        result = subprocess.run(["gh", "auth", "token", "--hostname", "github.com"],
                                capture_output=True, text=True, timeout=15)
        if result.returncode and interactive:
            subprocess.run(["gh", "auth", "login", "--hostname", "github.com", "--web", "--git-protocol", "https"], check=True)
            result = subprocess.run(["gh", "auth", "token", "--hostname", "github.com"],
                                    capture_output=True, text=True, timeout=15)
        if result.returncode or not result.stdout.strip():
            raise SetupError("USER_LOGIN_REQUIRED")
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        raise SetupError("USER_LOGIN_REQUIRED") from None


def request(client, body: dict, headers: dict) -> dict:
    try:
        response = client.post(ENDPOINT, json=body, headers=headers)
        if response.status_code in (401, 403):
            return {"ok": False, "denied": response.status_code}
        if response.status_code >= 400:
            raise SetupError("CONTROL_PLANE_UNAVAILABLE")
        value = response.json()
        if not isinstance(value, dict) or value.get("ok") is not True:
            raise SetupError("CONTROL_PLANE_RESPONSE_INVALID")
        return value
    except (httpx.HTTPError, ValueError):
        raise SetupError("CONTROL_PLANE_UNAVAILABLE") from None


def configure(state: Path, *, interactive: bool = False, client=None, binding=None, home=None) -> dict:
    private_directory(state)
    settings_path = state / "agent-settings.json"
    settings = load_settings(settings_path)
    binding = binding or machine_id()
    token_path, pending = state / "device-token.txt", state / "device-token.txt.pending-setup"
    own_client = client is None
    client = client or httpx.Client(timeout=20, follow_redirects=False)
    try:
        identity = None
        # Recover a committed-but-unacknowledged enrollment before attempting a rotation.
        for path in (token_path, pending):
            if not path.is_file():
                continue
            token = path.read_text(encoding="utf-8-sig").strip()
            if not 32 <= len(token) <= 512:
                continue
            identity = request(client, {"operation": "identify", "machine_binding_sha256": binding},
                               {"X-Ordax-Device-Token": token})
            if identity.get("ok"):
                if path == pending:
                    os.replace(pending, token_path)
                break
            if identity.get("denied") == 403:
                raise SetupError("MACHINE_BINDING_MISMATCH")
        if not identity or not identity.get("ok"):
            credential = github_token(interactive)
            if pending.is_file():
                token = pending.read_text(encoding="utf-8").strip()
                if len(token) != 64 or any(c not in "0123456789abcdef" for c in token):
                    raise SetupError("PENDING_TOKEN_INVALID_PRESERVED")
            else:
                token = secrets.token_hex(32)
                atomic_write(pending, token)
            identity = request(client, {
                "operation": "enroll", "machine_binding_sha256": binding,
                "device_name": socket.gethostname(),
                "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
            }, {"Authorization": "Bearer " + credential})
            if not identity.get("ok"):
                raise SetupError("USER_AUTHORIZATION_REQUIRED")
            os.replace(pending, token_path)
        import uuid
        device_id = str(uuid.UUID(identity["device_id"]))
        if identity.get("protocol") != "development-v2":
            raise SetupError("PROTOCOL_MISMATCH")
        settings.update(supabase_url=CONTROL_PLANE, control_plane_protocol="development-v2",
                        development_device_id=device_id)
        projects = settings.setdefault("projects", {})
        root = (home or Path.home()) / "Documents" / "github"
        for slug in ("cerco-no-interior-mvp", "dioramas-biblicos"):
            if (root / slug).is_dir() and slug not in projects:
                projects[slug] = {"path": str(root / slug), "apps": ["blender"],
                                  "blender": {"scripts_dir": "automation/blender"}}
        if settings.get("default_project") not in projects and projects:
            settings["default_project"] = next(iter(projects))
        atomic_json(settings_path, settings)
        return {"ok": True, "device_id": device_id, "protocol": "development-v2"}
    finally:
        if own_client:
            client.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interactive", action="store_true")
    args = parser.parse_args()
    try:
        state = Path(os.environ["LOCALAPPDATA"]) / "OrdaX" / "DevAgent"
        result = configure(state, interactive=args.interactive)
        print(json.dumps(result))
        return 0
    except SetupError as error:
        print(str(error))
        return 2
    except Exception:
        print("SETUP_FAILED")
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
