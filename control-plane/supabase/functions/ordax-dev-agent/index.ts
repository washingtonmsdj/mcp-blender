import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;
const BUCKET = "ordax-dev-artifacts";

const db = createClient(SUPABASE_URL, SERVICE_ROLE_KEY, {
  auth: { persistSession: false, autoRefreshToken: false },
});

const encoder = new TextEncoder();

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
    },
  });
}

async function sha256(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", encoder.encode(value));
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function randomToken(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function safeFileName(value: string): string {
  const clean = value.replace(/[^a-zA-Z0-9._-]+/g, "-").slice(0, 120);
  return clean || "artifact.bin";
}

async function authenticateAgent(req: Request) {
  const token = req.headers.get("x-ordax-agent-token")?.trim();
  if (!token) return null;

  const tokenHash = await sha256(token);
  const { data, error } = await db
    .from("ordax_dev_agents")
    .select("id,agent_name,disabled_at")
    .eq("token_hash", tokenHash)
    .maybeSingle();

  if (error || !data || data.disabled_at) return null;
  return data;
}

Deno.serve(async (req: Request) => {
  try {
    if (req.method !== "POST") return json({ error: "method_not_allowed" }, 405);

    if (req.headers.get("apikey") !== ANON_KEY) {
      return json({ error: "invalid_apikey" }, 401);
    }

    const body = await req.json();
    const op = String(body?.op ?? "");

    if (op === "register") {
      const pairingCode = String(body?.pairing_code ?? "").trim().toUpperCase();
      const agentName = String(body?.agent_name ?? "").trim();
      const machineId = String(body?.machine_id ?? "").trim();

      if (!pairingCode || !agentName || !machineId) {
        return json({ error: "missing_pairing_fields" }, 400);
      }

      const pairingHash = await sha256(pairingCode);
      const { data: pairing, error: pairingError } = await db
        .from("ordax_dev_pairing_tokens")
        .select("id,expires_at,consumed_at,agent_name_hint")
        .eq("code_hash", pairingHash)
        .maybeSingle();

      if (
        pairingError ||
        !pairing ||
        pairing.consumed_at ||
        new Date(pairing.expires_at).getTime() <= Date.now()
      ) {
        return json({ error: "pairing_invalid_or_expired" }, 403);
      }

      if (pairing.agent_name_hint && pairing.agent_name_hint !== agentName) {
        return json({ error: "pairing_agent_mismatch" }, 403);
      }

      const machineHash = await sha256(machineId);
      const agentToken = randomToken();
      const tokenHash = await sha256(agentToken);
      const now = new Date().toISOString();

      const { data: agent, error: agentError } = await db
        .from("ordax_dev_agents")
        .upsert(
          {
            agent_name: agentName,
            machine_id_hash: machineHash,
            token_hash: tokenHash,
            status: "online",
            capabilities: body?.capabilities ?? [],
            metadata: body?.metadata ?? {},
            agent_version: body?.agent_version ?? null,
            paired_at: now,
            last_seen_at: now,
            disabled_at: null,
          },
          { onConflict: "agent_name" },
        )
        .select("id,agent_name")
        .single();

      if (agentError || !agent) {
        return json({ error: "agent_registration_failed", detail: agentError?.message }, 500);
      }

      const { error: consumeError } = await db
        .from("ordax_dev_pairing_tokens")
        .update({ consumed_at: now })
        .eq("id", pairing.id)
        .is("consumed_at", null);

      if (consumeError) {
        return json({ error: "pairing_consume_failed", detail: consumeError.message }, 500);
      }

      return json({
        ok: true,
        agent_id: agent.id,
        agent_name: agent.agent_name,
        agent_token: agentToken,
      });
    }

    const agent = await authenticateAgent(req);
    if (!agent) return json({ error: "agent_unauthorized" }, 401);

    if (op === "heartbeat") {
      const now = new Date().toISOString();
      const { error } = await db
        .from("ordax_dev_agents")
        .update({
          status: body?.status ?? "online",
          capabilities: body?.capabilities ?? [],
          metadata: body?.metadata ?? {},
          agent_version: body?.agent_version ?? null,
          last_seen_at: now,
          last_error: body?.last_error ?? null,
        })
        .eq("id", agent.id);
      if (error) return json({ error: "heartbeat_failed", detail: error.message }, 500);
      return json({ ok: true, server_time: now });
    }

    if (op === "claim") {
      const { data, error } = await db.rpc("ordax_claim_dev_job", {
        p_agent_name: agent.agent_name,
      });
      if (error) return json({ error: "claim_failed", detail: error.message }, 500);
      return json({ ok: true, job: data ?? null });
    }

    const jobId = String(body?.job_id ?? "");
    if (!jobId) return json({ error: "job_id_required" }, 400);

    const { data: job, error: jobError } = await db
      .from("ordax_dev_jobs")
      .select("id,agent_name,lease_token,status")
      .eq("id", jobId)
      .eq("agent_name", agent.agent_name)
      .maybeSingle();

    if (jobError || !job) return json({ error: "job_not_found" }, 404);

    if (op === "event") {
      const { error } = await db.from("ordax_dev_job_events").insert({
        job_id: jobId,
        level: String(body?.level ?? "info"),
        message: String(body?.message ?? "").slice(0, 4000),
        data: body?.data ?? {},
      });
      if (error) return json({ error: "event_failed", detail: error.message }, 500);
      return json({ ok: true });
    }

    if (op === "complete") {
      const leaseToken = String(body?.lease_token ?? "");
      if (!leaseToken || leaseToken !== String(job.lease_token ?? "")) {
        return json({ error: "lease_mismatch" }, 409);
      }

      const ok = Boolean(body?.ok);
      const now = new Date().toISOString();
      const { error } = await db
        .from("ordax_dev_jobs")
        .update({
          status: ok ? "succeeded" : "failed",
          finished_at: now,
          result: body?.result ?? {},
          lease_token: null,
          leased_until: null,
        })
        .eq("id", jobId)
        .eq("agent_name", agent.agent_name)
        .eq("lease_token", leaseToken);

      if (error) return json({ error: "complete_failed", detail: error.message }, 500);

      await db
        .from("ordax_dev_agents")
        .update({
          status: "online",
          last_job_id: jobId,
          last_seen_at: now,
          last_error: ok ? null : String(body?.result?.summary ?? "job failed").slice(0, 4000),
        })
        .eq("id", agent.id);

      return json({ ok: true });
    }

    if (op === "upload_ticket") {
      const fileName = safeFileName(String(body?.file_name ?? "artifact.bin"));
      const kind = String(body?.kind ?? "artifact").slice(0, 80);
      const objectPath = `${agent.id}/${jobId}/${crypto.randomUUID()}-${fileName}`;

      const { data: signed, error: signedError } = await db.storage
        .from(BUCKET)
        .createSignedUploadUrl(objectPath);

      if (signedError || !signed) {
        return json({ error: "upload_ticket_failed", detail: signedError?.message }, 500);
      }

      const { data: artifact, error: artifactError } = await db
        .from("ordax_dev_artifacts")
        .insert({
          job_id: jobId,
          agent_name: agent.agent_name,
          kind,
          file_name: fileName,
          storage_path: objectPath,
          metadata: { state: "upload-issued" },
        })
        .select("id")
        .single();

      if (artifactError || !artifact) {
        return json({ error: "artifact_record_failed", detail: artifactError?.message }, 500);
      }

      return json({
        ok: true,
        artifact_id: artifact.id,
        bucket: BUCKET,
        path: objectPath,
        token: signed.token,
      });
    }

    if (op === "artifact_done") {
      const artifactId = String(body?.artifact_id ?? "");
      if (!artifactId) return json({ error: "artifact_id_required" }, 400);

      const { error } = await db
        .from("ordax_dev_artifacts")
        .update({
          sha256: body?.sha256 ?? null,
          size_bytes: body?.size_bytes ?? null,
          metadata: body?.metadata ?? { state: "uploaded" },
        })
        .eq("id", artifactId)
        .eq("job_id", jobId)
        .eq("agent_name", agent.agent_name);

      if (error) return json({ error: "artifact_finalize_failed", detail: error.message }, 500);
      return json({ ok: true });
    }

    return json({ error: "unknown_operation" }, 400);
  } catch (error) {
    return json(
      {
        error: "internal_error",
        detail: error instanceof Error ? error.message : String(error),
      },
      500,
    );
  }
});
