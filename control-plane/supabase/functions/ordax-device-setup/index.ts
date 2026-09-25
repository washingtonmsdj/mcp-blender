// User-authenticated enrollment, independent of Actions and its runners.
const URL = Deno.env.get("SUPABASE_URL") ?? "";
const KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
const REPO = "washingtonmsdj/mcp-blender";
const REPO_ID = 1141624338;
const json = (status: number, body: unknown) => new Response(JSON.stringify(body), {
  status, headers: { "content-type": "application/json", "cache-control": "no-store" },
});
const hash = async (s: string) => [...new Uint8Array(await crypto.subtle.digest(
  "SHA-256", new TextEncoder().encode(s),
))].map(b => b.toString(16).padStart(2, "0")).join("");
async function backend(path: string, body?: unknown) {
  return await fetch(`${URL}/rest/v1/${path}`, {
    method: body === undefined ? "GET" : "POST", redirect: "error",
    headers: { apikey: KEY, authorization: `Bearer ${KEY}`, "content-type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(15000),
  });
}
export async function handler(req: Request): Promise<Response> {
  if (req.method !== "POST") return json(405, { ok: false, error: "method_not_allowed" });
  if (!URL || !KEY) return json(503, { ok: false, error: "backend_unavailable" });
  try {
    const raw = await req.text();
    if (raw.length > 4096) return json(413, { ok: false, error: "request_too_large" });
    const body = JSON.parse(raw);
    if (!body || Array.isArray(body) || typeof body !== "object" ||
      Object.keys(body).some(k => !["operation", "machine_binding_sha256", "device_name", "token_sha256"].includes(k)) ||
      !/^[0-9a-f]{64}$/.test(body.machine_binding_sha256 ?? "")) {
      return json(400, { ok: false, error: "request_invalid" });
    }
    const binding = body.machine_binding_sha256;
    if (body.operation === "identify") {
      const token = req.headers.get("X-Ordax-Device-Token") ?? "";
      if (token.length < 32 || token.length > 512) return json(401, { ok: false, error: "device_auth_required" });
      const r = await backend(`ordax_device_credentials?select=device_id,ordax_devices!inner(stable_identity,mode,metadata)&token_sha256=eq.${await hash(token)}&revoked_at=is.null`);
      if (!r.ok) return json(503, { ok: false, error: "identity_unavailable" });
      const rows = await r.json();
      if (rows.length !== 1) return json(401, { ok: false, error: "device_token_invalid" });
      const d = rows[0].ordax_devices;
      if (d.mode !== "developer" || !(d.metadata?.machine_binding_sha256 === binding ||
        d.stable_identity === `github-oidc:${binding}` ||
        /^github-user:[0-9]+:/.test(d.stable_identity ?? "") && d.stable_identity.endsWith(`:${binding}`))) {
        return json(403, { ok: false, error: "machine_binding_mismatch" });
      }
      return json(200, { ok: true, protocol: "development-v2", device_id: rows[0].device_id });
    }
    if (body.operation !== "enroll" || !/^[0-9a-f]{64}$/.test(body.token_sha256 ?? "") ||
      typeof body.device_name !== "string" || body.device_name.length < 1 || body.device_name.length > 120 ||
      /[\x00-\x1f\x7f]/.test(body.device_name)) return json(400, { ok: false, error: "request_invalid" });
    const auth = req.headers.get("Authorization") ?? "";
    if (!/^Bearer [A-Za-z0-9_]+$/.test(auth) || auth.length > 1024) return json(401, { ok: false, error: "user_auth_required" });
    const headers = { authorization: auth, accept: "application/vnd.github+json", "user-agent": "OrdaX-Device-Setup", "X-GitHub-Api-Version": "2022-11-28" };
    const [userResponse, repoResponse] = await Promise.all([
      fetch("https://api.github.com/user", { headers, redirect: "error", signal: AbortSignal.timeout(15000) }),
      fetch(`https://api.github.com/repos/${REPO}`, { headers, redirect: "error", signal: AbortSignal.timeout(15000) }),
    ]);
    if (userResponse.status === 401) return json(401, { ok: false, error: "user_auth_required" });
    if (!userResponse.ok || !repoResponse.ok) return json(403, { ok: false, error: "repository_access_denied" });
    const user = await userResponse.json(), repo = await repoResponse.json();
    // Public repository visibility is not authorization. Require administrative access.
    if (!Number.isSafeInteger(user.id) || user.type !== "User" || repo.id !== REPO_ID || repo.permissions?.admin !== true) {
      return json(403, { ok: false, error: "repository_admin_required" });
    }
    const r = await backend("rpc/ordax_setup_device_v1", {
      p_github_user_id: String(user.id), p_binding: binding,
      p_name: body.device_name, p_token_sha256: body.token_sha256,
    });
    if (!r.ok) return json(409, { ok: false, error: "enrollment_rejected" });
    const result = await r.json();
    return json(200, { ...result, protocol: "development-v2" });
  } catch {
    // Never log bodies, Authorization, tokens or raw upstream errors.
    return json(503, { ok: false, error: "setup_temporarily_unavailable" });
  }
}
if (import.meta.main) Deno.serve(handler);
