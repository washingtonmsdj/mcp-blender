# Blender adoption in ORDAX Studio

ORDAX Studio treats Blender as a project capability, not as a separate product. The preferred path is the lightweight `ordax_studio_bridge` add-on installed by `blender.adoption_install`.

## Normal flow

1. Install the ORDAX adoption add-on once.
2. Open Blender normally, including by double-clicking a `.blend` file.
3. The add-on publishes a short-lived discovery heartbeat in the ORDAX state directory.
4. `blender.adopt` binds the matching window to its registered project.
5. `blender.live_start` always tries adoption before it is allowed to open another Blender process.

If an unmanaged Blender process exists and cannot be adopted, ORDAX fails closed and refuses to open a second window.

## Legacy BlendMCP migration

Older projects may still launch a project-local BlendMCP TCP server. Those projects can opt in to an in-place compatibility migration:

```json
{
  "apps": ["blender"],
  "blender": {
    "scripts_dir": "automation/blender",
    "legacy_blendmcp_port": 9877
  }
}
```

`legacy_blendmcp_port` is optional and must be between 1024 and 65535. ORDAX only connects to `127.0.0.1`, probes the legacy server with `get_addon_version`, and sends one fixed bootstrap operation that registers `ordax_studio_bridge` inside the existing Blender process.

Migration is accepted only after a fresh ORDAX companion presence appears with the expected project, PID and companion fingerprint. If multiple unmanaged Blender windows are running, the caller must select a PID explicitly.

The compatibility path does not save or modify the scene and does not permit arbitrary caller-provided Python. Projects that already use the ORDAX adoption add-on do not need the legacy port setting.
