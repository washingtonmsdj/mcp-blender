import type { OrdaxSpec } from "@/lib/ordax/types";

export type GameId = string;

export type GameDefinition = {
  id: GameId;
  title: string;
  tagline: string;
  description: string;
  /** Build a runnable Ordax spec (runtimeSpec) */
  buildSpec: () => OrdaxSpec;
  /** Optional: standalone in-app runner (HTML5 Canvas) */
  play?: {
    kind: "standalone";
    route: string;
  };
  /** Optional: relative path to the doc in repo (non-served), for humans */
  docPath?: string;
};
