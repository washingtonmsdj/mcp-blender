# OrdaX Action Gateway — contrato read-only inicial

Status: foundation only. This module is **not** a public network server.

## Objetivo

`ProductActionGateway` is the shared execution facade intended for future
OrdaX Product MCP and OrdaX Web clients. It reuses the Device Agent's existing
typed actions instead of creating a second backend or a second permission model.

The Control Plane remains responsible for authenticating identity and resolving
persisted grants. The gateway receives both a verified `ProductRequestContext`
and an already-resolved `ProductGrant`; it fails closed when subject, Space,
device, expiry, action or project scope does not match.

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

## Grant provenance and audit

A resolved grant carries a stable grant id, authenticated subject id, explicit
actions/projects, optional Space/device scope and optional expiry. The gateway
validates the grant structure at runtime instead of trusting Python type hints.

Execution also requires an audit sink. Before any local action runs, the gateway
must persist an authorization event. After the local read finishes, it persists
a result event before returning Product-facing data. If pre-execution audit
persistence fails, the local action does not run. If result-audit persistence
fails, the Product result is withheld.

Audit events contain identifiers, action/project, decision, phase and only the
**names** of payload fields. They do not copy text-file contents, Git diffs,
artifact bytes or other payload values into the audit record.

## Next integration step

Do not expose this gateway over HTTP/MCP until the Control Plane can provide a
verified identity plus durable user/Space/Project/device grants and audit
metadata. The future network surfaces should call this same gateway rather than
re-implement its allow-list.
