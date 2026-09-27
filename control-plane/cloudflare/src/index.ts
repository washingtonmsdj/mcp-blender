import { DurableObject } from "cloudflare:workers";

interface Env {
  DB: D1Database;
  ARTIFACTS: R2Bucket;
  DEVICE_SESSIONS: DurableObjectNamespace<DeviceSession>;
  ENROLLMENT_SESSIONS: DurableObjectNamespace<EnrollmentSession>;
  ORDAX_OPERATOR_TOKEN: string;
}

type JsonObject = Record<string, unknown>;

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const HEX64_RE = /^[0-9a-f]{64}$/i;
const GITHUB_REPOSITORY = "washingtonmsdj/mcp-blender";
const GITHUB_REPOSITORY_ID = 1141624338;

const ACTION_PREFIXES = [
  "blender.", "unity.", "git.", "project.", "projects.", "artifact.",
  "observation.", "game_assets.", "geo.", "visual.", "agent.",
];

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
    },
  });
}

function nowIso(): string {
  return new Date().toISOString();
}

function randomHex(bytes = 32): string {
  const value = crypto.getRandomValues(new Uint8Array(bytes));
  return [...value].map((item) => item.toString(16).padStart(2, "0")).join("");
}

async function sha256Text(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return [...new Uint8Array(digest)]
    .map((item) => item.toString(16).padStart(2, "0"))
    .join("");
}

function bytesToBase64(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}

function hexToArrayBuffer(value: string): ArrayBuffer {
  const bytes = new Uint8Array(value.length / 2);
  for (let index = 0; index < bytes.length; index += 1) {
    bytes[index] = Number.parseInt(value.slice(index * 2, index * 2 + 2), 16);
  }
  return bytes.buffer;
}

function arrayBufferToHex(value: ArrayBuffer): string {
  return [...new Uint8Array(value)]
    .map((item) => item.toString(16).padStart(2, "0"))
    .join("");
}

function isRecord(value: unknown): value is JsonObject {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function actionAllowed(value: string): boolean {
  return value === "ordax.dev.adapter.invoke"
    || ACTION_PREFIXES.some((prefix) => value.startsWith(prefix));
}

async function operatorAuthorized(request: Request, env: Env): Promise<boolean> {
  const auth = request.headers.get("authorization") ?? "";
  if (!env.ORDAX_OPERATOR_TOKEN || !auth.startsWith("Bearer ")) return false;
  const supplied = auth.slice(7);
  if (supplied.length !== env.ORDAX_OPERATOR_TOKEN.length) return false;
  const [a, b] = await Promise.all([
    sha256Text(supplied),
    sha256Text(env.ORDAX_OPERATOR_TOKEN),
  ]);
  return a === b;
}

async function authenticateDevice(
  env: Env,
  deviceId: string,
  rawToken: string,
): Promise<{ ok: true } | { ok: false; error: string }> {
  if (!UUID_RE.test(deviceId) || rawToken.length < 32 || rawToken.length > 512) {
    return { ok: false, error: "device_auth_required" };
  }
  const digest = await sha256Text(rawToken);
  const row = await env.DB.prepare(
    "SELECT id, revoked_at FROM ordax_devices WHERE id = ?1 AND token_sha256 = ?2",
  ).bind(deviceId, digest).first<{ id: string; revoked_at: string | null }>();
  if (!row) return { ok: false, error: "invalid_device_token" };
  if (row.revoked_at) return { ok: false, error: "device_revoked" };
  return { ok: true };
}

async function parseSmallJson(request: Request, maxBytes = 128 * 1024): Promise<JsonObject | null> {
  const raw = await request.text();
  if (raw.length === 0 || raw.length > maxBytes) return null;
  try {
    const value = JSON.parse(raw);
    return isRecord(value) ? value : null;
  } catch {
    return null;
  }
}

async function verifyGithubRepositoryAdmin(
  rawToken: string,
): Promise<{ userId: string } | null> {
  if (!rawToken || rawToken.length > 1024) return null;
  const headers = {
    authorization: `Bearer ${rawToken}`,
    accept: "application/vnd.github+json",
    "user-agent": "OrdaX-Device-Setup",
    "X-GitHub-Api-Version": "2022-11-28",
  };
  const [userResponse, repoResponse] = await Promise.all([
    fetch("https://api.github.com/user", {
      headers,
      redirect: "error",
      signal: AbortSignal.timeout(15_000),
    }),
    fetch(`https://api.github.com/repos/${GITHUB_REPOSITORY}`, {
      headers,
      redirect: "error",
      signal: AbortSignal.timeout(15_000),
    }),
  ]);
  if (!userResponse.ok || !repoResponse.ok) return null;

  const user = await userResponse.json() as JsonObject;
  const repo = await repoResponse.json() as JsonObject;
  const permissions = isRecord(repo.permissions) ? repo.permissions : {};
  if (
    !Number.isSafeInteger(user.id)
    || user.type !== "User"
    || repo.id !== GITHUB_REPOSITORY_ID
    || permissions.admin !== true
  ) {
    return null;
  }
  return { userId: String(user.id) };
}

async function deviceSetup(request: Request, env: Env): Promise<Response> {
  const body = await parseSmallJson(request, 16 * 1024);
  if (!body) return json({ ok: false, error: "request_invalid" }, 400);

  const operation = typeof body.operation === "string" ? body.operation : "";
  const binding = typeof body.machine_binding_sha256 === "string"
    ? body.machine_binding_sha256.toLowerCase()
    : "";
  if (!HEX64_RE.test(binding)) {
    return json({ ok: false, error: "request_invalid" }, 400);
  }

  if (operation === "identify") {
    const rawToken = request.headers.get("X-Ordax-Device-Token") ?? "";
    if (rawToken.length < 32 || rawToken.length > 512) {
      return json({ ok: false, error: "device_auth_required" }, 401);
    }
    const digest = await sha256Text(rawToken);
    const row = await env.DB.prepare(
      `SELECT id, machine_binding_sha256, revoked_at
       FROM ordax_devices WHERE token_sha256 = ?1`,
    ).bind(digest).first<{
      id: string;
      machine_binding_sha256: string | null;
      revoked_at: string | null;
    }>();
    if (!row || row.revoked_at) {
      return json({ ok: false, error: "device_token_invalid" }, 401);
    }
    if (row.machine_binding_sha256 !== binding) {
      return json({ ok: false, error: "machine_binding_mismatch" }, 403);
    }
    return json({
      ok: true,
      protocol: "cloudflare-v3",
      device_id: row.id,
    });
  }

  if (operation !== "enroll") {
    return json({ ok: false, error: "operation_not_allowed" }, 400);
  }

  const tokenSha256 = typeof body.token_sha256 === "string"
    ? body.token_sha256.toLowerCase()
    : "";
  const deviceName = typeof body.device_name === "string"
    ? body.device_name.trim()
    : "";
  if (
    !HEX64_RE.test(tokenSha256)
    || deviceName.length < 1
    || deviceName.length > 120
    || /[\x00-\x1f\x7f]/.test(deviceName)
  ) {
    return json({ ok: false, error: "request_invalid" }, 400);
  }

  const authorization = request.headers.get("Authorization") ?? "";
  if (!authorization.startsWith("Bearer ") || authorization.length > 1100) {
    return json({ ok: false, error: "user_auth_required" }, 401);
  }
  const github = await verifyGithubRepositoryAdmin(authorization.slice(7));
  if (!github) {
    return json({ ok: false, error: "repository_admin_required" }, 403);
  }

  const id = env.ENROLLMENT_SESSIONS.idFromName(binding);
  return env.ENROLLMENT_SESSIONS.get(id).fetch("https://enrollment.internal/enroll", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "X-Ordax-GitHub-User-Id": github.userId,
    },
    body: JSON.stringify({
      machine_binding_sha256: binding,
      device_name: deviceName,
      token_sha256: tokenSha256,
    }),
  });
}

async function provisionDevice(request: Request, env: Env): Promise<Response> {
  if (!await operatorAuthorized(request, env)) return json({ ok: false, error: "operator_unauthorized" }, 401);
  const body = await parseSmallJson(request, 16 * 1024);
  if (!body) return json({ ok: false, error: "invalid_json" }, 400);

  const deviceId = typeof body.device_id === "string" && UUID_RE.test(body.device_id)
    ? body.device_id
    : crypto.randomUUID();
  const name = typeof body.name === "string" ? body.name.trim().slice(0, 120) : "OrdaX Device";
  if (!name) return json({ ok: false, error: "device_name_required" }, 400);

  const token = randomHex(32);
  const tokenSha256 = await sha256Text(token);
  const createdAt = nowIso();
  await env.DB.prepare(
    `INSERT INTO ordax_devices (id, name, token_sha256, created_at, revoked_at)
     VALUES (?1, ?2, ?3, ?4, NULL)
     ON CONFLICT(id) DO UPDATE SET
       name = excluded.name,
       token_sha256 = excluded.token_sha256,
       revoked_at = NULL`,
  ).bind(deviceId, name, tokenSha256, createdAt).run();

  return json({
    ok: true,
    device_id: deviceId,
    device_token: token,
    protocol: "cloudflare-v3",
  }, 201);
}

async function deleteDevice(request: Request, env: Env, deviceId: string): Promise<Response> {
  if (!await operatorAuthorized(request, env)) {
    return json({ ok: false, error: "operator_unauthorized" }, 401);
  }
  if (!UUID_RE.test(deviceId)) {
    return json({ ok: false, error: "device_id_invalid" }, 400);
  }

  const existing = await env.DB.prepare(
    "SELECT id FROM ordax_devices WHERE id = ?1",
  ).bind(deviceId).first();
  if (!existing) return json({ ok: false, error: "device_not_found" }, 404);

  const artifactRows = await env.DB.prepare(
    "SELECT storage_path FROM ordax_artifacts WHERE device_id = ?1",
  ).bind(deviceId).all<{ storage_path: string }>();
  for (const row of artifactRows.results ?? []) {
    if (row.storage_path) await env.ARTIFACTS.delete(row.storage_path);
  }

  const statements = [
    env.DB.prepare(
      "DELETE FROM ordax_job_events WHERE job_id IN (SELECT id FROM ordax_jobs WHERE device_id = ?1)",
    ).bind(deviceId),
    env.DB.prepare(
      "DELETE FROM ordax_artifacts WHERE device_id = ?1",
    ).bind(deviceId),
    env.DB.prepare(
      "DELETE FROM ordax_jobs WHERE device_id = ?1",
    ).bind(deviceId),
    env.DB.prepare(
      "DELETE FROM ordax_devices WHERE id = ?1",
    ).bind(deviceId),
  ];
  const results = await env.DB.batch(statements);
  const deleted = results[3];

  return json({
    ok: true,
    device_id: deviceId,
    deleted: (deleted?.meta.changes ?? 0) === 1,
    artifacts_deleted: artifactRows.results?.length ?? 0,
  });
}

async function enqueueJob(request: Request, env: Env): Promise<Response> {
  if (!await operatorAuthorized(request, env)) return json({ ok: false, error: "operator_unauthorized" }, 401);
  const body = await parseSmallJson(request);
  if (!body) return json({ ok: false, error: "invalid_json" }, 400);

  const deviceId = typeof body.device_id === "string" ? body.device_id : "";
  const action = typeof body.action === "string" ? body.action : "";
  const project = body.project == null ? null : typeof body.project === "string" ? body.project : "";
  if (!UUID_RE.test(deviceId) || !actionAllowed(action) || project === "") {
    return json({ ok: false, error: "job_invalid" }, 400);
  }
  const device = await env.DB.prepare(
    "SELECT id FROM ordax_devices WHERE id = ?1 AND revoked_at IS NULL",
  ).bind(deviceId).first();
  if (!device) return json({ ok: false, error: "device_not_found" }, 404);

  const payload = isRecord(body.payload) ? { ...body.payload } : {};
  if (project) {
    if (payload.project != null && payload.project !== project) {
      return json({ ok: false, error: "project_conflict" }, 400);
    }
    payload.project = project;
  }

  const payloadBytes = new TextEncoder().encode(JSON.stringify(payload));
  if (payloadBytes.byteLength > 64 * 1024) {
    return json({ ok: false, error: "payload_too_large" }, 413);
  }
  const payloadB64 = bytesToBase64(payloadBytes);
  const payloadSha256 = await sha256Text(new TextDecoder().decode(payloadBytes));
  const jobId = crypto.randomUUID();
  const effectId = crypto.randomUUID();
  const createdAt = nowIso();

  await env.DB.prepare(
    `INSERT INTO ordax_jobs
      (id, device_id, capability, payload_canonical_b64, payload_sha256, status,
       effect_id, execution_epoch, created_at)
     VALUES (?1, ?2, ?3, ?4, ?5, 'queued', ?6, 0, ?7)`,
  ).bind(jobId, deviceId, action, payloadB64, payloadSha256, effectId, createdAt).run();

  const id = env.DEVICE_SESSIONS.idFromName(deviceId);
  await env.DEVICE_SESSIONS.get(id).fetch("https://device.internal/wake", {
    method: "POST",
    headers: { "X-Ordax-Device-Id": deviceId },
  });

  return json({ ok: true, job_id: jobId, effect_id: effectId, status: "queued" }, 201);
}

async function getJob(request: Request, env: Env, jobId: string): Promise<Response> {
  if (!await operatorAuthorized(request, env)) {
    return json({ ok: false, error: "operator_unauthorized" }, 401);
  }
  if (!UUID_RE.test(jobId)) return json({ ok: false, error: "job_id_invalid" }, 400);

  const row = await env.DB.prepare(
    `SELECT id, device_id, capability, status, effect_id, attempt_id, lease_id,
            execution_epoch, agent_instance_id, boot_id, lease_expires_at,
            result_json, result_sha256, error_code, created_at, started_at, finished_at
     FROM ordax_jobs WHERE id = ?1`,
  ).bind(jobId).first<Record<string, unknown>>();
  if (!row) return json({ ok: false, error: "job_not_found" }, 404);

  const events = await env.DB.prepare(
    `SELECT stage, message, progress_percent, created_at
     FROM ordax_job_events WHERE job_id = ?1 ORDER BY id ASC LIMIT 200`,
  ).bind(jobId).all();
  const artifacts = await env.DB.prepare(
    `SELECT id, file_name, kind, content_type, sha256, size_bytes, created_at
     FROM ordax_artifacts WHERE job_id = ?1 ORDER BY created_at ASC`,
  ).bind(jobId).all();

  let result: unknown = null;
  if (typeof row.result_json === "string" && row.result_json) {
    try { result = JSON.parse(row.result_json); } catch { result = null; }
  }
  const { result_json: _ignored, ...publicRow } = row;
  return json({
    ok: true,
    job: { ...publicRow, result },
    events: events.results ?? [],
    artifacts: artifacts.results ?? [],
  });
}

async function uploadArtifact(request: Request, env: Env, parts: string[]): Promise<Response> {
  const jobId = parts[2] ?? "";
  const artifactId = parts[3] ?? "";
  const deviceId = request.headers.get("X-Ordax-Device-Id") ?? "";
  const token = request.headers.get("X-Ordax-Device-Token") ?? "";
  if (!UUID_RE.test(jobId) || !UUID_RE.test(artifactId)) {
    return json({ ok: false, error: "artifact_path_invalid" }, 400);
  }
  const auth = await authenticateDevice(env, deviceId, token);
  if (!auth.ok) return json({ ok: false, error: auth.error }, 401);

  const job = await env.DB.prepare(
    "SELECT id FROM ordax_jobs WHERE id = ?1 AND device_id = ?2",
  ).bind(jobId, deviceId).first();
  if (!job) return json({ ok: false, error: "job_not_found" }, 404);

  const fileName = (request.headers.get("X-Ordax-Artifact-Name") ?? "artifact.bin")
    .replace(/[^a-zA-Z0-9._-]+/g, "-").slice(0, 180) || "artifact.bin";
  const kind = (request.headers.get("X-Ordax-Artifact-Kind") ?? "artifact").slice(0, 80);
  const sha256 = request.headers.get("X-Ordax-Artifact-Sha256") ?? "";
  const sizeBytes = Number(request.headers.get("X-Ordax-Artifact-Size") ?? request.headers.get("content-length") ?? "0");
  if (!HEX64_RE.test(sha256) || !Number.isSafeInteger(sizeBytes) || sizeBytes < 0 || sizeBytes > 90 * 1024 * 1024) {
    return json({ ok: false, error: "artifact_metadata_invalid" }, 400);
  }
  const metadataRaw = request.headers.get("X-Ordax-Artifact-Metadata") ?? "{}";
  try {
    const parsed = JSON.parse(metadataRaw);
    if (!isRecord(parsed)) throw new Error("not object");
  } catch {
    return json({ ok: false, error: "artifact_metadata_invalid" }, 400);
  }

  const storagePath = `${deviceId}/${jobId}/${artifactId}-${fileName}`;
  let stored: R2Object | null;
  try {
    stored = await env.ARTIFACTS.put(storagePath, request.body, {
      sha256: hexToArrayBuffer(sha256),
      httpMetadata: {
        contentType: request.headers.get("content-type") ?? "application/octet-stream",
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (/\((10014|10037)\)\s*$/.test(message)) {
      return json({ ok: false, error: "artifact_checksum_rejected" }, 422);
    }
    throw error;
  }

  if (!stored) {
    return json({ ok: false, error: "artifact_storage_write_failed" }, 503);
  }
  const storedSha256 = stored.checksums.sha256;
  if (
    stored.size !== sizeBytes
    || !storedSha256
    || arrayBufferToHex(storedSha256).toLowerCase() !== sha256
  ) {
    await env.ARTIFACTS.delete(storagePath);
    return json({ ok: false, error: "artifact_integrity_mismatch" }, 422);
  }

  const readToken = randomHex(32);
  const readTokenSha256 = await sha256Text(readToken);
  const createdAt = nowIso();
  const readExpiresAt = new Date(Date.now() + 60 * 60 * 1000).toISOString();
  await env.DB.prepare(
    `INSERT INTO ordax_artifacts
      (id, job_id, device_id, storage_path, file_name, kind, content_type, sha256,
       size_bytes, metadata_json, read_token_sha256, read_expires_at, created_at)
     VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13)`,
  ).bind(
    artifactId, jobId, deviceId, storagePath, fileName, kind,
    request.headers.get("content-type") ?? "application/octet-stream",
    sha256, sizeBytes, metadataRaw, readTokenSha256, readExpiresAt, createdAt,
  ).run();

  const origin = new URL(request.url).origin;
  const signedUrl = `${origin}/v3/artifacts/${artifactId}?token=${encodeURIComponent(readToken)}`;
  return json({
    ok: true,
    artifact_id: artifactId,
    storage_path: storagePath,
    signed_url: signedUrl,
    expires_at: readExpiresAt,
  }, 201);
}

async function downloadArtifact(request: Request, env: Env, artifactId: string): Promise<Response> {
  if (!UUID_RE.test(artifactId)) return json({ ok: false, error: "artifact_id_invalid" }, 400);
  const token = new URL(request.url).searchParams.get("token") ?? "";
  if (token.length < 32 || token.length > 512) return json({ ok: false, error: "artifact_token_required" }, 401);
  const digest = await sha256Text(token);
  const row = await env.DB.prepare(
    `SELECT storage_path, file_name, content_type, read_expires_at
     FROM ordax_artifacts WHERE id = ?1 AND read_token_sha256 = ?2`,
  ).bind(artifactId, digest).first<{
    storage_path: string;
    file_name: string;
    content_type: string | null;
    read_expires_at: string;
  }>();
  if (!row || new Date(row.read_expires_at).getTime() <= Date.now()) {
    return json({ ok: false, error: "artifact_token_invalid_or_expired" }, 403);
  }
  const object = await env.ARTIFACTS.get(row.storage_path);
  if (!object) return json({ ok: false, error: "artifact_not_found" }, 404);

  const headers = new Headers();
  object.writeHttpMetadata(headers);
  headers.set("content-type", row.content_type ?? headers.get("content-type") ?? "application/octet-stream");
  headers.set("content-disposition", `inline; filename="${row.file_name.replace(/"/g, "")}"`);
  headers.set("cache-control", "private, no-store");
  return new Response(object.body, { headers });
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const parts = url.pathname.split("/").filter(Boolean);

    if (request.method === "GET" && url.pathname === "/health") {
      return json({ ok: true, service: "ordax-control-plane-v3" });
    }

    if (request.method === "GET" && url.pathname === "/v3/device/ws") {
      if ((request.headers.get("Upgrade") ?? "").toLowerCase() !== "websocket") {
        return json({ ok: false, error: "websocket_required" }, 426);
      }
      const deviceId = url.searchParams.get("device_id") ?? "";
      const token = request.headers.get("X-Ordax-Device-Token") ?? "";
      const auth = await authenticateDevice(env, deviceId, token);
      if (!auth.ok) return json({ ok: false, error: auth.error }, 401);

      const id = env.DEVICE_SESSIONS.idFromName(deviceId);
      const headers = new Headers(request.headers);
      headers.set("X-Ordax-Device-Id", deviceId);
      headers.delete("X-Ordax-Device-Token");
      return env.DEVICE_SESSIONS.get(id).fetch("https://device.internal/ws", {
        method: "GET",
        headers,
      });
    }

    if (request.method === "POST" && url.pathname === "/v3/device/setup") {
      return deviceSetup(request, env);
    }
    if (request.method === "POST" && url.pathname === "/v3/devices") {
      return provisionDevice(request, env);
    }
    if (request.method === "DELETE" && parts[0] === "v3" && parts[1] === "devices" && parts.length === 3) {
      return deleteDevice(request, env, parts[2]);
    }
    if (request.method === "POST" && url.pathname === "/v3/jobs") {
      return enqueueJob(request, env);
    }
    if (request.method === "GET" && parts[0] === "v3" && parts[1] === "jobs" && parts.length === 3) {
      return getJob(request, env, parts[2]);
    }
    if (request.method === "PUT" && parts[0] === "v3" && parts[1] === "artifacts" && parts.length === 4) {
      return uploadArtifact(request, env, parts);
    }
    if (request.method === "GET" && parts[0] === "v3" && parts[1] === "artifacts" && parts.length === 3) {
      return downloadArtifact(request, env, parts[2]);
    }

    return json({ ok: false, error: "not_found" }, 404);
  },
};

export class EnrollmentSession extends DurableObject<Env> {
  constructor(ctx: DurableObjectState, env: Env) {
    super(ctx, env);
  }

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);
    if (request.method !== "POST" || url.pathname !== "/enroll") {
      return json({ ok: false, error: "not_found" }, 404);
    }

    const githubUserId = request.headers.get("X-Ordax-GitHub-User-Id") ?? "";
    if (!/^[0-9]{1,32}$/.test(githubUserId)) {
      return json({ ok: false, error: "user_identity_invalid" }, 401);
    }
    const body = await parseSmallJson(request, 8 * 1024);
    if (!body) return json({ ok: false, error: "request_invalid" }, 400);

    const binding = typeof body.machine_binding_sha256 === "string"
      ? body.machine_binding_sha256.toLowerCase()
      : "";
    const tokenSha256 = typeof body.token_sha256 === "string"
      ? body.token_sha256.toLowerCase()
      : "";
    const name = typeof body.device_name === "string" ? body.device_name.trim() : "";
    if (!HEX64_RE.test(binding) || !HEX64_RE.test(tokenSha256) || !name) {
      return json({ ok: false, error: "request_invalid" }, 400);
    }

    const existing = await this.env.DB.prepare(
      `SELECT id, owner_github_user_id, enrollment_window_started_at, enrollment_count
       FROM ordax_devices WHERE machine_binding_sha256 = ?1`,
    ).bind(binding).first<{
      id: string;
      owner_github_user_id: string | null;
      enrollment_window_started_at: string | null;
      enrollment_count: number;
    }>();

    if (existing?.owner_github_user_id && existing.owner_github_user_id !== githubUserId) {
      return json({ ok: false, error: "device_owner_mismatch" }, 403);
    }

    const now = new Date();
    const previousWindow = existing?.enrollment_window_started_at
      ? new Date(existing.enrollment_window_started_at)
      : null;
    const sameWindow = Boolean(
      previousWindow
      && Number.isFinite(previousWindow.getTime())
      && now.getTime() - previousWindow.getTime() < 60 * 60 * 1000,
    );
    const previousCount = sameWindow ? Number(existing?.enrollment_count ?? 0) : 0;
    if (previousCount >= 10) {
      return json({ ok: false, error: "enrollment_rate_limited" }, 429);
    }

    const deviceId = existing?.id ?? crypto.randomUUID();
    const windowStartedAt = sameWindow && previousWindow
      ? previousWindow.toISOString()
      : now.toISOString();
    const enrolledAt = now.toISOString();
    const nextCount = previousCount + 1;

    if (existing) {
      const updated = await this.env.DB.prepare(
        `UPDATE ordax_devices SET
           name = ?1,
           token_sha256 = ?2,
           owner_github_user_id = ?3,
           revoked_at = NULL,
           last_enrolled_at = ?4,
           enrollment_window_started_at = ?5,
           enrollment_count = ?6
         WHERE id = ?7
           AND machine_binding_sha256 = ?8
           AND (owner_github_user_id IS NULL OR owner_github_user_id = ?3)`,
      ).bind(
        name, tokenSha256, githubUserId, enrolledAt,
        windowStartedAt, nextCount, deviceId, binding,
      ).run();
      if ((updated.meta.changes ?? 0) !== 1) {
        return json({ ok: false, error: "enrollment_conflict" }, 409);
      }
    } else {
      try {
        await this.env.DB.prepare(
          `INSERT INTO ordax_devices
            (id, name, token_sha256, created_at, revoked_at,
             machine_binding_sha256, owner_github_user_id, last_enrolled_at,
             enrollment_window_started_at, enrollment_count)
           VALUES (?1, ?2, ?3, ?4, NULL, ?5, ?6, ?7, ?8, ?9)`,
        ).bind(
          deviceId, name, tokenSha256, enrolledAt, binding,
          githubUserId, enrolledAt, windowStartedAt, nextCount,
        ).run();
      } catch {
        return json({ ok: false, error: "enrollment_conflict" }, 409);
      }
    }

    return json({
      ok: true,
      protocol: "cloudflare-v3",
      device_id: deviceId,
    });
  }
}

type SocketAttachment = {
  deviceId: string;
  agentInstanceId: string;
  bootId: string;
};

export class DeviceSession extends DurableObject<Env> {
  constructor(ctx: DurableObjectState, env: Env) {
    super(ctx, env);
  }

  private ack(ws: WebSocket, requestId: unknown, ok: boolean, extra: JsonObject = {}): void {
    ws.send(JSON.stringify({
      type: "ack",
      request_id: typeof requestId === "string" ? requestId : null,
      ok,
      ...extra,
    }));
  }

  private attachment(ws: WebSocket): SocketAttachment | null {
    const value = ws.deserializeAttachment();
    return isRecord(value)
      && typeof value.deviceId === "string"
      && typeof value.agentInstanceId === "string"
      && typeof value.bootId === "string"
      ? value as unknown as SocketAttachment
      : null;
  }

  private async deliverNextJob(ws: WebSocket, deviceId: string): Promise<void> {
    const now = nowIso();
    const candidate = await this.env.DB.prepare(
      `SELECT id, capability, payload_canonical_b64, payload_sha256, effect_id, execution_epoch
       FROM ordax_jobs
       WHERE device_id = ?1
         AND (status = 'queued' OR (status IN ('leased','running') AND lease_expires_at < ?2))
       ORDER BY created_at ASC
       LIMIT 1`,
    ).bind(deviceId, now).first<{
      id: string;
      capability: string;
      payload_canonical_b64: string;
      payload_sha256: string;
      effect_id: string;
      execution_epoch: number;
    }>();
    if (!candidate) return;

    const attachment = this.attachment(ws);
    if (!attachment) return;
    const attemptId = crypto.randomUUID();
    const leaseId = crypto.randomUUID();
    const nextEpoch = Number(candidate.execution_epoch ?? 0) + 1;
    const leaseExpiresAt = new Date(Date.now() + 120_000).toISOString();

    const update = await this.env.DB.prepare(
      `UPDATE ordax_jobs SET
         status = 'leased',
         attempt_id = ?1,
         lease_id = ?2,
         execution_epoch = ?3,
         agent_instance_id = ?4,
         boot_id = ?5,
         lease_expires_at = ?6
       WHERE id = ?7 AND device_id = ?8
         AND (status = 'queued' OR lease_expires_at < ?9)`,
    ).bind(
      attemptId, leaseId, nextEpoch, attachment.agentInstanceId,
      attachment.bootId, leaseExpiresAt, candidate.id, deviceId, now,
    ).run();
    if ((update.meta.changes ?? 0) !== 1) return;

    ws.send(JSON.stringify({
      type: "job",
      job: {
        job_id: candidate.id,
        capability: candidate.capability,
        payload_canonical_b64: candidate.payload_canonical_b64,
        payload_sha256: candidate.payload_sha256,
        effect_id: candidate.effect_id,
        attempt_id: attemptId,
        lease_id: leaseId,
        execution_epoch: nextEpoch,
        agent_instance_id: attachment.agentInstanceId,
        boot_id: attachment.bootId,
        expires_at: leaseExpiresAt,
      },
    }));
  }

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);
    const deviceId = request.headers.get("X-Ordax-Device-Id") ?? "";
    if (!UUID_RE.test(deviceId)) return json({ ok: false, error: "device_id_invalid" }, 400);

    if (url.pathname === "/ws") {
      if ((request.headers.get("Upgrade") ?? "").toLowerCase() !== "websocket") {
        return json({ ok: false, error: "websocket_required" }, 426);
      }
      const pair = new WebSocketPair();
      const client = pair[0];
      const server = pair[1];
      this.ctx.acceptWebSocket(server);
      const agentInstanceId = request.headers.get("X-Ordax-Agent-Instance") ?? "";
      const bootId = request.headers.get("X-Ordax-Boot-Id") ?? "";
      if (!UUID_RE.test(agentInstanceId) || !UUID_RE.test(bootId)) {
        server.close(1008, "invalid runtime identity");
        return new Response(null, { status: 101, webSocket: client });
      }
      server.serializeAttachment({ deviceId, agentInstanceId, bootId });
      await this.env.DB.prepare(
        "UPDATE ordax_devices SET last_seen_at = ?1 WHERE id = ?2",
      ).bind(nowIso(), deviceId).run();
      server.send(JSON.stringify({
        type: "hello",
        device_id: deviceId,
        protocol: "cloudflare-v3",
      }));
      await this.deliverNextJob(server, deviceId);
      return new Response(null, { status: 101, webSocket: client });
    }

    if (url.pathname === "/wake" && request.method === "POST") {
      for (const ws of this.ctx.getWebSockets()) {
        if (this.attachment(ws)?.deviceId === deviceId) {
          await this.deliverNextJob(ws, deviceId);
        }
      }
      return json({ ok: true });
    }

    return json({ ok: false, error: "not_found" }, 404);
  }

  async webSocketMessage(ws: WebSocket, raw: string | ArrayBuffer): Promise<void> {
    let message: JsonObject;
    try {
      const text = typeof raw === "string" ? raw : new TextDecoder().decode(raw);
      const parsed = JSON.parse(text);
      if (!isRecord(parsed)) throw new Error("not object");
      message = parsed;
    } catch {
      this.ack(ws, null, false, { error: "invalid_json" });
      return;
    }

    const attachment = this.attachment(ws);
    if (!attachment) {
      ws.close(1008, "missing identity");
      return;
    }
    const requestId = message.request_id;
    const type = typeof message.type === "string" ? message.type : "";
    const deviceId = attachment.deviceId;

    if (type === "heartbeat") {
      await this.env.DB.prepare(
        "UPDATE ordax_devices SET last_seen_at = ?1 WHERE id = ?2 AND revoked_at IS NULL",
      ).bind(nowIso(), deviceId).run();
      this.ack(ws, requestId, true, { server_time: nowIso() });
      return;
    }

    const jobId = typeof message.job_id === "string" ? message.job_id : "";
    const leaseId = typeof message.lease_id === "string" ? message.lease_id : "";
    const executionEpoch = Number.isSafeInteger(message.execution_epoch)
      ? Number(message.execution_epoch) : 0;
    if (!UUID_RE.test(jobId) || !UUID_RE.test(leaseId) || executionEpoch < 1) {
      this.ack(ws, requestId, false, { error: "execution_context_invalid" });
      return;
    }

    const active = await this.env.DB.prepare(
      `SELECT id FROM ordax_jobs
       WHERE id = ?1 AND device_id = ?2 AND lease_id = ?3 AND execution_epoch = ?4
         AND agent_instance_id = ?5 AND boot_id = ?6
         AND status IN ('leased','running')`,
    ).bind(
      jobId, deviceId, leaseId, executionEpoch,
      attachment.agentInstanceId, attachment.bootId,
    ).first();
    if (!active) {
      this.ack(ws, requestId, false, { error: "lease_not_active" });
      return;
    }

    if (type === "start") {
      const startedAt = nowIso();
      const result = await this.env.DB.prepare(
        `UPDATE ordax_jobs SET status = 'running', started_at = COALESCE(started_at, ?1)
         WHERE id = ?2 AND device_id = ?3 AND lease_id = ?4 AND execution_epoch = ?5`,
      ).bind(startedAt, jobId, deviceId, leaseId, executionEpoch).run();
      this.ack(ws, requestId, (result.meta.changes ?? 0) === 1);
      return;
    }

    if (type === "lease_heartbeat") {
      const leasedUntil = new Date(Date.now() + 120_000).toISOString();
      await this.env.DB.prepare(
        `UPDATE ordax_jobs SET lease_expires_at = ?1
         WHERE id = ?2 AND device_id = ?3 AND lease_id = ?4 AND execution_epoch = ?5`,
      ).bind(leasedUntil, jobId, deviceId, leaseId, executionEpoch).run();
      this.ack(ws, requestId, true, { leased_until: leasedUntil });
      return;
    }

    if (type === "progress") {
      const percent = message.progress_percent == null ? null
        : Number.isInteger(message.progress_percent)
          ? Math.max(0, Math.min(100, Number(message.progress_percent)))
          : null;
      const stage = typeof message.stage === "string" ? message.stage.slice(0, 96) : "info";
      const text = typeof message.message === "string" ? message.message.slice(0, 512) : null;
      await this.env.DB.prepare(
        `INSERT INTO ordax_job_events (job_id, stage, message, progress_percent, created_at)
         VALUES (?1, ?2, ?3, ?4, ?5)`,
      ).bind(jobId, stage, text, percent, nowIso()).run();
      this.ack(ws, requestId, true);
      return;
    }

    if (type === "report") {
      const status = typeof message.status === "string" ? message.status : "";
      const resultSha256 = typeof message.result_sha256 === "string" ? message.result_sha256 : "";
      if (!["succeeded", "failed", "cancelled"].includes(status) || !HEX64_RE.test(resultSha256)) {
        this.ack(ws, requestId, false, { error: "report_invalid" });
        return;
      }
      const resultValue = isRecord(message.result) ? message.result : {};
      const resultJson = JSON.stringify(resultValue);
      if (new TextEncoder().encode(resultJson).byteLength > 512 * 1024) {
        this.ack(ws, requestId, false, { error: "result_too_large" });
        return;
      }

      const finishedAt = nowIso();
      const update = await this.env.DB.prepare(
        `UPDATE ordax_jobs SET
           status = ?1, result_json = ?2, result_sha256 = ?3,
           error_code = ?4, finished_at = ?5, lease_expires_at = NULL
         WHERE id = ?6 AND device_id = ?7 AND lease_id = ?8 AND execution_epoch = ?9`,
      ).bind(
        status, resultJson, resultSha256,
        typeof message.error_code === "string" ? message.error_code : null,
        finishedAt, jobId, deviceId, leaseId, executionEpoch,
      ).run();
      const ok = (update.meta.changes ?? 0) === 1;
      this.ack(ws, requestId, ok, ok ? { status } : { error: "report_rejected" });
      if (ok) await this.deliverNextJob(ws, deviceId);
      return;
    }

    this.ack(ws, requestId, false, { error: "operation_not_allowed" });
  }

  async webSocketClose(
    _ws: WebSocket,
    _code: number,
    _reason: string,
    _wasClean: boolean,
  ): Promise<void> {
    // Presence is freshness-based in D1; disconnect doesn't revoke the device.
  }

  async webSocketError(_ws: WebSocket, _error: unknown): Promise<void> {
    // The next device reconnect reuses the same Durable Object identity.
  }
}
