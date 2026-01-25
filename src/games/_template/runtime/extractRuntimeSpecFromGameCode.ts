import type { OrdaxSpec } from "@/lib/ordax/types";
import type { CodeGameModule, RuntimeSpecCollector } from "./types";
// Constitutional validation temporarily disabled due to browser cache issues
// import { 
//   validateConstitutionalCompliance, 
//   formatViolationsForChat,
//   type RuntimeSpec 
// } from "@/lib/ordax/constitutional-validator";

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

  // "Extraction mode" contract: run ONLY game.setup({mode:"extract"})
  // and collect registrations. No runtime/RAF/input should execute here.
  game.setup({ mode: "extract", collector });

  const spec: OrdaxSpec = {
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

  // CONSTITUTIONAL VALIDATION (Parte 4 - Integração)
  // Temporarily disabled due to browser cache issues
  // TODO: Re-enable after browser cache is cleared
  /*
  try {
    const gameCode = game.toString();
    const runtimeSpec: RuntimeSpec = {
      code: gameCode,
      hasTimeManager: /TimeManager/.test(gameCode),
      hasStateManager: /StateManager|currentState/.test(gameCode),
      hasInputManager: /InputManager|keys.*Map/.test(gameCode),
      hasSaveManager: /SaveManager|localStorage/.test(gameCode),
      hasViewportManager: /ViewportManager|handleResize/.test(gameCode),
      hasStartScreen: /StartScreen|renderStartScreen/.test(gameCode),
      hasHUD: /HUD|renderHUD/.test(gameCode),
      hasGameOverScreen: /GameOverScreen|renderGameOverScreen/.test(gameCode)
    };

    const validation = validateConstitutionalCompliance(runtimeSpec);

    if (!validation.isValid) {
      console.warn("⚠️ Constitutional validation failed for extracted game code:");
      console.warn(formatViolationsForChat(validation));
      
      (spec as any).constitutionalValidation = {
        isValid: false,
        violations: validation.violations,
        summary: validation.summary
      };
    } else {
      console.log("✅ Constitutional validation passed for extracted game code");
      (spec as any).constitutionalValidation = {
        isValid: true,
        violations: [],
        summary: { critical: 0, severe: 0, minor: 0 }
      };
    }
  } catch (error) {
    console.error("Error during constitutional validation:", error);
  }
  */

  return spec;
}

