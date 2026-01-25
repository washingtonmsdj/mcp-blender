// AI Streaming Client
import { supabase } from "@/integrations/supabase/client";
import type { OrdaxSpec } from "@/lib/ordax/types";
import type { CodeSemanticPatch } from "@/lib/ordax/code-mutator";

export type ChatMsg = { role: "user" | "assistant"; content: string };

export type StreamCallback = (chunk: string) => void;

export type GeneratedFile = {
  path: string;
  content: string;
};

export type GenerationResult = {
  files: GeneratedFile[];
  spec?: OrdaxSpec;
  patch?: CodeSemanticPatch;
  fullResponse: string;
  planWarnings?: string[];
  assistantSummary?: string;
  appliedEdits?: string[];
  semanticPatch?: unknown;
  report?: unknown;
  engineGapReport?: unknown;
  error?: string;
  message?: string;
};

export type NewGamePhase = "plan" | "spec";

function extractFirstJsonObject(text: string): string | null {
  const start = text.indexOf("{");
  const end = text.lastIndexOf("}");
  if (start === -1 || end === -1 || end <= start) return null;
  return text.slice(start, end + 1);
}

export async function generateWithStreaming(
  messages: ChatMsg[],
  currentSpec?: OrdaxSpec,
  projectFiles?: GeneratedFile[],
  onChunk?: StreamCallback
): Promise<{ result?: GenerationResult; error?: string }> {
  try {
    // Call streaming function
    const { data, error } = await supabase.functions.invoke("game-ai-chat-stream", {
      body: { messages, currentSpec, projectFiles },
    });

    if (error) {
      return { error: error.message };
    }

    // For now, handle non-streaming response
    // In production, implement SSE client
    const fullResponse = data?.response || "";

    if (onChunk) {
      // Simulate streaming for demo
      const words = fullResponse.split(" ");
      for (let i = 0; i < words.length; i++) {
        onChunk(words[i] + " ");
        await new Promise((resolve) => setTimeout(resolve, 50));
      }
    }

    // Parse response
    try {
      const parsed = JSON.parse(fullResponse);

      if (parsed.files && parsed.spec) {
        return {
          result: {
            files: parsed.files,
            spec: parsed.spec,
            fullResponse,
          },
        };
      }

      // Fallback to old format
      return {
        result: {
          files: [],
          spec: parsed,
          fullResponse,
        },
      };
    } catch (parseError) {
      return { error: "Failed to parse AI response" };
    }
  } catch (error) {
    return {
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

// SSE Client for true streaming
export class StreamingClient {
  private eventSource: EventSource | null = null;
  private abortController: AbortController | null = null;

  async stream(
    messages: ChatMsg[],
    currentSpec?: OrdaxSpec,
    projectFiles?: GeneratedFile[],
    onChunk?: StreamCallback,
    onComplete?: (result: GenerationResult) => void,
    onError?: (error: string) => void,
    options?: {
      phase?: NewGamePhase;
      approvedPlan?: unknown;
      approvedPlanHuman?: string;
      mode?: "spec" | "code_patch";
      targetGameId?: string;
    }
  ) {
    try {
      // Get token (optional for now)
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;

      // Avoid relying on protected SupabaseClient internals.
      const baseUrl = import.meta.env.VITE_SUPABASE_URL as string | undefined;
      const anonKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY as string | undefined;
      if (!baseUrl) {
        onError?.("VITE_SUPABASE_URL não configurada");
        return;
      }
      if (!anonKey) {
        onError?.("VITE_SUPABASE_PUBLISHABLE_KEY não configurada");
        return;
      }

      const url = new URL(`${baseUrl}/functions/v1/game-ai-chat-stream`);

      // Cancel any previous in-flight stream
      this.abortController?.abort();
      this.abortController = new AbortController();

      const response = await fetch(url.toString(), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          // Required for calling backend functions from the browser.
          apikey: anonKey,
          Authorization: `Bearer ${token ?? anonKey}`,
        },
        signal: this.abortController.signal,
        body: JSON.stringify({ messages, currentSpec, projectFiles, ...(options ?? {}) }),
      });

      if (!response.ok) {
        let details = "";
        try {
          details = await response.text();
        } catch {
          // ignore
        }
        onError?.(
          `HTTP ${response.status} ${response.statusText}${details ? ` — ${details.slice(0, 500)}` : ""}`
        );
        return;
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let fullResponse = "";
      let buffer = "";

      if (!reader) {
        onError?.("No reader available");
        return;
      }

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        let newlineIndex: number;
        while ((newlineIndex = buffer.indexOf("\n")) !== -1) {
          let line = buffer.slice(0, newlineIndex);
          buffer = buffer.slice(newlineIndex + 1);
          if (line.endsWith("\r")) line = line.slice(0, -1);
          if (!line || line.startsWith(":")) continue;
          if (!line.startsWith("data: ")) continue;

          const jsonStr = line.slice(6).trim();
          if (!jsonStr || jsonStr === "[DONE]") continue;

          try {
            const parsed = JSON.parse(jsonStr);
            const content = parsed.choices?.[0]?.delta?.content as string | undefined;
            if (content) {
              fullResponse += content;
              onChunk?.(content);
            }
          } catch {
            // Incomplete JSON: put it back and wait for more.
            buffer = line + "\n" + buffer;
            break;
          }
        }
      }

      // Parse final response
      try {
        const jsonCandidate = extractFirstJsonObject(fullResponse) ?? fullResponse;
        const parsed = JSON.parse(jsonCandidate);

        if (parsed?.error) {
          onError?.(typeof parsed?.message === "string" ? parsed.message : String(parsed.error));
          return;
        }

        const spec = parsed?.spec ? (parsed.spec as OrdaxSpec) : undefined;
        const patch = parsed?.patch as CodeSemanticPatch | undefined;
        const planWarnings = Array.isArray(parsed?.planWarnings)
          ? parsed.planWarnings.filter((s: unknown) => typeof s === "string")
          : undefined;
        const assistantSummary = typeof parsed?.assistantSummary === "string" ? parsed.assistantSummary : undefined;
        const appliedEdits = Array.isArray(parsed?.appliedEdits)
          ? parsed.appliedEdits.filter((s: unknown) => typeof s === "string")
          : undefined;
        onComplete?.({
          files: parsed.files || [],
          spec,
          patch,
          planWarnings,
          assistantSummary,
          appliedEdits,
          semanticPatch: parsed?.semanticPatch,
          report: parsed?.report,
          engineGapReport: parsed?.engineGapReport,
          fullResponse,
        });
      } catch (e) {
        onError?.(
          "Failed to parse final response (JSON inválido). Tente novamente ou use o fallback."
        );
      }
    } catch (error) {
      // If user cancelled, do not treat as error.
      if (error instanceof DOMException && error.name === "AbortError") return;
      onError?.(error instanceof Error ? error.message : String(error));
    }
  }

  cancel() {
    this.abortController?.abort();
    this.abortController = null;
    if (this.eventSource) this.eventSource.close();
    this.eventSource = null;
  }
}
