# ORDAX Studio — Computer Control policy

Computer Control is a typed capability of ORDAX Runtime. It is not an unrestricted remote shell.

## Authority model

A remote action is executable only when every required boundary agrees:

1. the authenticated ORDAX account can reach the device;
2. an active Product grant includes the project and typed action;
3. the local Runtime policy allows the requested computer resource;
4. the action-specific validator accepts the bounded payload.

A remote grant never overrides local computer policy. Local policy never creates a remote grant.

## Local policy SSOT

The canonical local policy is the `computer_access` section of:

`%LOCALAPPDATA%\OrdaX\DevAgent\agent-settings.json`

Example:

```json
{
  "computer_access": {
    "enabled": true,
    "full_filesystem": false,
    "allowed_roots": ["C:\\Users\\USER\\Documents\\github"],
    "allowed_applications": ["notepad.exe"]
  }
}
```
`allowed_applications` defaults to an empty list. Therefore `computer.launch_app` is denied until the computer owner explicitly allows an executable.

Entries may be absolute `.exe` paths or `.exe` basenames. Basenames are resolved to a concrete executable path before use; the policy compares normalized resolved paths, not an arbitrary matching filename.

Environment overrides exist for managed deployments:

- `ORDAX_COMPUTER_ACCESS_ENABLED`
- `ORDAX_COMPUTER_FULL_FILESYSTEM`
- `ORDAX_COMPUTER_ALLOWED_ROOTS`
- `ORDAX_COMPUTER_ALLOWED_APPLICATIONS`

On Windows, path-list environment values use the platform path separator (`;`). Invalid policy fails closed.


## Owner-local Studio controls

ORDAX Studio exposes **Acesso ao computador** as a local owner surface for the same `computer_access` SSOT. The UI can enable/disable Computer Control, manage `allowed_roots`, manage `allowed_applications`, and explicitly opt into `full_filesystem`.

The editor is deliberately **not** a Product MCP action. Remote GPT clients can read the effective non-secret policy through `computer.access_status`, but they cannot widen local roots, allow applications or enable full-filesystem access. Local writes preserve unrelated agent settings, use an atomic file replacement and require an `expected_revision` so a stale Studio window cannot overwrite a newer settings file. Fields controlled by `ORDAX_COMPUTER_*` environment variables are shown as externally managed and are not overwritten by Studio.

## App launch

`computer.launch_app` does not use a shell. The Runtime resolves exactly one Windows `.exe`, validates bounded arguments and requires that resolved executable to be in `allowed_applications`.

For public review, allow only `notepad.exe`. Do not allow `powershell.exe`, `pwsh.exe`, `cmd.exe`, scripting hosts, package managers or other shell-like executables merely to make a demo pass.

## Filesystem

Filesystem actions remain bounded by `allowed_roots` unless `full_filesystem=true` is an explicit local choice. Product grants still apply independently.

## Auditability

`computer.access_status` exposes the effective non-secret local policy so Studio and authorized MCP clients can explain why an operation is allowed or denied.

Computer Control mutations continue through Product MCP, Cloudflare grant enforcement, ORDAX Runtime validation and the existing receipt/audit path.
