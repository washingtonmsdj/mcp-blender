export type JsonObject = Record<string, unknown>;

type Handler = (request: Request) => Promise<Response>;
type StatusHandler = (request: Request, requestId: string) => Promise<Response>;

export interface OrdaxMcpHandlers {
  session: Handler;
  targets: Handler;
  createAction: Handler;
  getAction: StatusHandler;
}

interface ToolSpec {
  name: string;
  description: string;
  action?: string;
  projectRequired?: boolean;
  properties?: Record<string, JsonObject>;
  required?: string[];
}

const STRING = { type: "string" };
const NUMBER = { type: "number" };
const BOOLEAN = { type: "boolean" };
const DEVICE = { type: "string", description: "ORDAX device UUID returned by ordax_targets." };
const PROJECT = { type: "string", description: "Registered ORDAX project slug." };
const SPACE = { type: "string", description: "Optional Product Space id used by the grant." };
const WAIT = { type: "integer", minimum: 0, maximum: 20000, default: 8000, description: "How long the gateway waits for completion before returning a request_id." };
const STRING_ARRAY = { type: "array", items: STRING, minItems: 1, maxItems: 256 };
const ENV_OBJECT = { type: "object", maxProperties: 64, additionalProperties: { anyOf: [{ type: "string" }, { type: "number" }, { type: "boolean" }] } };
const REPLACEMENTS = {
  type: "array",
  minItems: 1,
  maxItems: 100,
  items: {
    type: "object",
    properties: {
      old: STRING,
      new: STRING,
      expected_count: { type: "integer", minimum: 1, maximum: 10000 },
    },
    required: ["old", "new"],
    additionalProperties: false,
  },
};

const TOOLS: ToolSpec[] = [
  { name: "ordax_session", description: "Inspect the authenticated ORDAX Product session." },
  { name: "ordax_targets", description: "List ORDAX devices, Spaces and grants visible to the authenticated user." },
  { name: "ordax_action_status", description: "Read the status/result of a previously queued ORDAX action.", properties: { request_id: STRING }, required: ["request_id"] },
  { name: "repository_catalog", description: "List repositories registered on an ORDAX device.", action: "workspace.repository_catalog", properties: { device_id: DEVICE, space_id: SPACE, wait_for_completion_ms: WAIT }, required: ["device_id"] },
  { name: "handoff_get", description: "Load an expiring ORDAX continuation handoff for a fresh ChatGPT conversation.", action: "handoff.get", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, handoff_id: STRING, wait_for_completion_ms: WAIT }, required: ["device_id", "project", "handoff_id"] },
  { name: "handoff_create", description: "Create an expiring continuation handoff so work can resume in a fresh ChatGPT conversation.", action: "handoff.create", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, summary: STRING, next_action: STRING, completed: { type: "array", items: STRING, maxItems: 100 }, blockers: { type: "array", items: STRING, maxItems: 100 }, changed_paths: { type: "array", items: STRING, maxItems: 100 }, ttl_hours: { type: "integer", minimum: 1, maximum: 168 }, wait_for_completion_ms: WAIT }, required: ["device_id", "project", "summary"] },
  { name: "project_inventory", description: "Inspect a bounded inventory of one registered project.", action: "project.inventory", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, max_depth: { type: "integer", minimum: 1, maximum: 12 }, max_entries: { type: "integer", minimum: 1, maximum: 10000 }, wait_for_completion_ms: WAIT }, required: ["device_id", "project"] },
  { name: "project_text_read", description: "Read a granted text file inside a registered project.", action: "project.text_read", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, path: STRING, wait_for_completion_ms: WAIT }, required: ["device_id", "project", "path"] },
  { name: "project_text_write", description: "Write a granted project text file with SHA-256 concurrency protection.", action: "project.text_write", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, path: STRING, content: STRING, expected_sha256: STRING, create: BOOLEAN, wait_for_completion_ms: WAIT }, required: ["device_id", "project", "path", "content"] },
  { name: "project_text_patch", description: "Patch a granted project text file using exact replacements and a SHA-256 precondition.", action: "project.text_patch", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, path: STRING, expected_sha256: STRING, replacements: { type: "array", items: { type: "object" }, maxItems: 100 }, wait_for_completion_ms: WAIT }, required: ["device_id", "project", "path", "expected_sha256", "replacements"] },
  { name: "projects_list", description: "List projects visible on an authorized ORDAX device.", action: "projects.list", properties: { device_id: DEVICE, space_id: SPACE, wait_for_completion_ms: WAIT }, required: ["device_id"] },
  { name: "project_search", description: "Search text across a granted project.", action: "project.search_text", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, query: STRING, max_results: { type: "integer", minimum: 1, maximum: 100 }, max_files: { type: "integer", minimum: 50, maximum: 5000 }, case_sensitive: BOOLEAN, wait_for_completion_ms: WAIT }, required: ["device_id", "project", "query"] },
  { name: "project_read_batch", description: "Read several granted project text files in one bounded call.", action: "project.text_read_batch", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, paths: { type: "array", items: STRING, minItems: 1, maxItems: 16 }, max_total_bytes: { type: "integer", minimum: 65536, maximum: 786432 }, wait_for_completion_ms: WAIT }, required: ["device_id", "project", "paths"] },
  { name: "project_health", description: "Inspect sanitized project, Git, memory and adapter health.", action: "agent.project_health", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, wait_for_completion_ms: WAIT }, required: ["device_id", "project"] },
  { name: "project_preview_status", description: "Inspect the project's supervised preview/runtime state.", action: "project.preview_status", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, wait_for_completion_ms: WAIT }, required: ["device_id", "project"] },
  { name: "workspace_file_stat", description: "Inspect any path inside a granted project.", action: "workspace.file_stat", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, path: STRING, wait_for_completion_ms: WAIT }, required: ["device_id", "project"] },
  { name: "workspace_directory_list", description: "List directories anywhere inside a granted project.", action: "workspace.directory_list", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, path: STRING, max_depth: { type: "integer", minimum: 1, maximum: 12 }, max_entries: { type: "integer", minimum: 1, maximum: 5000 }, include_hidden: BOOLEAN, wait_for_completion_ms: WAIT }, required: ["device_id", "project"] },
  { name: "workspace_text_read", description: "Read UTF-8 text anywhere inside a granted project with optional line ranges.", action: "workspace.text_read", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, path: STRING, start_line: { type: "integer", minimum: 1 }, end_line: { type: "integer", minimum: 1 }, wait_for_completion_ms: WAIT }, required: ["device_id", "project", "path"] },
  { name: "workspace_text_write", description: "Create or replace project text with SHA-256 concurrency protection.", action: "workspace.text_write", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, path: STRING, content: STRING, expected_sha256: STRING, create: BOOLEAN, wait_for_completion_ms: WAIT }, required: ["device_id", "project", "path", "content"] },
  { name: "workspace_text_patch", description: "Patch arbitrary project text using exact replacements and SHA-256 guards.", action: "workspace.text_patch", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, path: STRING, expected_sha256: STRING, replacements: REPLACEMENTS, wait_for_completion_ms: WAIT }, required: ["device_id", "project", "path", "expected_sha256", "replacements"] },
  { name: "workspace_directory_create", description: "Create a directory inside a granted project.", action: "workspace.directory_create", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, path: STRING, parents: BOOLEAN, wait_for_completion_ms: WAIT }, required: ["device_id", "project", "path"] },
  { name: "workspace_path_remove", description: "Remove a project path. Recursive directory removal requires recursive=true.", action: "workspace.path_remove", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, path: STRING, expected_sha256: STRING, recursive: BOOLEAN, wait_for_completion_ms: WAIT }, required: ["device_id", "project", "path"] },
  { name: "workspace_path_move", description: "Move or rename a path inside a granted project.", action: "workspace.path_move", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, source: STRING, destination: STRING, expected_sha256: STRING, overwrite: BOOLEAN, wait_for_completion_ms: WAIT }, required: ["device_id", "project", "source", "destination"] },
  { name: "git_status", description: "Read bounded Git status for a granted project.", action: "git.status", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, wait_for_completion_ms: WAIT }, required: ["device_id", "project"] },
  { name: "git_diff", description: "Read a bounded Git diff for a granted project.", action: "git.diff", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, paths: { type: "array", items: STRING, maxItems: 50 }, wait_for_completion_ms: WAIT }, required: ["device_id", "project"] },
  { name: "git_command", description: "Run an approved Git subcommand against a granted project. Repository hooks may execute, but credential/config inspection is blocked and authenticated remote URLs are redacted.", action: "git.command", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, args: { type: "array", items: STRING, minItems: 1, maxItems: 128 }, timeout_seconds: { type: "integer", minimum: 1, maximum: 1800 }, wait_for_completion_ms: WAIT }, required: ["device_id", "project", "args"] },
  { name: "terminal_exec", description: "Execute a foreground command with the local OS user's permissions. Requires an explicit terminal.exec grant.", action: "terminal.exec", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, cwd: STRING, argv: STRING_ARRAY, command: STRING, shell: BOOLEAN, timeout_seconds: { type: "integer", minimum: 1, maximum: 1800 }, env: ENV_OBJECT, wait_for_completion_ms: WAIT }, required: ["device_id", "project"] },
  { name: "artifacts_list", description: "List bounded artifact metadata for a granted project.", action: "artifacts.list", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, max_items: { type: "integer", minimum: 1, maximum: 100 }, wait_for_completion_ms: WAIT }, required: ["device_id", "project"] },
  { name: "artifact_preview", description: "Read a bounded preview of a granted project artifact.", action: "artifact.preview", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, artifact_name: STRING, project_artifact_path: STRING, thumbnail: BOOLEAN, max_bytes: { type: "integer", minimum: 1, maximum: 262144 }, max_width: { type: "integer", minimum: 1, maximum: 4096 }, max_height: { type: "integer", minimum: 1, maximum: 4096 }, quality: { type: "integer", minimum: 1, maximum: 100 }, wait_for_completion_ms: WAIT }, required: ["device_id", "project"] },
  { name: "blender_status", description: "Read sanitized live Blender status for a project.", action: "blender.live_status", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, wait_for_completion_ms: WAIT }, required: ["device_id", "project"] },
  { name: "blender_scene_snapshot", description: "Inspect a bounded snapshot of the live Blender scene.", action: "blender.live_scene_snapshot", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, max_objects: { type: "integer", minimum: 1, maximum: 10000 }, object_names: { type: "array", items: STRING, maxItems: 256 }, timeout_seconds: NUMBER, wait_for_completion_ms: WAIT }, required: ["device_id", "project"] },
  { name: "blender_object_inspect", description: "Inspect one live Blender object by name or ORDAX object id.", action: "blender.live_object_inspect", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, object_name: STRING, ordax_object_id: STRING, timeout_seconds: NUMBER, wait_for_completion_ms: WAIT }, required: ["device_id", "project"] },
  { name: "blender_modeling_schema", description: "Read the validated live Blender modeling contracts and guards.", action: "blender.live_modeling_schema", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, wait_for_completion_ms: WAIT }, required: ["device_id", "project"] },
  { name: "blender_start", description: "Adopt or start the project's visible Blender session without opening duplicate windows.", action: "blender.live_start", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, wait_seconds: NUMBER, timeout_seconds: NUMBER, pid: { type: "integer", minimum: 1 }, adopt_blank: BOOLEAN, wait_for_completion_ms: WAIT }, required: ["device_id", "project"] },
  { name: "blender_transform", description: "Apply a validated transform to one live Blender object.", action: "blender.live_object_transform", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, object_name: STRING, ordax_object_id: STRING, location: { type: "array", items: NUMBER, minItems: 3, maxItems: 3 }, rotation_euler: { type: "array", items: NUMBER, minItems: 3, maxItems: 3 }, scale: { type: "array", items: NUMBER, minItems: 3, maxItems: 3 }, dimensions: { type: "array", items: NUMBER, minItems: 3, maxItems: 3 }, timeout_seconds: NUMBER, wait_for_completion_ms: WAIT }, required: ["device_id", "project"] },
  { name: "blender_create_primitive", description: "Create a bounded validated primitive in the live Blender scene.", action: "blender.live_create_primitive", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, name: STRING, primitive: STRING, location: { type: "array", items: NUMBER, minItems: 3, maxItems: 3 }, size: NUMBER, radius: NUMBER, depth: NUMBER, segments: { type: "integer" }, timeout_seconds: NUMBER, wait_for_completion_ms: WAIT }, required: ["device_id", "project", "name", "primitive"] },
  { name: "blender_apply_material", description: "Apply a validated material to one live Blender object.", action: "blender.live_material_apply", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, object_name: STRING, ordax_object_id: STRING, material_name: STRING, base_color: { type: "array", items: NUMBER, minItems: 3, maxItems: 4 }, roughness: NUMBER, metallic: NUMBER, transmission: NUMBER, alpha: NUMBER, ior: NUMBER, surface_render_method: STRING, transparency_overlap: BOOLEAN, timeout_seconds: NUMBER, wait_for_completion_ms: WAIT }, required: ["device_id", "project", "material_name"] },
  { name: "blender_save", description: "Save the granted live Blender project.", action: "blender.live_save", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, target_path: STRING, timeout_seconds: NUMBER, wait_for_completion_ms: WAIT }, required: ["device_id", "project"] },
];

const READ_ONLY_TOOLS = new Set([
  "ordax_session",
  "ordax_targets",
  "ordax_action_status",
  "repository_catalog",
  "handoff_get",
  "project_inventory",
  "project_text_read",
  "projects_list",
  "project_search",
  "project_read_batch",
  "project_health",
  "project_preview_status",
  "workspace_file_stat",
  "workspace_directory_list",
  "workspace_text_read",
  "git_status",
  "git_diff",
  "artifacts_list",
  "artifact_preview",
  "blender_status",
  "blender_scene_snapshot",
  "blender_object_inspect",
  "blender_modeling_schema",
]);

const DESTRUCTIVE_TOOLS = new Set([
  "project_text_write",
  "project_text_patch",
  "workspace_text_write",
  "workspace_text_patch",
  "workspace_path_remove",
  "workspace_path_move",
  "git_command",
  "terminal_exec",
  "blender_transform",
  "blender_apply_material",
  "blender_save",
]);

const OPEN_WORLD_TOOLS = new Set([
  "git_command",
  "terminal_exec",
]);

const TOOL_TITLES: Record<string, string> = {
  ordax_session: "Check ORDAX account session",
  ordax_targets: "List connected ORDAX devices",
  ordax_action_status: "Check ORDAX action status",
  repository_catalog: "List device repositories",
  handoff_get: "Load continuation handoff",
  handoff_create: "Create continuation handoff",
  project_inventory: "Inspect project inventory",
  project_text_read: "Read project text file",
  project_text_write: "Write project text file",
  project_text_patch: "Patch project text file",
  projects_list: "List device projects",
  project_search: "Search project text",
  project_read_batch: "Read project files",
  project_health: "Inspect project health",
  project_preview_status: "Inspect project preview",
  workspace_file_stat: "Inspect project path",
  workspace_directory_list: "List project directory",
  workspace_text_read: "Read workspace text",
  workspace_text_write: "Write workspace text",
  workspace_text_patch: "Patch workspace text",
  workspace_directory_create: "Create workspace directory",
  workspace_path_remove: "Remove workspace path",
  workspace_path_move: "Move workspace path",
  git_status: "Read Git status",
  git_diff: "Read Git diff",
  git_command: "Run Git command",
  terminal_exec: "Run project command",
  artifacts_list: "List project artifacts",
  artifact_preview: "Preview project artifact",
  blender_status: "Inspect Blender status",
  blender_scene_snapshot: "Inspect Blender scene",
  blender_object_inspect: "Inspect Blender object",
  blender_modeling_schema: "Read Blender modeling capabilities",
  blender_start: "Start or adopt Blender",
  blender_transform: "Transform Blender object",
  blender_create_primitive: "Create Blender primitive",
  blender_apply_material: "Apply Blender material",
  blender_save: "Save Blender project",
};

function toolAnnotations(name: string): JsonObject {
  const readOnly = READ_ONLY_TOOLS.has(name);
  return {
    readOnlyHint: readOnly,
    destructiveHint: DESTRUCTIVE_TOOLS.has(name),
    openWorldHint: OPEN_WORLD_TOOLS.has(name),
    idempotentHint: readOnly,
  };
}

function toolInvocationText(name: string): { invoking: string; invoked: string } {
  const title = TOOL_TITLES[name] ?? name.replace(/_/g, " ");
  return {
    invoking: `${title}…`.slice(0, 64),
    invoked: `${title} complete`.slice(0, 64),
  };
}

function responseJson(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), { status, headers: { "content-type": "application/json; charset=utf-8" } });
}

function rpcResult(id: unknown, result: unknown): Response {
  return responseJson({ jsonrpc: "2.0", id, result });
}

function rpcError(id: unknown, code: number, message: string, data?: unknown): Response {
  return responseJson({ jsonrpc: "2.0", id: id ?? null, error: { code, message, ...(data === undefined ? {} : { data }) } });
}

async function bodyJson(response: Response): Promise<JsonObject> {
  try {
    const value = await response.json();
    return value && typeof value === "object" && !Array.isArray(value) ? value as JsonObject : {};
  } catch {
    return {};
  }
}

function sanitizeTargets(payload: JsonObject): JsonObject {
  const rawTargets = Array.isArray(payload.targets) ? payload.targets : [];
  const targets = rawTargets.flatMap((raw) => {
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) return [];
    const target = raw as JsonObject;
    const rawGrants = Array.isArray(target.grants) ? target.grants : [];
    const grants = rawGrants.flatMap((rawGrant) => {
      if (!rawGrant || typeof rawGrant !== "object" || Array.isArray(rawGrant)) return [];
      const grant = rawGrant as JsonObject;
      return [{
        space_id: typeof grant.space_id === "string" ? grant.space_id : null,
        actions: Array.isArray(grant.actions) ? grant.actions.filter((item) => typeof item === "string") : [],
        projects: Array.isArray(grant.projects) ? grant.projects.filter((item) => typeof item === "string") : [],
      }];
    });
    return [{
      device_id: typeof target.device_id === "string" ? target.device_id : "",
      name: typeof target.name === "string" ? target.name : "ORDAX device",
      grants,
    }];
  });
  return { ok: payload.ok !== false, targets };
}

function sanitizeActionPayload(payload: JsonObject, requestId?: string): JsonObject {
  if (payload.pending === true) {
    return {
      ok: payload.ok !== false,
      pending: true,
      request_id: requestId ?? (typeof payload.request_id === "string" ? payload.request_id : ""),
      message: typeof payload.message === "string" ? payload.message : "Action is still running.",
    };
  }
  const rawAction = payload.action;
  if (rawAction && typeof rawAction === "object" && !Array.isArray(rawAction)) {
    const action = rawAction as JsonObject;
    return {
      ok: payload.ok !== false,
      pending: false,
      action: {
        name: typeof action.action === "string" ? action.action : "",
        project: typeof action.project === "string" ? action.project : null,
        status: typeof action.status === "string" ? action.status : "",
        result: action.result ?? null,
        error_code: typeof action.error_code === "string" ? action.error_code : null,
      },
    };
  }
  if (payload.ok === false) {
    return {
      ok: false,
      pending: false,
      error: typeof payload.error === "string" ? payload.error : "ordax_action_failed",
    };
  }
  return { ok: payload.ok !== false, pending: false };
}

function textToolResult(payload: unknown, isError = false): JsonObject {
  const text = JSON.stringify(payload, null, 2);
  const structured = payload && typeof payload === "object" && !Array.isArray(payload) ? payload : { value: payload };
  return { content: [{ type: "text", text }], structuredContent: structured, isError };
}

function cloneWithAuth(source: Request, url: string, method: string, body?: unknown): Request {
  const headers = new Headers();
  const auth = source.headers.get("authorization");
  if (auth) headers.set("authorization", auth);
  if (body !== undefined) headers.set("content-type", "application/json");
  return new Request(url, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
}

function toolDefinitions(): JsonObject[] {
  return TOOLS.map((tool) => {
    const invocation = toolInvocationText(tool.name);
    return {
      name: tool.name,
      title: TOOL_TITLES[tool.name] ?? tool.name.replace(/_/g, " "),
      description: tool.description,
      securitySchemes: [{ type: "oauth2", scopes: ["email"] }],
      annotations: toolAnnotations(tool.name),
      _meta: {
        securitySchemes: [{ type: "oauth2", scopes: ["email"] }],
        "openai/toolInvocation/invoking": invocation.invoking,
        "openai/toolInvocation/invoked": invocation.invoked,
      },
      inputSchema: {
        type: "object",
        properties: tool.properties ?? {},
        required: tool.required ?? [],
        additionalProperties: false,
      },
      outputSchema: {
        type: "object",
        additionalProperties: true,
      },
    };
  });
}

function specFor(name: string): ToolSpec | undefined {
  return TOOLS.find((tool) => tool.name === name);
}

async function waitForAction(source: Request, requestId: string, timeoutMs: number, handlers: OrdaxMcpHandlers): Promise<JsonObject> {
  const deadline = Date.now() + timeoutMs;
  while (true) {
    const statusRequest = cloneWithAuth(source, new URL(`/v3/product/actions/${requestId}`, source.url).toString(), "GET");
    const statusResponse = await handlers.getAction(statusRequest, requestId);
    const payload = await bodyJson(statusResponse);
    if (!statusResponse.ok) return { ok: false, pending: false, request_id: requestId, upstream_status: statusResponse.status, response: payload };
    const action = payload.action;
    if (action && typeof action === "object" && !Array.isArray(action)) {
      const state = String((action as JsonObject).status ?? "");
      if (["succeeded", "failed", "cancelled"].includes(state)) return sanitizeActionPayload({ ...payload, pending: false }, requestId);
    }
    if (Date.now() >= deadline) return sanitizeActionPayload({ ok: true, pending: true, request_id: requestId, message: "Action is still running; call ordax_action_status with this request_id." }, requestId);
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
}

async function callTool(source: Request, name: string, args: JsonObject, handlers: OrdaxMcpHandlers): Promise<JsonObject> {
  if (name === "ordax_session") {
    const response = await handlers.session(cloneWithAuth(source, new URL("/v3/product/session", source.url).toString(), "GET"));
    return textToolResult(
      response.ok
        ? { ok: true, authenticated: true }
        : { ok: false, authenticated: false, error: "authentication_required" },
      !response.ok,
    );
  }
  if (name === "ordax_targets") {
    const response = await handlers.targets(cloneWithAuth(source, new URL("/v3/product/targets", source.url).toString(), "GET"));
    const payload = await bodyJson(response);
    return textToolResult(response.ok ? sanitizeTargets(payload) : { ok: false, error: "targets_unavailable" }, !response.ok);
  }
  if (name === "ordax_action_status") {
    const requestId = typeof args.request_id === "string" ? args.request_id : "";
    if (!requestId) return textToolResult({ ok: false, error: "request_id_required" }, true);
    const response = await handlers.getAction(cloneWithAuth(source, new URL(`/v3/product/actions/${requestId}`, source.url).toString(), "GET"), requestId);
    const payload = await bodyJson(response);
    return textToolResult(response.ok ? sanitizeActionPayload(payload, requestId) : { ok: false, error: "action_status_unavailable" }, !response.ok);
  }

  const spec = specFor(name);
  if (!spec?.action) return textToolResult({ ok: false, error: "tool_not_found", tool: name }, true);
  const deviceId = typeof args.device_id === "string" ? args.device_id : "";
  const project = spec.projectRequired && typeof args.project === "string" ? args.project : null;
  const spaceId = typeof args.space_id === "string" ? args.space_id : null;
  const rawWait = typeof args.wait_for_completion_ms === "number" ? args.wait_for_completion_ms : 8000;
  const waitMs = Math.max(0, Math.min(20000, Math.floor(rawWait)));
  const actionArgs: JsonObject = {};
  for (const [key, value] of Object.entries(args)) {
    if (!["device_id", "project", "space_id", "wait_for_completion_ms"].includes(key)) actionArgs[key] = value;
  }
  const createRequest = cloneWithAuth(source, new URL("/v3/product/actions", source.url).toString(), "POST", {
    device_id: deviceId,
    space_id: spaceId,
    action: spec.action,
    project,
    arguments: actionArgs,
  });
  const created = await handlers.createAction(createRequest);
  const createdPayload = await bodyJson(created);
  if (!created.ok) return textToolResult(createdPayload, true);
  const requestId = typeof createdPayload.request_id === "string" ? createdPayload.request_id : "";
  if (!requestId) return textToolResult({ ok: false, error: "product_request_id_missing", response: createdPayload }, true);
  const finalPayload = await waitForAction(source, requestId, waitMs, handlers);
  const action = finalPayload.action;
  const failed = finalPayload.ok === false || Boolean(action && typeof action === "object" && !Array.isArray(action) && String((action as JsonObject).status ?? "") !== "succeeded" && !finalPayload.pending);
  return textToolResult(finalPayload, failed);
}

export async function handleOrdaxMcp(request: Request, handlers: OrdaxMcpHandlers): Promise<Response> {
  if (request.method === "GET") return new Response(null, { status: 405, headers: { allow: "POST" } });
  if (request.method !== "POST") return new Response(null, { status: 405, headers: { allow: "GET, POST" } });

  const sessionProbe = await handlers.session(cloneWithAuth(request, new URL("/v3/product/session", request.url).toString(), "GET"));
  if (!sessionProbe.ok) {
    const headers = new Headers(sessionProbe.headers);
    headers.set("www-authenticate", `Bearer resource_metadata="${new URL("/.well-known/oauth-protected-resource", request.url).toString()}"`);
    return new Response(sessionProbe.body, { status: sessionProbe.status, headers });
  }

  let message: JsonObject;
  try {
    const raw = await request.json();
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) throw new Error("invalid");
    message = raw as JsonObject;
  } catch {
    return rpcError(null, -32700, "Parse error");
  }
  if (message.jsonrpc !== "2.0" || typeof message.method !== "string") return rpcError(message.id, -32600, "Invalid Request");
  const id = message.id;
  const method = message.method;
  if (method === "notifications/initialized") return new Response(null, { status: 202 });
  if (method === "ping") return rpcResult(id, {});
  if (method === "initialize") return rpcResult(id, {
    protocolVersion: "2025-06-18",
    capabilities: { tools: { listChanged: false } },
    serverInfo: { name: "ORDAX Dev", version: "0.4.0" },
    instructions: "Use ORDAX Dev only when the user asks to work with a connected ORDAX device or one of its registered projects. List connected devices before project-scoped work when the target is unknown. Respect project boundaries and the user’s explicit intent. Write, execute, Git and Blender mutation tools remain grant- and audit-protected by the ORDAX Runtime.",
  });
  if (method === "tools/list") return rpcResult(id, { tools: toolDefinitions() });
  if (method === "tools/call") {
    const params = message.params;
    if (!params || typeof params !== "object" || Array.isArray(params)) return rpcError(id, -32602, "Invalid params");
    const name = typeof (params as JsonObject).name === "string" ? String((params as JsonObject).name) : "";
    const rawArgs = (params as JsonObject).arguments;
    const args = rawArgs && typeof rawArgs === "object" && !Array.isArray(rawArgs) ? rawArgs as JsonObject : {};
    if (!specFor(name)) return rpcError(id, -32601, "Tool not found", { tool: name });
    try {
      return rpcResult(id, await callTool(request, name, args, handlers));
    } catch (error) {
      return rpcResult(id, textToolResult({ ok: false, error: "ordax_mcp_internal_error", detail: error instanceof Error ? error.message : String(error) }, true));
    }
  }
  return rpcError(id, -32601, "Method not found");
}

