import { useMemo, useState, useRef, useEffect } from "react";
import { Send, Sparkles, StopCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import type { OrdaxSpec } from "@/lib/ordax/types";
import { StreamingClient, type ChatMsg } from "@/lib/ordax/ai-streaming";
import { normalizeOrdaxSpec } from "@/lib/ordax/normalize";
import { autoFixOrdaxSpec, lintOrdaxSpec } from "@/lib/ordax/spec-lint";
import { contextManager } from "@/lib/ordax/context-manager";
import { vfs } from "@/lib/vfs/VirtualFileSystem";
import { supabase } from "@/integrations/supabase/client";
import { PlanReviewDrawer, type GamePlanResult } from "@/components/ordax/PlanReviewDrawer";
import { buildHumanGamePlanText } from "@/lib/ordax/human-game-plan";
import { validateRuntimeAgainstPlan } from "@/lib/ordax/validateRuntimeAgainstPlan";
import { applyCodeSemanticPatch, loadCodeGameFromVfs, type CodeSemanticPatch } from "@/lib/ordax/code-mutator";
import { extractRuntimeSpecFromGameCode } from "@/games/_template";

function summarizePatch(patch: CodeSemanticPatch) {
  const dirs = new Set<string>();
  let hasCodeGameUpdate = false;
  const prefix = `/vfs/games/${patch.gameId}/`;

  for (const op of patch.ops) {
    const p =
      op.op === "rename_file"
        ? op.to
        : op.op === "create_file" || op.op === "update_file" || op.op === "delete_file"
          ? op.path
          : "";
    const rel = typeof p === "string" && p.startsWith(prefix) ? p.slice(prefix.length) : String(p ?? "");
    const seg = rel.split("/").filter(Boolean);
    if (seg.length >= 2) dirs.add(seg[0]);
    if (op.op === "update_file" && op.path === `${prefix}codeGame.ts`) hasCodeGameUpdate = true;
  }

  const touched = Array.from(dirs).sort();
  const needsRegistration = touched.some((d) =>
    ["systems", "entities", "ui", "state", "input", "audio", "spawn"].includes(d)
  );
  const warnings: string[] = [];
  if (needsRegistration && !hasCodeGameUpdate) {
    warnings.push("Falta update em codeGame.ts (registro obrigatório). O backend deve rejeitar.");
  }
  return { touchedDirs: touched, needsRegistration, hasCodeGameUpdate, warnings };
}

function wantsAudioFromPrompt(prompt: string): boolean {
  const t = (prompt || "").toLowerCase();
  return (
    t.includes("áudio") ||
    t.includes("audio") ||
    t.includes("som") ||
    t.includes("sfx") ||
    t.includes("música") ||
    t.includes("musica") ||
    t.includes("music")
  );
}

function wantsDesertFromPrompt(prompt: string): boolean {
  const t = (prompt || "").toLowerCase();
  // Keep it simple and explicit. If user says “desert”, they likely want a ground-like vibe.
  return t.includes("deserto") || t.includes("desert") || t.includes("areia") || t.includes("duna");
}

function wantsSpaceFromPrompt(prompt: string): boolean {
  const t = (prompt || "").toLowerCase();
  return (
    t.includes("espaço") ||
    t.includes("espaco") ||
    t.includes("space") ||
    t.includes("galáxia") ||
    t.includes("galaxia") ||
    t.includes("nebula") ||
    t.includes("estrela") ||
    t.includes("star")
  );
}

function wantsShieldFromPrompt(prompt: string): boolean {
  const t = (prompt || "").toLowerCase();
  return t.includes("escudo") || t.includes("shield");
}

function ensureBackgroundIntent(spec: OrdaxSpec, prompt: string): { spec: OrdaxSpec; applied: boolean; note?: string } {
  const wantsDesert = wantsDesertFromPrompt(prompt);
  const wantsSpace = wantsSpaceFromPrompt(prompt);

  // If user explicitly asked for desert (and not space), avoid space cues.
  if (wantsDesert && !wantsSpace) {
    const currentLayers = spec.visual?.background?.layers ?? [];
    const hadSpaceLayers = currentLayers.some((l) => l.type === "starfield" || l.type === "nebula");

    const nextLayers: NonNullable<OrdaxSpec["visual"]>['background']['layers'] = [
      { type: "solid", parallax: 0 },
      { type: "gradient", parallax: 0.12 },
    ];

    const nextTheme = {
      ...(spec.visual?.theme ?? {}),
      // Warm sand-ish palette (HSL only).
      background: (spec.visual?.theme?.background ?? "hsl(38, 40%, 6%)"),
      primary: (spec.visual?.theme?.primary ?? "hsl(38, 90%, 55%)"),
      accent: (spec.visual?.theme?.accent ?? "hsl(12, 90%, 55%)"),
    };

    return {
      spec: {
        ...spec,
        visual: {
          ...(spec.visual ?? {}),
          theme: nextTheme,
          background: { layers: nextLayers },
        },
      },
      applied: hadSpaceLayers || !spec.visual?.background?.layers?.length,
      note: "🌵 Fundo: forçado para deserto (sem starfield/nebula)",
    };
  }

  return { spec, applied: false };
}

function ensureAudioInSpec(spec: OrdaxSpec, prompt: string): { spec: OrdaxSpec; applied: boolean } {
  if (!wantsAudioFromPrompt(prompt)) return { spec, applied: false };

  const systems = Array.isArray(spec.systems) ? spec.systems : [];
  const hasAudio = systems.includes("AudioSystem");
  const nextSystems = hasAudio ? systems : [...systems, "AudioSystem"];

  // Defaults (can be swapped later for real assets). We only fill what is missing.
  const nextAudio = {
    ...(spec.audio ?? {}),
    music: spec.audio?.music ?? "/audio/bgm.mp3",
    sounds: {
      collision: spec.audio?.sounds?.collision ?? "/audio/hit.wav",
      score: spec.audio?.sounds?.score ?? "/audio/coin.wav",
      gameOver: spec.audio?.sounds?.gameOver ?? "/audio/gameover.wav",
      jump: spec.audio?.sounds?.jump ?? "/audio/jump.wav",
      // Shooter-friendly
      shoot: spec.audio?.sounds?.shoot ?? "/audio/shoot.wav",
      ...(spec.audio?.sounds ?? {}),
    },
  } satisfies OrdaxSpec["audio"];

  // If we changed nothing, avoid noise.
  const changed = !hasAudio || !spec.audio;
  return {
    spec: {
      ...spec,
      systems: nextSystems,
      audio: nextAudio,
    },
    applied: changed,
  };
}

function ensureShieldInSpec(spec: OrdaxSpec, prompt: string): { spec: OrdaxSpec; applied: boolean } {
  if (!wantsShieldFromPrompt(prompt)) return { spec, applied: false };

  const entities = spec.scene?.entities ?? [];
  const playerIdx = entities.findIndex((e) => e.type === "player" || e.id === "player");
  if (playerIdx < 0) return { spec, applied: false };

  const player = entities[playerIdx];
  const props = (player.props ?? {}) as Record<string, unknown>;

  // Default shield: 50 points, slow regen.
  const nextProps = {
    ...props,
    shield: (typeof props.shield === "number" ? props.shield : 50),
    shieldRegen: (typeof props.shieldRegen === "number" ? props.shieldRegen : 12),
  };

  const nextEntities = [...entities];
  nextEntities[playerIdx] = { ...player, props: nextProps };

  // If there is a UI overlay entity, hint it should show shield.
  const uiIdx = nextEntities.findIndex((e) => e.type === "ui");
  if (uiIdx >= 0) {
    const ui = nextEntities[uiIdx];
    const uiProps = (ui.props ?? {}) as Record<string, unknown>;
    nextEntities[uiIdx] = { ...ui, props: { ...uiProps, showShieldBar: true } };
  }

  return {
    spec: {
      ...spec,
      scene: {
        ...(spec.scene ?? { gravity: { x: 0, y: 0 } }),
        entities: nextEntities,
      },
    },
    applied: true,
  };
}

function applyIntentPatches(spec: OrdaxSpec, prompt: string): { spec: OrdaxSpec; patches: string[]; notes: string[] } {
  let out = spec;
  const patches: string[] = [];
  const notes: string[] = [];

  const bg = ensureBackgroundIntent(out, prompt);
  out = bg.spec;
  if (bg.applied) {
    patches.push("FORCE_BACKGROUND_FROM_PROMPT");
    if (bg.note) notes.push(bg.note);
  }

  const audio = ensureAudioInSpec(out, prompt);
  out = audio.spec;
  if (audio.applied) patches.push("FORCE_AUDIO_FROM_PROMPT");

  const shield = ensureShieldInSpec(out, prompt);
  out = shield.spec;
  if (shield.applied) patches.push("FORCE_SHIELD_FROM_PROMPT");

  return { spec: out, patches, notes };
}

type Props = {
  onSpec: (spec: OrdaxSpec, raw: string) => void;
  currentSpec?: OrdaxSpec;
  /** When set, enables code-first mutation mode against /vfs/games/<gameId>/ */
  gameId?: string;
};

const examplePrompts = [
  "Jogo de nave espacial com asteroides",
  "Platformer 2D com moedas",
  "Crie um jogo de corrida top-down",
];

export function StudioChatPanel({ onSpec, currentSpec, gameId }: Props) {
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [streamingContent, setStreamingContent] = useState("");
  const streamingClientRef = useRef<StreamingClient | null>(null);
  const scrollAreaRef = useRef<HTMLDivElement | null>(null);
  const shouldStickToBottomRef = useRef(true);

  // AI Debug
  const [showDebug, setShowDebug] = useState(false);
  const [debugRaw, setDebugRaw] = useState<string>("");
  const [debugSanitized, setDebugSanitized] = useState<string>("");
  const [debugError, setDebugError] = useState<string>("");
  const [debugFixes, setDebugFixes] = useState<string>("");
  const lastUserPromptRef = useRef<string>("");

  // Code Mutator UX: patch preview + confirm
  const [pendingPatch, setPendingPatch] = useState<CodeSemanticPatch | null>(null);
  const [pendingPatchOpen, setPendingPatchOpen] = useState(false);
  const [pendingPatchSummary, setPendingPatchSummary] = useState<ReturnType<typeof summarizePatch> | null>(null);
  const pendingPatchMetaRef = useRef<{ assistantSummary?: string; appliedEdits?: string[] } | null>(null);

  const isEditMode = !!currentSpec;
  const codeEntryPath = gameId ? `/vfs/games/${gameId}/codeGame.ts` : undefined;
  const isCodeMutatorMode = !!(isEditMode && gameId && codeEntryPath && vfs.getNodeByPath(codeEntryPath));

  // NEW_GAME planning gate
  const [planReviewOpen, setPlanReviewOpen] = useState(false);
  const [planResult, setPlanResult] = useState<GamePlanResult | null>(null);
  const approvedPlanHuman = useMemo(() => {
    if (!planResult?.plan) return "";
    return buildHumanGamePlanText({
      plan: planResult.plan,
      planDiff: planResult.planDiff,
      warnings: planResult.planWarnings,
      engineGapReport: planResult.engineGapReport ?? null,
    });
  }, [planResult]);
  const [pendingNewGameMessages, setPendingNewGameMessages] = useState<ChatMsg[] | null>(null);
  const [acceptingPlan, setAcceptingPlan] = useState(false);

  // Keep the last accepted plan as a persistent contract for subsequent edits.
  const [acceptedPlan, setAcceptedPlan] = useState<unknown | null>(null);
  const acceptedPlanHuman = useMemo(() => {
    if (!planResult?.plan) return "";
    return buildHumanGamePlanText({
      plan: planResult.plan,
      planDiff: planResult.planDiff,
      warnings: planResult.planWarnings,
      engineGapReport: planResult.engineGapReport ?? null,
    });
  }, [planResult]);

  type ChatStage =
    | "idle"
    | "planning"
    | "awaiting_accept"
    | "generating"
    | "applying"
    | "coaching";
  const [stage, setStage] = useState<ChatStage>("idle");

  const placeholder = isCodeMutatorMode
    ? `Peça mudanças no código do jogo (patches TS em /vfs/games/${gameId}/). Ex: "refatore codeGame.ts para organizar systems"…`
    : isEditMode
    ? "Peça melhorias no jogo atual (ex: 'melhore o visual do player', 'adicione tela de pause', 'balanceie a dificuldade')…"
    : "Descreva seu jogo aqui…";

  const requestCoachTips = async (spec: OrdaxSpec) => {
    try {
      setStage("coaching");
      const { data, error } = await supabase.functions.invoke("game-ai-chat", {
        body: {
          mode: "coach",
          // Não enviamos prompt “inventado” no client; o coach usa apenas o currentSpec.
          messages: [],
          currentSpec: spec,
        },
      });

      if (error) {
        toast.error(`Coach: ${error.message}`);
        return;
      }

      const text = (data as any)?.text as string | undefined;
      if (!text?.trim()) return;

      const assistantMessage: ChatMsg = { role: "assistant", content: text.trim() };
      setMessages((prev) => [...prev, assistantMessage]);
      contextManager.addMessage(assistantMessage);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      toast.error(`Coach: ${msg}`);
    } finally {
      setStage("idle");
    }
  };

  const debugSummary = useMemo(() => {
    if (!debugSanitized) return null;
    try {
      const parsed = JSON.parse(debugSanitized) as Partial<OrdaxSpec>;
      const entities = parsed?.scene?.entities?.length ?? 0;
      const systems = parsed?.systems?.length ?? 0;
      const gameType = parsed?.gameType ?? "unknown";
      return { entities, systems, gameType };
    } catch {
      return null;
    }
  }, [debugSanitized]);

  const getViewportEl = () => {
    const root = scrollAreaRef.current;
    if (!root) return null;
    return root.querySelector<HTMLElement>("[data-radix-scroll-area-viewport]");
  };

  const scrollToBottom = (behavior: ScrollBehavior = "auto") => {
    const viewport = getViewportEl();
    if (!viewport) return;
    viewport.scrollTo({ top: viewport.scrollHeight, behavior });
  };

  // Update context when spec changes
  useEffect(() => {
    if (currentSpec) {
      contextManager.updateSpec(currentSpec);
    }
  }, [currentSpec]);

  const send = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || isLoading) return;

    const userMessage: ChatMsg = { role: "user", content: trimmed };
    lastUserPromptRef.current = trimmed;
    setMessages((prev) => [...prev, userMessage]);
    contextManager.addMessage(userMessage);
    setInput("");
    setIsLoading(true);
    setStage(isEditMode ? "generating" : "planning");
    setIsStreaming(false);
    setStreamingContent("");
    // If user was already at the bottom, keep following the stream.
    // If not, don't force-scroll while they read older messages.
    shouldStickToBottomRef.current = true;

    // Reset debug state for this run
    setDebugError("");
    setDebugRaw("");
    setDebugSanitized("");
    setDebugFixes("");

    // NEW_GAME now has a mandatory planning gate.
    if (!isEditMode) {
      try {
        const { data, error } = await supabase.functions.invoke("game-ai-chat", {
          body: {
            mode: "spec",
            phase: "plan",
            messages: [...messages, userMessage],
          },
        });

        setIsLoading(false);
        setStage("awaiting_accept");

        if (error) {
          toast.error(`Erro: ${error.message}`);
          return;
        }

        // Planner can return either the new structured payload (preferred)
        // or a legacy payload with { raw: "{...json...}" }.
        const isStructured = (data as any)?.kind === "GAME_PLAN_RESULT";
        const legacyRaw = (data as any)?.raw as string | undefined;

        let nextPlan: GamePlanResult | null = null;

        if (isStructured) {
          nextPlan = {
            plan: (data as any)?.plan,
            planWarnings: (data as any)?.planWarnings,
            planDiff: (data as any)?.planDiff,
          };
        } else if (legacyRaw?.trim()) {
          // Show the raw in debug, and parse it as the plan.
          setDebugRaw(legacyRaw);
          try {
            nextPlan = {
              plan: JSON.parse(legacyRaw),
              planWarnings: [
                "Planner retornou payload legado (raw). Diff/avisos podem estar incompletos até atualizar o endpoint.",
              ],
            };
          } catch (e) {
            toast.error("Planner retornou RAW inválido");
            setDebugError(e instanceof Error ? e.message : String(e));
            return;
          }
        } else {
          toast.error("Resposta inesperada do planner");
          setDebugError(JSON.stringify(data));
          return;
        }

        setPlanResult(nextPlan);
        setPendingNewGameMessages([...messages, userMessage]);
        setPlanReviewOpen(true);

        const assistantMessage: ChatMsg = {
          role: "assistant",
          content:
            "🧠 GAME_PLAN gerado. Revise o plano no painel e clique em ‘Aceitar e gerar runtimeSpec’.",
        };
        setMessages((prev) => [...prev, assistantMessage]);
        contextManager.addMessage(assistantMessage);
      } catch (e) {
        setIsLoading(false);
        setStage("idle");
        const msg = e instanceof Error ? e.message : String(e);
        toast.error(`Planner: ${msg}`);
        setDebugError(msg);
      }
      return;
    }

    // EDIT mode: generate immediately
    await generateSpecStreaming([...messages, userMessage], currentSpec);
  };

  const generateSpecStreaming = async (fullMessages: ChatMsg[], spec?: OrdaxSpec, approvedPlan?: unknown) => {
    // Get project files
    const projectFiles = isCodeMutatorMode && gameId
      ? vfs
          .getAllFiles()
          .filter((f) => f.path.startsWith(`/vfs/games/${gameId}/`))
          .map((f) => ({ path: f.path, content: f.content }))
      : vfs.getAllFiles().map((f) => ({
          path: f.path,
          content: f.content,
        }));

    // Create streaming client
    const client = new StreamingClient();
    streamingClientRef.current = client;

    setIsStreaming(true);
    setStreamingContent("");
    setStage("generating");

    try {
      await client.stream(
        fullMessages,
        isCodeMutatorMode ? undefined : spec,
        projectFiles,
        (chunk) => setStreamingContent((prev) => prev + chunk),
        (result) => {
          setIsStreaming(false);
          setIsLoading(false);
          setAcceptingPlan(false);
          setStreamingContent("");
          setStage("applying");

          setDebugRaw(result.fullResponse ?? "");

          // ==============================
          // CODE MUTATOR MODE (code-first)
          // ==============================
          if (isCodeMutatorMode && result.patch && gameId && codeEntryPath) {
            try {
              const patch = result.patch as CodeSemanticPatch;

              // Quality-first: preview + confirm before applying
              setPendingPatch(patch);
              setPendingPatchSummary(summarizePatch(patch));
              pendingPatchMetaRef.current = {
                assistantSummary: (result as any)?.assistantSummary as string | undefined,
                appliedEdits: (result as any)?.appliedEdits as string[] | undefined,
              };
              setPendingPatchOpen(true);
              setStage("idle");
            } catch (e) {
              const msg = e instanceof Error ? e.message : String(e);
              toast.error(msg);
              setDebugError(msg);
              setStage("idle");
              setMessages((prev) => [...prev, { role: "assistant", content: `❌ ${msg}` }]);
            }
            return;
          }

          // Update files in VFS (JSON/spec pipeline)
          if (result.files && result.files.length > 0) {
            result.files.forEach((file) => {
              const existing = vfs.getNodeByPath(file.path);
              if (existing && existing.type === "file") {
                vfs.updateFileContent(existing.id, file.content);
              } else {
                const parts = file.path.split("/");
                const fileName = parts.pop() || "file.ts";
                const dirPath = parts.join("/") || "/";
                vfs.createFile(fileName, dirPath, "typescript", file.content);
              }
            });
            toast.success(`${result.files.length} arquivos atualizados!`);
          }

          if (result.spec) {
            // Contract guard-rails: reject generic/non-patch responses.
            const hasSemanticPatch = !!(result as any)?.semanticPatch;
            const hasAppliedEdits = Array.isArray((result as any)?.appliedEdits) && ((result as any).appliedEdits as any[]).length > 0;
            if (!hasSemanticPatch || !hasAppliedEdits) {
              const msg = "COMPILER_ERROR: resposta da IA sem semanticPatch/appliedEdits (rejeitada).";
              toast.error(msg);
              setDebugError(msg);
              setStage("idle");
              setMessages((prev) => [...prev, { role: "assistant", content: `❌ ${msg}` }]);
              return;
            }

            const issues = lintOrdaxSpec(result.spec as any);
            const fixed = autoFixOrdaxSpec(result.spec as any, issues);

            const promptPatched = applyIntentPatches(fixed.spec as any, lastUserPromptRef.current);
            if (fixed.fixes.length || fixed.issues.length || promptPatched.patches.length) {
              setDebugFixes(
                JSON.stringify(
                  {
                    issues: fixed.issues,
                    fixes: fixed.fixes,
                    promptPatches: promptPatched.patches,
                  },
                  null,
                  2
                )
              );
            }

            const normalized = normalizeOrdaxSpec(promptPatched.spec as any);

            // Validate runtimeSpec against the last accepted plan (if any)
            const planToValidate = approvedPlan ?? acceptedPlan;
            if (planToValidate) {
              const validation = validateRuntimeAgainstPlan(planToValidate, normalized);
              const hardErrors = validation.issues.filter((i) => i.severity === "error");
              if (hardErrors.length) {
                const msg = `COMPILER_ERROR: runtimeSpec viola o plano aceito (${hardErrors.length} erro(s)).`;
                setDebugError(
                  JSON.stringify(
                    {
                      message: msg,
                      issues: validation.issues,
                      warnings: validation.warnings,
                      engineGapReport: validation.engineGapReport,
                    },
                    null,
                    2
                  )
                );
                toast.error(msg);
                setStage("idle");
                setMessages((prev) => [...prev, { role: "assistant", content: `❌ ${msg}\n\nPeça para eu corrigir: ex: \"corrija o runtimeSpec para obedecer o plano\".` }]);
                return;
              }
              if (validation.warnings.length || validation.engineGapReport?.items?.length) {
                const warnBlock = [
                  ...(validation.warnings.length ? [`⚠️ Warnings:\n- ${validation.warnings.join("\n- ")}`] : []),
                  ...(validation.engineGapReport?.items?.length
                    ? [
                        `⚠️ ENGINE_GAP:\n- ${validation.engineGapReport.items
                          .slice(0, 5)
                          .map((it) => `${it.area}: ${it.limitation}`)
                          .join("\n- ")}`,
                      ]
                    : []),
                ].join("\n\n");
                if (warnBlock.trim()) {
                  setMessages((prev) => [...prev, { role: "assistant", content: warnBlock }]);
                }
              }
            }

            const raw = JSON.stringify(normalized, null, 2);
            setDebugSanitized(raw);

            const appliedEdits = (result as any)?.appliedEdits as string[] | undefined;
            const assistantSummaryFromModel = (result as any)?.assistantSummary as string | undefined;

            const planWarn = (result as any)?.planWarnings as string[] | undefined;
            const planWarnBlock = planWarn?.length
              ? `\n\n🧠 Plano (auto-ajustes):\n- ${planWarn.slice(0, 6).join("\n- ")}`
              : "";

            const appliedBlock = appliedEdits?.length
              ? `\n\nAlterações aplicadas:\n- ${appliedEdits.slice(0, 10).join("\n- ")}`
              : "";

            const assistantSummary: ChatMsg = {
              role: "assistant",
              content:
                (assistantSummaryFromModel?.trim()
                  ? assistantSummaryFromModel.trim()
                  : `✓ ${normalized.title || "Jogo atualizado"}` +
                    (normalized.description ? `\n${normalized.description}` : "")) +
                (wantsAudioFromPrompt(lastUserPromptRef.current)
                  ? "\n\n🔊 Áudio: ativado (AudioSystem + bloco audio)"
                  : "") +
                (promptPatched.notes?.length ? `\n\n${promptPatched.notes.join("\n")}` : "") +
                planWarnBlock +
                appliedBlock +
                "\n\nAgora me diga o que você quer melhorar no projeto (mecânicas, visual, UI, dificuldade, etc.).",
            };
            setMessages((prev) => [...prev, assistantSummary]);
            contextManager.addMessage(assistantSummary);

            onSpec(normalized, raw);
            void requestCoachTips(normalized);
          }

          // if requestCoachTips runs, it will drive stage; otherwise, go idle.
          if (!result?.spec) setStage("idle");
        },
        (error) => {
          console.warn("Streaming failed, using fallback:", error);
          setDebugError(error);
          setAcceptingPlan(false);
          void useFallbackSpec(fullMessages, spec, approvedPlan);
        },
        isCodeMutatorMode && gameId
          ? {
              mode: "code_patch",
              targetGameId: gameId,
            }
          : approvedPlan
          ? {
              phase: "spec",
              approvedPlan,
              approvedPlanHuman: acceptedPlanHuman || undefined,
            }
          : acceptedPlan
            ? {
                phase: "spec",
                approvedPlan: acceptedPlan,
                approvedPlanHuman: acceptedPlanHuman || undefined,
              }
            : undefined
      );
    } catch (error) {
      console.warn("Streaming error, using fallback:", error);
      setAcceptingPlan(false);
      void useFallbackSpec(fullMessages, spec, approvedPlan);
    }
  };

  // Fallback to original non-streaming method
  const useFallbackSpec = async (fullMessages: ChatMsg[], spec?: OrdaxSpec, approvedPlan?: unknown) => {
    try {
      // Code-first mutation fallback (non-stream)
      if (isCodeMutatorMode && gameId && codeEntryPath) {
        const projectFiles = vfs
          .getAllFiles()
          .filter((f) => f.path.startsWith(`/vfs/games/${gameId}/`))
          .map((f) => ({ path: f.path, content: f.content }));

        const { data, error } = await supabase.functions.invoke("game-ai-chat", {
          body: {
            mode: "code_patch",
            targetGameId: gameId,
            projectFiles,
            messages: fullMessages,
          },
        });

        setIsStreaming(false);
        setIsLoading(false);
        setStreamingContent("");
        setStage("applying");

        if (error) {
          toast.error(`Erro: ${error.message}`);
          setMessages((prev) => [...prev, { role: "assistant", content: `❌ Erro: ${error.message}` }]);
          return;
        }

        const raw = (data as any)?.raw as string | undefined;
        if (!raw?.trim()) {
          toast.error("Resposta vazia da IA");
          setMessages((prev) => [...prev, { role: "assistant", content: "❌ Resposta vazia da IA" }]);
          return;
        }

        setDebugRaw(raw);
        const parsed = JSON.parse(raw);
        if (parsed?.error) {
          const msg = typeof parsed?.message === "string" ? parsed.message : String(parsed.error);
          toast.error(msg);
          setDebugError(msg);
          setStage("idle");
          setMessages((prev) => [...prev, { role: "assistant", content: `❌ ${msg}` }]);
          return;
        }

        const patch = parsed?.patch as CodeSemanticPatch | undefined;
        if (!patch) {
          const msg = "COMPILER_ERROR: resposta da IA sem patch (rejeitada).";
          toast.error(msg);
          setDebugError(msg);
          setStage("idle");
          setMessages((prev) => [...prev, { role: "assistant", content: `❌ ${msg}` }]);
          return;
        }

        // Quality-first: preview + confirm before applying
        setPendingPatch(patch);
        setPendingPatchSummary(summarizePatch(patch));
        pendingPatchMetaRef.current = {
          assistantSummary: typeof parsed?.assistantSummary === "string" ? parsed.assistantSummary : undefined,
          appliedEdits: Array.isArray(parsed?.appliedEdits)
            ? parsed.appliedEdits.filter((s: unknown) => typeof s === "string")
            : undefined,
        };
        setPendingPatchOpen(true);
        setStage("idle");
        return;
      }

      const { data, error } = await supabase.functions.invoke("game-ai-chat", {
        body: { 
          messages: fullMessages,
          currentSpec: spec,
            ...((approvedPlan ?? acceptedPlan)
              ? {
                  mode: "spec",
                  phase: "spec",
                  approvedPlan: approvedPlan ?? acceptedPlan,
                  approvedPlanHuman: acceptedPlanHuman || undefined,
                }
              : {}),
        },
      });

      setIsStreaming(false);
      setIsLoading(false);
      setStreamingContent("");
      setStage("applying");

      if (error) {
        toast.error(`Erro: ${error.message}`);
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: `❌ Erro: ${error.message}`,
          },
        ]);
        return;
      }

      const raw = (data as any)?.raw as string | undefined;
      if (!raw) {
        toast.error("Resposta vazia da IA");
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: "❌ Resposta vazia da IA",
          },
        ]);
        return;
      }

      try {
        setDebugRaw(raw);
        const parsed = JSON.parse(raw);

          if ((parsed as any)?.error) {
            const msg = typeof (parsed as any)?.message === "string" ? (parsed as any).message : String((parsed as any).error);
            toast.error(msg);
            setDebugError(msg);
            setStage("idle");
            setMessages((prev) => [...prev, { role: "assistant", content: `❌ ${msg}` }]);
            return;
          }

        const json = (parsed?.spec ?? parsed) as any;
        const assistantSummaryFromModel = typeof parsed?.assistantSummary === "string" ? parsed.assistantSummary : undefined;
        const appliedEdits = Array.isArray(parsed?.appliedEdits)
          ? parsed.appliedEdits.filter((s: unknown) => typeof s === "string")
          : undefined;

          const hasSemanticPatch = !!(parsed as any)?.semanticPatch;
          const hasAppliedEdits = !!appliedEdits?.length;
          if (!hasSemanticPatch || !hasAppliedEdits) {
            const msg = "COMPILER_ERROR: resposta da IA sem semanticPatch/appliedEdits (rejeitada).";
            toast.error(msg);
            setDebugError(msg);
            setStage("idle");
            setMessages((prev) => [...prev, { role: "assistant", content: `❌ ${msg}` }]);
            return;
          }
        const assistantMessage: ChatMsg = {
          role: "assistant",
          content:
            (assistantSummaryFromModel?.trim()
              ? assistantSummaryFromModel.trim()
              : `✓ ${json.title || "Jogo gerado"}\n\n${json.description || ""}`) +
            (appliedEdits?.length ? `\n\nAlterações aplicadas:\n- ${appliedEdits.slice(0, 10).join("\n- ")}` : ""),
        };
        setMessages((prev) => [...prev, assistantMessage]);
        contextManager.addMessage(assistantMessage);

        // Update spec
        const issues = lintOrdaxSpec(json as any);
        const fixed = autoFixOrdaxSpec(json as any, issues);

        // Deterministic “intent patches” (robustness layer above the model).
        const promptPatched = applyIntentPatches(fixed.spec as any, lastUserPromptRef.current);
        if (fixed.fixes.length || fixed.issues.length || promptPatched.patches.length) {
          setDebugFixes(
            JSON.stringify(
              {
                issues: fixed.issues,
                fixes: fixed.fixes,
                promptPatches: promptPatched.patches,
              },
              null,
              2
            )
          );
        }

        const normalized = normalizeOrdaxSpec(promptPatched.spec as any);

        const planToValidate = approvedPlan ?? acceptedPlan;
        if (planToValidate) {
          const validation = validateRuntimeAgainstPlan(planToValidate, normalized);
          const hardErrors = validation.issues.filter((i) => i.severity === "error");
          if (hardErrors.length) {
            const msg = `COMPILER_ERROR: runtimeSpec viola o plano aceito (${hardErrors.length} erro(s)).`;
            setDebugError(JSON.stringify(validation, null, 2));
            toast.error(msg);
            setStage("idle");
            setMessages((prev) => [...prev, { role: "assistant", content: `❌ ${msg}` }]);
            return;
          }
        }
        const sanitized = JSON.stringify(normalized, null, 2);
        setDebugSanitized(sanitized);
        onSpec(normalized, sanitized);
        toast.success("Jogo gerado com sucesso!");

        // Dicas proativas estilo Lovable
        void requestCoachTips(normalized);
      } catch (parseError) {
        toast.error("Erro ao processar resposta");
        setDebugError(String(parseError));
        setStage("idle");
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: `❌ Erro ao processar resposta: ${parseError}`,
          },
        ]);
      }
    } catch (error) {
      setIsStreaming(false);
      setIsLoading(false);
      setStreamingContent("");
      setStage("idle");
      const errorMsg = error instanceof Error ? error.message : String(error);
      toast.error(`Erro: ${errorMsg}`);
      setDebugError(errorMsg);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `❌ Erro: ${errorMsg}`,
        },
      ]);
    } finally {
      // Safety: NEW_GAME accept flow can get here via streaming fallback.
      setAcceptingPlan(false);
    }
  };

  const applyPendingPatch = async () => {
    if (!pendingPatch || !gameId || !codeEntryPath) return;

    setPendingPatchOpen(false);
    setStage("applying");

    // Snapshot VFS for rollback safety
    const snapshot = vfs.export();
    try {
      const applyResult = applyCodeSemanticPatch(vfs as any, pendingPatch);
      if (!applyResult.ok) {
        const msg = `COMPILER_ERROR: patch rejeitado: ${("errors" in applyResult ? applyResult.errors : []).join("; ")}`;
        vfs.import(snapshot);
        toast.error(msg);
        setDebugError(msg);
        setMessages((prev) => [...prev, { role: "assistant", content: `❌ ${msg}` }]);
        setStage("idle");
        return;
      }

      // Import/extract smoke test; rollback if it fails
      const game = await loadCodeGameFromVfs(vfs as any, codeEntryPath);
      const nextSpec = extractRuntimeSpecFromGameCode(game);
      const raw = JSON.stringify(nextSpec, null, 2);
      setDebugSanitized(raw);
      onSpec(nextSpec, raw);

      toast.success(`Patch aplicado (${applyResult.appliedOps.length} ops)`);

      const meta = pendingPatchMetaRef.current;
      const assistantSummaryFromModel = meta?.assistantSummary;
      const appliedEdits = meta?.appliedEdits;
      const assistantSummary: ChatMsg = {
        role: "assistant",
        content:
          (assistantSummaryFromModel?.trim() ? assistantSummaryFromModel.trim() : "✓ Patch aplicado no código") +
          (appliedEdits?.length ? `\n\nAlterações aplicadas:\n- ${appliedEdits.slice(0, 10).join("\n- ")}` : "") +
          "\n\nPeça o próximo ajuste no código (sempre via patches).",
      };
      setMessages((prev) => [...prev, assistantSummary]);
      contextManager.addMessage(assistantSummary);
    } catch (e) {
      vfs.import(snapshot);
      const msg = e instanceof Error ? e.message : String(e);
      toast.error(`Rollback: patch quebrou import/extract — ${msg}`);
      setDebugError(msg);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `❌ Patch revertido automaticamente (quebrou import/extract).\n\nDetalhes: ${msg}` },
      ]);
    } finally {
      setPendingPatch(null);
      setPendingPatchSummary(null);
      pendingPatchMetaRef.current = null;
      setStage("idle");
    }
  };

  const cancelPendingPatch = () => {
    setPendingPatchOpen(false);
    setPendingPatch(null);
    setPendingPatchSummary(null);
    pendingPatchMetaRef.current = null;
    toast("Patch cancelado (não aplicado).", { duration: 2000 });
  };

  const acceptPlanAndGenerate = async () => {
    if (!planResult?.plan || !pendingNewGameMessages) return;
    setAcceptedPlan(planResult.plan);
    setAcceptingPlan(true);
    setIsLoading(true);
    setStage("generating");
    // Feche imediatamente para evitar a sensação de travamento; o progresso aparece no chat.
    setPlanReviewOpen(false);

    try {
      await generateSpecStreaming(pendingNewGameMessages, undefined, planResult.plan);
    } finally {
      // Safety net: se streaming/fallback falhar antes do onComplete, não deixe a UI travada.
      setAcceptingPlan(false);
    }
  };

  const stopStreaming = () => {
    if (streamingClientRef.current) {
      streamingClientRef.current.cancel();
      setIsStreaming(false);
      setIsLoading(false);
      setStreamingContent("");
      setStage("idle");
    }
  };

  const stageLabel = useMemo(() => {
    switch (stage) {
      case "planning":
        return "Planejando…";
      case "awaiting_accept":
        return "Aguardando aceitação…";
      case "generating":
        return "Gerando runtimeSpec…";
      case "applying":
        return "Aplicando mudanças…";
      case "coaching":
        return "Sugerindo próximos passos…";
      default:
        return "";
    }
  }, [stage]);

  const loadingBubbleText = useMemo(() => {
    // This bubble is used only when we have no token chunks yet.
    if (stageLabel) return stageLabel;
    return "Trabalhando…";
  }, [stageLabel]);

  // Keep the chat scroll anchored *inside the panel* (prevents the whole view from being pushed).
  useEffect(() => {
    if (!shouldStickToBottomRef.current) return;
    // Use rAF to wait the DOM update (message/stream chunk) before measuring scrollHeight.
    const id = requestAnimationFrame(() => scrollToBottom("auto"));
    return () => cancelAnimationFrame(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages.length, streamingContent, isStreaming]);

  useEffect(() => {
    const viewport = getViewportEl();
    if (!viewport) return;

    const onScroll = () => {
      const thresholdPx = 24;
      const distanceFromBottom = viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight;
      shouldStickToBottomRef.current = distanceFromBottom <= thresholdPx;
    };

    viewport.addEventListener("scroll", onScroll, { passive: true });
    return () => viewport.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div className="flex h-full flex-col bg-card">
      <PlanReviewDrawer
        open={planReviewOpen}
        onOpenChange={setPlanReviewOpen}
        data={planResult}
        onAccept={acceptPlanAndGenerate}
        accepting={acceptingPlan || isStreaming || isLoading}
      />

      {/* Code mutator patch preview */}
      <AlertDialog open={pendingPatchOpen} onOpenChange={setPendingPatchOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Aplicar patch de código?</AlertDialogTitle>
            <AlertDialogDescription>
              O patch será aplicado no VFS e passará por um smoke test (import + extract). Se falhar, rollback automático.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="space-y-2 text-sm">
            <div>
              <span className="font-medium">Ops:</span> {pendingPatch?.ops.length ?? 0}
            </div>
            <div>
              <span className="font-medium">Dirs tocados:</span>{" "}
              {pendingPatchSummary?.touchedDirs?.length ? pendingPatchSummary.touchedDirs.join(", ") : "(nenhum)"}
            </div>
            {pendingPatchSummary?.warnings?.length ? (
              <div className="rounded-md border border-border/50 p-2">
                <div className="font-medium">Avisos</div>
                <ul className="list-disc pl-5">
                  {pendingPatchSummary.warnings.map((w) => (
                    <li key={w}>{w}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={cancelPendingPatch}>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={applyPendingPatch}>Aplicar</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      {/* Header */}
      <div className="h-12 border-b border-border/50 flex items-center justify-between px-4 bg-card/60">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-primary" />
          <span className="font-semibold text-sm">Ordax AI</span>
          <Badge variant="outline" className="border-neon-green/30 bg-neon-green/10 text-neon-green text-[10px] h-5">
            <span className="w-1 h-1 rounded-full bg-neon-green mr-1 animate-pulse"></span>
            Online
          </Badge>
        </div>
        {(isLoading || isStreaming || acceptingPlan || stage !== "idle") && (
          <div className="text-xs text-primary font-mono animate-pulse">
            {stageLabel || "Processando…"}
          </div>
        )}
      </div>

      {/* AI Debug */}
      <div className="border-b border-border/50 bg-muted/10 px-3 py-2">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-7 text-[11px]"
              onClick={() => setShowDebug((v) => !v)}
            >
              {showDebug ? "Ocultar Debug" : "AI Debug"}
            </Button>
            {debugSummary && (
              <div className="flex items-center gap-2 text-[10px] text-muted-foreground font-mono">
                <span>type={debugSummary.gameType}</span>
                <span>entities={debugSummary.entities}</span>
                <span>systems={debugSummary.systems}</span>
              </div>
            )}
            {debugError && (
              <span className="text-[10px] text-destructive font-mono truncate max-w-[220px]">{debugError}</span>
            )}
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-7 text-[11px]"
            onClick={() => {
              const last = lastUserPromptRef.current.trim();
              if (!last) return toast.info("Nenhuma prompt anterior");
              void send(last);
            }}
            disabled={isLoading || isStreaming}
          >
            Retry
          </Button>
        </div>

        {showDebug && (
          <div className="mt-2 grid gap-2">
            <div className="rounded-md border border-border/50 bg-background/10">
              <div className="px-2 py-1 text-[10px] font-mono text-muted-foreground border-b border-border/50">RAW (modelo)</div>
              <ScrollArea className="h-28">
                <pre className="p-2 text-[10px] leading-relaxed whitespace-pre-wrap break-words">{debugRaw || "(vazio)"}</pre>
              </ScrollArea>
            </div>
            <div className="rounded-md border border-border/50 bg-background/10">
              <div className="px-2 py-1 text-[10px] font-mono text-muted-foreground border-b border-border/50">SANITIZED (OrdaxSpec aplicado)</div>
              <ScrollArea className="h-28">
                <pre className="p-2 text-[10px] leading-relaxed whitespace-pre-wrap break-words">{debugSanitized || "(ainda não gerado)"}</pre>
              </ScrollArea>
            </div>

            <div className="rounded-md border border-border/50 bg-background/10">
              <div className="px-2 py-1 text-[10px] font-mono text-muted-foreground border-b border-border/50">LINT/AUTO-FIX (issues + correções aplicadas)</div>
              <ScrollArea className="h-28">
                <pre className="p-2 text-[10px] leading-relaxed whitespace-pre-wrap break-words">{debugFixes || "(nenhuma correção necessária)"}</pre>
              </ScrollArea>
            </div>
          </div>
        )}
      </div>

      {/* Messages */}
      <ScrollArea ref={scrollAreaRef} className="flex-1 p-4">
        {messages.length === 0 && (
          <div className="space-y-4">
            <div className="glass-panel p-4 rounded-lg border border-border/50">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center shrink-0">
                  <Sparkles className="h-4 w-4 text-primary" />
                </div>
                <div className="flex-1">
                  <div className="font-semibold text-sm mb-1">
                    {isEditMode ? "Modo Projeto" : "Olá! Sou o Ordax AI"}
                  </div>
                  <div className="text-xs text-muted-foreground leading-relaxed">
                    {isEditMode
                      ? "Você já tem um jogo. Peça mudanças e melhorias — eu edito o projeto atual."
                      : "Descreva o jogo que você quer criar e eu vou gerar automaticamente."}
                  </div>
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <div className="text-xs font-semibold text-muted-foreground">
                {isEditMode ? "Sugestões rápidas:" : "Exemplos:"}
              </div>

              {(isEditMode
                ? [
                    "Melhore o visual do player (mais detalhado, com feedback de dano e propulsão)",
                    "Adicione uma tela de pause e uma tela de New Game (overlay)",
                    "Deixe o game loop mais claro: objetivos, score e progressão de dificuldade",
                    "Ajuste câmera e UI para ficar mais 'AAA' (HUD, feedback, partículas)",
                  ]
                : examplePrompts
              ).map((prompt, idx) => (
                <button
                  key={idx}
                  onClick={() => setInput(prompt)}
                  className="w-full text-left p-3 rounded-lg glass-panel border border-border/50 hover:border-primary/30 transition-colors text-xs"
                >
                  • {prompt}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-3">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={cn(
                "flex gap-3 animate-fade-in",
                m.role === "user" ? "justify-end" : "justify-start"
              )}
            >
              {m.role === "assistant" && (
                <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center shrink-0">
                  <Sparkles className="h-4 w-4 text-primary" />
                </div>
              )}
              <div
                className={cn(
                  "max-w-[80%] rounded-lg px-4 py-3 text-xs",
                  m.role === "user"
                    ? "bg-primary/20 border border-primary/30 text-foreground"
                    : "glass-panel border border-border/50 text-foreground"
                )}
              >
                <div className="whitespace-pre-wrap leading-relaxed">
                  {m.content}
                </div>
              </div>
              {m.role === "user" && (
                <div className="w-8 h-8 rounded-full bg-surface-2 flex items-center justify-center shrink-0">
                  <span className="text-xs">👤</span>
                </div>
              )}
            </div>
          ))}

          {/* Loading indicator (for cases where streaming has no visible chunks) */}
          {(isLoading || isStreaming) && !streamingContent && (
            <div className="flex gap-3 animate-fade-in">
              <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center shrink-0">
                <Sparkles className="h-4 w-4 text-primary animate-pulse" />
              </div>
              <div className="max-w-[80%] rounded-lg px-4 py-3 text-xs glass-panel border border-border/50 text-foreground">
                <div className="leading-relaxed">
                  {loadingBubbleText}
                  <span className="inline-block w-2 h-4 bg-primary animate-pulse ml-2 align-middle" />
                </div>
              </div>
            </div>
          )}

          {/* Streaming message */}
          {isStreaming && streamingContent && (
            <div className="flex gap-3 animate-fade-in">
              <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center shrink-0">
                <Sparkles className="h-4 w-4 text-primary animate-pulse" />
              </div>
              <div className="max-w-[80%] rounded-lg px-4 py-3 text-xs glass-panel border border-border/50 text-foreground">
                <div className="whitespace-pre-wrap leading-relaxed">
                  {streamingContent}
                  <span className="inline-block w-2 h-4 bg-primary animate-pulse ml-1"></span>
                </div>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Input */}
      <div className="border-t border-border/50 p-4 bg-card/60">
        <div className="flex gap-2">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={placeholder}
            className="min-h-[80px] max-h-[120px] resize-none bg-background border-border/50 text-xs"
            onKeyDown={(e) => {
              if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
                e.preventDefault();
                void send(input);
              }
            }}
          />
          {isStreaming ? (
            <Button
              size="icon"
              variant="destructive"
              className="h-auto shrink-0 self-end"
              onClick={stopStreaming}
            >
              <StopCircle className="h-4 w-4" />
            </Button>
          ) : (
            <Button
              size="icon"
              className="h-auto shrink-0 self-end neon-glow"
              onClick={() => void send(input)}
              disabled={isLoading || !input.trim()}
            >
              <Send className="h-4 w-4" />
            </Button>
          )}
        </div>
        <div className="text-[10px] text-muted-foreground mt-2">
          Pressione Ctrl+Enter para enviar
        </div>
      </div>
    </div>
  );
}
