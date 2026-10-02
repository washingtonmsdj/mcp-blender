# ORDAX Dev — OpenAI MCP annotation review evidence

Generated from the canonical public tool surface on `control-plane/cloudflare/src/mcp_http.ts`.

This document is reviewer-facing evidence for the OpenAI plugin submission. The server advertises explicit boolean `readOnlyHint`, `destructiveHint`, and `openWorldHint` values for every public MCP tool. The justifications below explain why each value matches the tool's behavior.

| Tool | readOnly | destructive | openWorld | Justification |
| --- | :---: | :---: | :---: | --- |
| `ordax_session` | true | false | false | Reads or computes bounded data from the authenticated ORDAX account/device/project and does not modify external state. |
| `ordax_profile` | true | false | false | Reads or computes bounded data from the authenticated ORDAX account/device/project and does not modify external state. |
| `ordax_targets` | true | false | false | Reads or computes bounded data from the authenticated ORDAX account/device/project and does not modify external state. |
| `ordax_action_status` | true | false | false | Reads or computes bounded data from the authenticated ORDAX account/device/project and does not modify external state. |
| `repository_catalog` | true | false | false | Reads or computes bounded data from the authenticated ORDAX account/device/project and does not modify external state. |
| `handoff_get` | true | false | false | Reads or computes bounded data from the authenticated ORDAX account/device/project and does not modify external state. |
| `handoff_create` | false | false | false | Creates additive state or starts/adopts a local capability without deleting or overwriting existing user data by default. |
| `project_inventory` | true | false | false | Reads or computes bounded data from the authenticated ORDAX account/device/project and does not modify external state. |
| `project_text_read` | true | false | false | Reads or computes bounded data from the authenticated ORDAX account/device/project and does not modify external state. |
| `project_text_write` | false | true | false | Can overwrite, patch, move, remove, save, or otherwise modify existing project/Blender state, so it is treated as potentially destructive. |
| `project_text_patch` | false | true | false | Can overwrite, patch, move, remove, save, or otherwise modify existing project/Blender state, so it is treated as potentially destructive. |
| `projects_list` | true | false | false | Reads or computes bounded data from the authenticated ORDAX account/device/project and does not modify external state. |
| `project_create` | false | false | false | Creates a new project only inside the configured ORDAX workspace, without overwriting an existing path; the action requires an explicit grant. |
| `project_search` | true | false | false | Reads or computes bounded data from the authenticated ORDAX account/device/project and does not modify external state. |
| `project_read_batch` | true | false | false | Reads or computes bounded data from the authenticated ORDAX account/device/project and does not modify external state. |
| `project_health` | true | false | false | Reads or computes bounded data from the authenticated ORDAX account/device/project and does not modify external state. |
| `project_preview_status` | true | false | false | Reads or computes bounded data from the authenticated ORDAX account/device/project and does not modify external state. |
| `workspace_file_stat` | true | false | false | Reads or computes bounded data from the authenticated ORDAX account/device/project and does not modify external state. |
| `workspace_directory_list` | true | false | false | Reads or computes bounded data from the authenticated ORDAX account/device/project and does not modify external state. |
| `workspace_text_read` | true | false | false | Reads or computes bounded data from the authenticated ORDAX account/device/project and does not modify external state. |
| `workspace_text_write` | false | true | false | Can overwrite, patch, move, remove, save, or otherwise modify existing project/Blender state, so it is treated as potentially destructive. |
| `workspace_text_patch` | false | true | false | Can overwrite, patch, move, remove, save, or otherwise modify existing project/Blender state, so it is treated as potentially destructive. |
| `workspace_directory_create` | false | false | false | Creates additive state or starts/adopts a local capability without deleting or overwriting existing user data by default. |
| `workspace_path_remove` | false | true | false | Can overwrite, patch, move, remove, save, or otherwise modify existing project/Blender state, so it is treated as potentially destructive. |
| `workspace_path_move` | false | true | false | Can overwrite, patch, move, remove, save, or otherwise modify existing project/Blender state, so it is treated as potentially destructive. |
| `git_status` | true | false | false | Reads or computes bounded data from the authenticated ORDAX account/device/project and does not modify external state. |
| `git_diff` | true | false | false | Reads or computes bounded data from the authenticated ORDAX account/device/project and does not modify external state. |
| `git_command` | false | true | true | Can execute commands or Git operations that may modify project state and may contact open-ended external destinations; explicit grants and host confirmation are required. |
| `terminal_exec` | false | true | true | Can execute commands or Git operations that may modify project state and may contact open-ended external destinations; explicit grants and host confirmation are required. |
| `artifacts_list` | true | false | false | Reads or computes bounded data from the authenticated ORDAX account/device/project and does not modify external state. |
| `artifact_preview` | true | false | false | Reads or computes bounded data from the authenticated ORDAX account/device/project and does not modify external state. |
| `blender_status` | true | false | false | Reads or computes bounded data from the authenticated ORDAX account/device/project and does not modify external state. |
| `blender_scene_snapshot` | true | false | false | Reads or computes bounded data from the authenticated ORDAX account/device/project and does not modify external state. |
| `blender_object_inspect` | true | false | false | Reads or computes bounded data from the authenticated ORDAX account/device/project and does not modify external state. |
| `blender_modeling_schema` | true | false | false | Reads or computes bounded data from the authenticated ORDAX account/device/project and does not modify external state. |
| `blender_start` | false | false | false | Creates additive state or starts/adopts a local capability without deleting or overwriting existing user data by default. |
| `blender_transform` | false | true | false | Can overwrite, patch, move, remove, save, or otherwise modify existing project/Blender state, so it is treated as potentially destructive. |
| `blender_create_primitive` | false | false | false | Creates additive state or starts/adopts a local capability without deleting or overwriting existing user data by default. |
| `blender_apply_material` | false | true | false | Can overwrite, patch, move, remove, save, or otherwise modify existing project/Blender state, so it is treated as potentially destructive. |
| `blender_save` | false | true | false | Can overwrite, patch, move, remove, save, or otherwise modify existing project/Blender state, so it is treated as potentially destructive. |

## Classification policy

- **Read-only**: retrieval, bounded inspection, health/status, search, preview metadata, and artifact/file reads.
- **Non-destructive write**: additive state such as creating a handoff, directory, primitive, or starting/adopting Blender.
- **Destructive/write**: operations that can overwrite, patch, move, delete, save, transform, execute commands, or otherwise mutate existing state.
- **Open-world**: only `git_command` and `terminal_exec`, because they may contact arbitrary remote destinations through Git/network-capable commands. Private ORDAX account/device/project reads are not open-world merely because the Control Plane is remotely hosted.

The runtime still enforces account, device, project, Space, and action grants independently of these host-facing hints.
