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

const TOOLS: ToolSpec[] = [
  { name: "ordax_session", description: "Inspect the authenticated ORDAX Product session." },
  { name: "ordax_targets", description: "List ORDAX devices, Spaces and grants visible to the authenticated user." },
  { name: "ordax_action_status", description: "Read the status/result of a previously queued ORDAX action.", properties: { request_id: STRING }, required: ["request_id"] },
  { name: "repository_catalog", description: "List repositories registered on an ORDAX device.", action: "workspace.repository_catalog", properties: { device_id: DEVICE, space_id: SPACE, wait_for_completion_ms: WAIT }, required: ["device_id"] },
  { name: "project_inventory", description: "Inspect a bounded inventory of one registered project.", action: "project.inventory", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, max_depth: { type: "integer", minimum: 1, maximum: 12 }, max_entries: { type: "integer", minimum: 1, maximum: 10000 }, wait_for_completion_ms: WAIT }, required: ["device_id", "project"] },
  { name: "project_text_read", description: "Read a granted text file inside a registered project.", action: "project.text_read", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, path: STRING, wait_for_completion_ms: WAIT }, required: ["device_id", "project", "path"] },
  { name: "project_text_write", description: "Write a granted project text file with SHA-256 concurrency protection.", action: "project.text_write", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, path: STRING, content: STRING, expected_sha256: STRING, create: BOOLEAN, wait_for_completion_ms: WAIT }, required: ["device_id", "project", "path", "content"] },
  { name: "project_text_patch", description: "Patch a granted project text file using exact replacements and a SHA-256 precondition.", action: "project.text_patch", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, path: STRING, expected_sha256: STRING, replacements: { type: "array", items: { type: "object" }, maxItems: 100 }, wait_for_completion_ms: WAIT }, required: ["device_id", "project", "path", "expected_sha256", "replacements"] },
  { name: "git_status", description: "Read bounded Git status for a granted project.", action: "git.status", projectRequired: true, properties: { device_id: DEVICE, project: PROJECT, space_id: SPACE, wait_for_completion_ms: WAIT }, required: ["device_id", "project"] },
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
  return TOOLS.map((tool) => ({
    name: tool.name,
    description: tool.description,
    securitySchemes: [{ type: "oauth2", scopes: ["email"] }],
    _meta: { securitySchemes: [{ type: "oauth2", scopes: ["email"] }] },
    inputSchema: {
      type: "object",
      properties: tool.properties ?? {},
      required: tool.required ?? [],
      additionalProperties: false,
    },
  }));
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
      if (["succeeded", "failed", "cancelled"].includes(state)) return { ...payload, pending: false };
    }
    if (Date.now() >= deadline) return { ok: true, pending: true, request_id: requestId, message: "Action is still running; call ordax_action_status with this request_id." };
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
}

async function callTool(source: Request, name: string, args: JsonObject, handlers: OrdaxMcpHandlers): Promise<JsonObject> {
  if (name === "ordax_session") {
    const response = await handlers.session(cloneWithAuth(source, new URL("/v3/product/session", source.url).toString(), "GET"));
    const payload = await bodyJson(response);
    return textToolResult(payload, !response.ok);
  }
  if (name === "ordax_targets") {
    const response = await handlers.targets(cloneWithAuth(source, new URL("/v3/product/targets", source.url).toString(), "GET"));
    const payload = await bodyJson(response);
    return textToolResult(payload, !response.ok);
  }
  if (name === "ordax_action_status") {
    const requestId = typeof args.request_id === "string" ? args.request_id : "";
    if (!requestId) return textToolResult({ ok: false, error: "request_id_required" }, true);
    const response = await handlers.getAction(cloneWithAuth(source, new URL(`/v3/product/actions/${requestId}`, source.url).toString(), "GET"), requestId);
    const payload = await bodyJson(response);
    return textToolResult(payload, !response.ok);
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
    serverInfo: { name: "ordax-studio-remote", version: "1.0.0" },
    instructions: "ORDAX Studio remote access. Discover targets first, then use project-scoped typed tools. Writes remain grant- and audit-protected on the Device Agent.",
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

