import { supabase } from "@/integrations/supabase/client";
import { ordaxSpecSchema } from "@/lib/ordax/schema";
import type { OrdaxSpec } from "@/lib/ordax/types";
import { normalizeOrdaxSpec } from "@/lib/ordax/normalize";

export type ChatMsg = { role: "user" | "assistant"; content: string };

export async function generateOrdaxSpec(
  messages: ChatMsg[],
  currentSpec?: OrdaxSpec,
): Promise<{ spec?: OrdaxSpec; raw?: string; error?: string }> {
  const { data, error } = await supabase.functions.invoke("game-ai-chat", {
    body: { messages, currentSpec },
  });

  if (error) return { error: error.message };
  const raw = (data as any)?.raw as string | undefined;
  if (!raw) return { error: "Resposta vazia da IA." };

  try {
    const json = JSON.parse(raw);
    const parsed = ordaxSpecSchema.safeParse(json);
    if (!parsed.success) {
      return { raw, error: "A IA retornou JSON inválido para o schema do Ordax." };
    }
    return { spec: normalizeOrdaxSpec(parsed.data), raw };
  } catch {
    return { raw, error: "A IA não retornou JSON parseável." };
  }
}
