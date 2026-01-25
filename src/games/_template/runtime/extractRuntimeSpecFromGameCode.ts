import type { OrdaxSpec } from "@/lib/ordax/types";
import type { CodeGameModule, RuntimeSpecCollector } from "./types";

function uniq(list: string[]) {
  return Array.from(new Set(list.filter((s) => typeof s === "string" && s.trim())));
}

export function extractRuntimeSpecFromGameCode(game: CodeGameModule): OrdaxSpec {
  const systems: string[] = [];
  const entities: OrdaxSpec["scene"]["entities"] = [];
  let visual: OrdaxSpec["visual"] | undefined;
  let audio: OrdaxSpec["audio"] | undefined;
  let gravity: OrdaxSpec["scene"]["gravity"] = { x: 0, y: 0 };

  const collector: RuntimeSpecCollector = {
    useSystem: (name) => systems.push(name),
    addEntity: (e) => entities.push(e),
    setVisual: (v) => {
      visual = v;
    },
    setAudio: (a) => {
      audio = a;
    },
    setGravity: (g) => {
      gravity = g;
    },
  };

  // “Extraction mode” contract: run ONLY game.setup({mode:"extract"})
  // and collect registrations. No runtime/RAF/input should execute here.
  game.setup({ mode: "extract", collector });

  return {
    gameType: game.meta.gameType,
    title: game.meta.title,
    description: game.meta.description,
    systems: uniq(systems),
    visual,
    audio,
    scene: {
      gravity,
      entities,
    },
  };
}
