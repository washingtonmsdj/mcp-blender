# OrdaX Action Gateway — contrato read-only inicial

Status: foundation only. This module is **not** a public network server.

## Objetivo

`ProductActionGateway` is the shared execution facade intended for future
OrdaX Product MCP and OrdaX Web clients. It reuses the Device Agent's existing
typed actions instead of creating a second backend or a second permission model.

The Control Plane remains responsible for resolving identity and persisted
grants. The gateway receives an already-resolved `ProductGrant` and fails
closed when no matching action/project grant is present.

## Initial read-only surface

- `projects.list`
- `project.inventory`
- `project.text_read`
- `git.status`
- `git.diff`
- `artifact.preview`

This first surface intentionally excludes:

- `project.text_write` and `project.text_patch`;
- `git.sync`;
- Blender and Unity execution actions;
- `artifact.read_chunk` bulk transfer;
- generic shell access;
- implicit wildcard grants.

## Privacy boundary

The local Device Agent may legitimately know workstation-specific absolute
paths. Product-facing results remove those details where the existing local
action returns them:

- project roots are removed from project discovery/inventory;
- Git command arrays are removed because they contain local paths;
- artifact absolute paths are removed from previews;
- project discovery omits private adapter configuration.

The project slug, relative project paths, bounded text content, bounded diffs
and explicitly granted artifact preview bytes remain available.

## Execution contract

A Product action executes only when all of these are true:

1. the action exists in the explicit Product read-only catalog;
2. the caller-supplied grant contains that action;
3. project-scoped actions include a project slug;
4. the grant contains that project;
5. the payload contains only fields approved for that action;
6. the mapped local Device Agent action is installed.

There is no default grant.

## Next integration step

Do not expose this gateway over HTTP/MCP until the Control Plane can provide a
verified identity plus durable user/Space/Project/device grants and audit
metadata. The future network surfaces should call this same gateway rather than
re-implement its allow-list.
