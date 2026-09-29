# ORDAX Studio — Blender window adoption

`mcp-blender` is the historical repository name. The product/runtime is **ORDAX Studio**, and Blender is one typed capability of the ORDAX Studio MCP.

## Goal

A Blender window is a user-owned working session. ORDAX must reuse the correct existing window whenever possible and must never open a second visible Blender merely because its companion is missing or stale.

## Bootstrap model

ORDAX installs a lightweight Blender add-on named `ordax_studio_bridge` into each detected Blender user profile. The add-on is only responsible for discovery and safe adoption; modeling operations continue through the typed live companion.

The bootstrap configuration lives under the local ORDAX agent state directory and contains only registered Blender projects, trusted companion paths, project roots, script roots, control roots and artifact roots.

`BlenderAdoptionManager.ensure_installed()` makes this bootstrap self-healing. It refreshes project configuration, verifies the installed add-on by SHA-256 and companion fingerprint, and only invokes Blender's preference enable/save flow when the installed bootstrap is missing or outdated.

## Manual Blender launch

When Blender is opened manually and the add-on is enabled:

1. the add-on writes a short-lived discovery record containing PID, file path, Blender version, dirty state and current ORDAX attachment;
2. if the opened `.blend` belongs unambiguously to one registered Blender project, the add-on loads the trusted ORDAX companion into that same process automatically;
3. `start_blender` sees the fresh presence and reuses the window rather than spawning another process.

No arbitrary process injection is used.

## ORDAX-managed Blender launch

A Blender process started by `BlenderLiveBridge` already receives `blender_live_companion.py` through Blender's `--python` launch contract. The persistent add-on detects the managed ORDAX command-line arguments and stays in discovery-only mode, preventing two companion timers from being registered in the same Blender process.

## Existing unmanaged window

If Blender is already running but the ORDAX add-on was not active in that process, ORDAX refuses to open a second visible window. The bootstrap is installed/synchronized for future launches and the current window must be reopened once so Blender loads the enabled add-on.

This is intentionally fail-closed. ORDAX does not use OS-level code injection to mutate an arbitrary Blender process.

## Multiple windows

If multiple fresh Blender windows point into the same project, ORDAX does not guess. `blender_instances` exposes their PIDs and `adopt_blender` requires an explicit PID.

A window already attached to another ORDAX project is never considered a candidate for a new project, even if the user opens a file from the new project in that same Blender process. Reopen Blender before changing managed projects in one process.

## Timeout behavior

Adoption requests are short-lived. If the requested window does not acknowledge the request before the timeout, ORDAX removes the pending request so it cannot be consumed later and unexpectedly attach a stale operation.

## MCP tools

- `install_blender_adoption` — explicit install/repair entrypoint; retained for diagnostics and manual recovery.
- `blender_instances` — lists discovered adoptable windows and unmanaged Blender PIDs.
- `adopt_blender` — adopts one discovered window, optionally by PID.
- `start_blender` — adoption-first entrypoint; spawns only when no physical Blender window already exists.
- `get_blender_status`, `get_scene_info`, `get_object_info`, `get_viewport_screenshot` — normal read/visual operations after adoption.

## Invariants

- never silently choose between multiple matching Blender windows;
- never spawn a second visible Blender when an unmanaged Blender process already exists;
- never adopt a window already attached to another project;
- never trust companion code outside the packaged ORDAX asset root;
- never keep an adoption request after its caller timed out;
- never register both the persistent add-on companion and the managed-launch companion in the same process;
- preserve unsaved user work and do not close/restart a dirty Blender window automatically.
