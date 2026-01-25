import type { OrdaxSpec } from "@/lib/ordax/types";

/**
 * Canonical template contract version.
 *
 * IMPORTANT: bump only when introducing breaking changes to the public API in `_template`.
 */
export const CODE_GAME_TEMPLATE_CONTRACT_VERSION = "1" as const;

export type GamePhase = "start" | "play" | "gameover";

export type GameTemplateMeta = {
  id: string;
  title: string;
  description: string;
  gameType: OrdaxSpec["gameType"];
};

/**
 * Collector: games register systems/entities here; used both for debug and to project Ordax runtimeSpec.
 * This is intentionally a *narrow* contract so the code remains the source of truth.
 */
export type RuntimeSpecCollector = {
  useSystem: (systemName: string) => void;
  addEntity: (e: OrdaxSpec["scene"]["entities"][number]) => void;
  setVisual: (visual: OrdaxSpec["visual"]) => void;
  setAudio: (audio: OrdaxSpec["audio"]) => void;
  setGravity: (g: OrdaxSpec["scene"]["gravity"]) => void;
};

export type GameTemplateContext = {
  /**
   * - "extract": must be pure/deterministic. No RAF, timers, listeners, network, audio, storage.
   * - "run": normal gameplay runtime.
   */
  mode: "run" | "extract";
  collector?: RuntimeSpecCollector;
};

export type CodeGameModule = {
  /** Stable metadata used by the game library + runtimeSpec projection. */
  meta: GameTemplateMeta;
  /**
   * Public entry point.
   *
   * In extract mode, MUST only register via collector and return (no side-effects).
   * In run mode, may mount input/RAF/render etc.
   */
  setup: (ctx: GameTemplateContext) => void;

  /** Reserved for future lifecycle standardization (optional, stable shape). */
  hooks?: {
    onMount?: (ctx: GameTemplateContext) => void;
    onUnmount?: (ctx: GameTemplateContext) => void;
  };
};
