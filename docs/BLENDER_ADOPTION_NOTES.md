# ORDAX Blender migration notes

The preferred integration is the `ordax_studio_bridge` adoption add-on. `blender.live_start` must adopt a matching running Blender before considering a new process.

Legacy projects can set `blender.legacy_blendmcp_port` to migrate an already-open project-local BlendMCP session in place. The compatibility path is loopback-only, probes the legacy server first, registers only the fixed ORDAX adoption add-on, and verifies project + PID + companion fingerprint before reporting success.

If no safe adoption path is available while Blender is already running, ORDAX refuses to open a second window.
