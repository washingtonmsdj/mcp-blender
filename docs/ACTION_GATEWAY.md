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

## Control Plane persistence boundary

Cloudflare v3 now has the administrative persistence foundation for this
contract: D1 stores Product grants and the audit schema, and the Worker can
create/list/revoke only the same explicit read-only action set.

The Control Plane also has a shared grant-resolution primitive that evaluates
subject, optional Space/device scope, action, project, expiry and revocation.
Its current HTTP surface is operator-only diagnostic plumbing; the resolver is
intended to be reused after real Product authentication is added.

This is deliberately **not** Product authentication or Product execution. The
operator credential administers/diagnoses grants but never becomes the
authenticated Product subject, and there is no Product action execution
endpoint.

## Product MCP facade

`ordax_dev_agent.product_mcp.ProductMcpFacade` now defines the first read-only
Product MCP tool surface without creating a public server. It maps MCP-friendly
tool names to this gateway and still requires a verified `ProductRequestContext`
plus a resolved `ProductGrant` on every call.

The facade intentionally performs no authentication, grant lookup, network I/O
or credential handling. Mutation tools are not registered. This keeps Product
MCP and OrdaX Web on the same authorization/audit path instead of duplicating
allow-lists.

## Next integration step

The Control Plane now has a separate JWT/JWKS Product identity probe at
`/v3/product/session`. It proves the Product subject only; it does not resolve a
grant or execute work.

Do not expose Product action execution over HTTP/public MCP until that authenticated
subject is bound to a live non-revoked/non-expired grant for the requested
subject/device/project and the gateway's mandatory audit events are persisted.
The future authenticated MCP host should wrap `ProductMcpFacade` rather than
re-implementing its allow-list.
