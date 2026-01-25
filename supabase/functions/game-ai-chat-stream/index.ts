import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { CompilerSessionStore } from "../_shared/compiler-session-store.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

// Constitutional Validator Types (inline para Deno)
type ViolationLevel = 'CRITICAL' | 'SEVERE' | 'MINOR';

interface ConstitutionalViolation {
  id: string;
  level: ViolationLevel;
  pilar: string;
  rule: string;
  message: string;
  fix: string;
}

interface ValidationResult {
  isValid: boolean;
  violations: ConstitutionalViolation[];
  summary: {
    critical: number;
    severe: number;
    minor: number;
  };
}

interface RuntimeSpec {
  code: string;
  hasTimeManager?: boolean;
  hasStateManager?: boolean;
  hasInputManager?: boolean;
  hasSaveManager?: boolean;
  hasViewportManager?: boolean;
  hasStartScreen?: boolean;
  hasHUD?: boolean;
  hasGameOverScreen?: boolean;
}

const CANONICAL_ALLOWED_DIRS = new Set(["systems", "entities", "ui", "state", "input", "audio", "spawn", "utils", "_derived"]);
const CANONICAL_ROOT_FILES = new Set(["codeGame.ts"]);

// Constitutional Validation Rules (inline)
const VALIDATION_RULES = [
  {
    id: 'TIME_001',
    level: 'CRITICAL' as ViolationLevel,
    pilar: 'Time Management',
    check: (spec: RuntimeSpec) => {
      const hasUpdateWithDelta = /update\s*\(\s*deltaTime\s*:\s*number\s*\)/.test(spec.code);
      const usesDeltaInMovement = /[+\-*\/]=?\s*.*\s*\*\s*deltaTime/.test(spec.code);
      return hasUpdateWithDelta && usesDeltaInMovement;
    },
    message: 'Game must use deltaTime for frame-independent movement',
    fix: 'Add deltaTime parameter to update() and multiply all movement by deltaTime'
  },
  {
    id: 'FSM_001',
    level: 'CRITICAL' as ViolationLevel,
    pilar: 'FSM',
    check: (spec: RuntimeSpec) => {
      const hasEnum = /enum\s+GameState\s*{/.test(spec.code);
      const hasStart = /START\s*=/.test(spec.code);
      const hasPlaying = /PLAYING\s*=/.test(spec.code);
      const hasPaused = /PAUSED\s*=/.test(spec.code);
      const hasGameOver = /GAME_OVER\s*=/.test(spec.code);
      return hasEnum && hasStart && hasPlaying && hasPaused && hasGameOver;
    },
    message: 'GameState enum must exist with START, PLAYING, PAUSED, GAME_OVER',
    fix: 'Add GameState enum with all required states'
  },
  {
    id: 'FSM_002',
    level: 'CRITICAL' as ViolationLevel,
    pilar: 'FSM',
    check: (spec: RuntimeSpec) => spec.hasStateManager === true || /currentState/.test(spec.code),
    message: 'StateManager is required for game state management',
    fix: 'Add StateManager to core systems'
  },
  {
    id: 'UI_001',
    level: 'CRITICAL' as ViolationLevel,
    pilar: 'UI System',
    check: (spec: RuntimeSpec) => spec.hasStartScreen === true || /StartScreen|renderStartScreen/.test(spec.code),
    message: 'StartScreen is required for game initialization',
    fix: 'Add StartScreen component with render() and handleClick()'
  },
  {
    id: 'UI_002',
    level: 'CRITICAL' as ViolationLevel,
    pilar: 'UI System',
    check: (spec: RuntimeSpec) => spec.hasGameOverScreen === true || /GameOverScreen|renderGameOverScreen/.test(spec.code),
    message: 'GameOverScreen is required for game completion',
    fix: 'Add GameOverScreen component with score display and restart option'
  },
  {
    id: 'UI_003',
    level: 'SEVERE' as ViolationLevel,
    pilar: 'UI System',
    check: (spec: RuntimeSpec) => spec.hasHUD === true || /HUD|renderHUD/.test(spec.code),
    message: 'HUD is required for displaying game information',
    fix: 'Add HUD component to display score, lives, or other game info'
  },
  {
    id: 'INPUT_001',
    level: 'CRITICAL' as ViolationLevel,
    pilar: 'Input System',
    check: (spec: RuntimeSpec) => spec.hasInputManager === true || /keys\s*[:=].*Map/.test(spec.code),
    message: 'InputManager is required for centralized input handling',
    fix: 'Add InputManager to core systems'
  },
  {
    id: 'INPUT_002',
    level: 'SEVERE' as ViolationLevel,
    pilar: 'Input System',
    check: (spec: RuntimeSpec) => {
      const hasKeyboard = /keydown|keyup/.test(spec.code);
      const hasMouseOrTouch = /mousedown|mouseup|touchstart|touchend|click/.test(spec.code);
      return hasKeyboard && hasMouseOrTouch;
    },
    message: 'InputManager must support at least keyboard and mouse/touch',
    fix: 'Add event listeners for keyboard and mouse/touch'
  },
  {
    id: 'SAVE_001',
    level: 'CRITICAL' as ViolationLevel,
    pilar: 'Save System',
    check: (spec: RuntimeSpec) => spec.hasSaveManager === true || /localStorage/.test(spec.code),
    message: 'SaveManager is required for data persistence',
    fix: 'Add SaveManager to core systems'
  },
  {
    id: 'SAVE_002',
    level: 'CRITICAL' as ViolationLevel,
    pilar: 'Save System',
    check: (spec: RuntimeSpec) => {
      const hasSave = /localStorage\.setItem/.test(spec.code) || /saveHighScore/.test(spec.code);
      const hasLoad = /localStorage\.getItem/.test(spec.code) || /loadHighScore/.test(spec.code);
      return hasSave && hasLoad;
    },
    message: 'HighScore must be persisted using localStorage',
    fix: 'Add saveHighScore() and loadHighScore() methods'
  },
  {
    id: 'VIEWPORT_001',
    level: 'CRITICAL' as ViolationLevel,
    pilar: 'Viewport Management',
    check: (spec: RuntimeSpec) => /addEventListener\s*\(\s*['"]resize['"]/.test(spec.code) || /handleResize/.test(spec.code),
    message: 'Resize handler is required for responsive canvas',
    fix: 'Add window resize event listener'
  },
  {
    id: 'LOOP_001',
    level: 'CRITICAL' as ViolationLevel,
    pilar: 'Game Loop',
    check: (spec: RuntimeSpec) => /requestAnimationFrame/.test(spec.code),
    message: 'Game loop must use requestAnimationFrame',
    fix: 'Replace setInterval/setTimeout with requestAnimationFrame'
  },
  {
    id: 'LOOP_002',
    level: 'CRITICAL' as ViolationLevel,
    pilar: 'Game Loop',
    check: (spec: RuntimeSpec) => {
      const hasUpdate = /function\s+update\s*\(|update\s*\(.*\)\s*{|update\s*:\s*\(/.test(spec.code);
      const hasRender = /function\s+render\s*\(|render\s*\(.*\)\s*{|render\s*:\s*\(/.test(spec.code);
      return hasUpdate && hasRender;
    },
    message: 'Game loop must separate update() and render() logic',
    fix: 'Create separate update() and render() functions'
  }
];

function validateConstitutionalCompliance(spec: RuntimeSpec): ValidationResult {
  const violations: ConstitutionalViolation[] = [];

  for (const rule of VALIDATION_RULES) {
    try {
      if (!rule.check(spec)) {
        violations.push({
          id: rule.id,
          level: rule.level,
          pilar: rule.pilar,
          rule: '',
          message: rule.message,
          fix: rule.fix
        });
      }
    } catch (error) {
      console.error(`Error checking rule ${rule.id}:`, error);
    }
  }

  const summary = {
    critical: violations.filter(v => v.level === 'CRITICAL').length,
    severe: violations.filter(v => v.level === 'SEVERE').length,
    minor: violations.filter(v => v.level === 'MINOR').length
  };

  return {
    isValid: summary.critical === 0,
    violations,
    summary
  };
}

const CANONICAL_ALLOWED_DIRS = new Set(["systems", "entities", "ui", "state", "input", "audio", "spawn", "utils", "_derived"]);
const CANONICAL_ROOT_FILES = new Set(["codeGame.ts"]);

function normalizePath(p: string) {
  const t = (p ?? "").trim();
  if (!t.startsWith("/")) return `/${t}`;
  return t;
}

function validateCodeSemanticPatchOrThrow(patch: any, targetGameId: string) {
  if (!patch || patch.kind !== "CODE_SEMANTIC_PATCH") throw new Error("Patch inválido: kind");
  if (patch.version !== "1") throw new Error(`Patch inválido: version=${String(patch.version)}`);
  if (patch.gameId !== targetGameId) throw new Error(`Patch inválido: gameId=${String(patch.gameId)} (esperado ${targetGameId})`);
  if (!Array.isArray(patch.ops)) throw new Error("Patch inválido: ops");

  const prefix = `/vfs/games/${targetGameId}/`;
  const touchedCanonicalDirs = new Set<string>();
  const codeGamePath = `${prefix}codeGame.ts`;
  let hasCodeGameUpdate = false;

  for (const op of patch.ops) {
    const opType = op?.op;
    if (typeof opType !== "string") throw new Error("Op inválida: sem campo op");

    const path = opType === "rename_file" ? op?.to : op?.path;
    const from = opType === "rename_file" ? op?.from : undefined;
    const pathsToCheck = [path, from].filter((x) => typeof x === "string") as string[];

    for (const raw of pathsToCheck) {
      const abs = normalizePath(raw);
      if (!abs.startsWith(prefix)) throw new Error(`Path fora do escopo permitido: ${abs}`);
      if (abs.includes("..")) throw new Error(`Path inválido (..): ${abs}`);

      const rel = abs.slice(prefix.length);
      const seg = rel.split("/").filter(Boolean);
      if (seg.length === 0) throw new Error(`Path inválido (raiz): ${abs}`);
      if (seg.length === 1) {
        if (!CANONICAL_ROOT_FILES.has(seg[0])) throw new Error(`Arquivo na raiz não permitido: ${abs}`);
      } else {
        if (!CANONICAL_ALLOWED_DIRS.has(seg[0])) throw new Error(`Diretório não permitido: ${abs}`);
        if (["systems", "entities", "ui", "state", "input", "audio", "spawn"].includes(seg[0])) touchedCanonicalDirs.add(seg[0]);
      }

      if (opType === "delete_file" && abs === codeGamePath) throw new Error("Não é permitido deletar codeGame.ts");
    }

    if (opType === "update_file" && normalizePath(op?.path) === codeGamePath) {
      hasCodeGameUpdate = true;
    }
  }

  if (touchedCanonicalDirs.size && !hasCodeGameUpdate) {
    throw new Error(
      `Patch incompleto: alterou/criou em [${Array.from(touchedCanonicalDirs).join(", ")}] mas não incluiu update_file em ${codeGamePath} (registro obrigatório).`
    );
  }
}

function toSseFromFullText(fullText: string) {
  // StreamingClient expects OpenAI-style SSE with choices[0].delta.content.
  const payload = JSON.stringify({ choices: [{ delta: { content: fullText } }] });
  return `data: ${payload}\n\n` + `data: [DONE]\n\n`;
}

type OrdaxGameType = "platformer" | "topdown" | "shooter" | "puzzle" | "racing" | "sports" | "unknown";

type GamePlan = {
  kind: "GAME_PLAN";
  gameType: OrdaxGameType;
  title: string;
  description: string;
  coreLoop: string;
  requiredSystems: string[];
  requiredEntities: string[];
  loopType: "winlose" | "survival" | "objective";
  lifecycle: {
    requiredStates: ("start" | "playing" | "gameover")[];
    requiredTransitions: ("start->playing" | "playing->gameover" | "gameover->restart")[];
    requiredUI: ("hud" | "gameover_screen")[];
    requiredSignalsAnyOf: ("player_health" | "objective_progress" | "timer")[];
    signal: "player_health" | "objective_progress" | "timer";
    requiredControls: ("start_game" | "restart_game")[];
    startCondition: string;
    loseCondition: string;
    winCondition?: string;
    scoreRule: string;
  };
  mustHave: {
    hasEnemies: boolean;
    hasAI: boolean;
    hasScore: boolean;
    hasHUD: boolean;
    hasSpawner: boolean;
  };
};

type PlanDiff = {
  autoAddedSystems: string[];
  autoAddedEntities: string[];
  coreLoopAutoGenerated: boolean;
  loopTypeAutoFixed: boolean;
  lifecycle: {
    autoAddedStates: string[];
    autoAddedTransitions: string[];
    autoAddedUI: string[];
    autoAddedControls: string[];
    requiredSignalsAnyOfAutoAdded: boolean;
    signalAutoChosen: boolean;
    startConditionAutoAdded: boolean;
    loseConditionAutoAdded: boolean;
    winConditionAutoAdded: boolean;
    scoreRuleAutoAdded: boolean;
  };
};

const ORDAX_ALLOWED_SYSTEMS = [
  "PhysicsSystem",
  "CollisionSystem",
  "ParticleSystem",
  "AnimationSystem",
  "AudioSystem",
  "CameraSystem",
  "AISystem",
  "SpawnerSystem",
  "ScoreSystem",
  "UISystem",
  "TimerSystem",
  "DialogueSystem",
  "InventorySystem",
  "SaveSystem",
] as const;

const ALLOWED_SYSTEM_SET = new Set<string>(ORDAX_ALLOWED_SYSTEMS);

function uniq(list: string[]) {
  const out: string[] = [];
  const seen = new Set<string>();
  for (const s of list) {
    if (!s || seen.has(s)) continue;
    seen.add(s);
    out.push(s);
  }
  return out;
}

function containsAny(haystack: string, needles: string[]) {
  const t = (haystack || "").toLowerCase();
  return needles.some((n) => t.includes(n));
}

function requiredSystemsForGenre(gameType: OrdaxGameType): string[] {
  const base = ["CameraSystem", "UISystem"];
  switch (gameType) {
    case "puzzle":
      return [...base, "ScoreSystem", "TimerSystem"];
    case "racing":
    case "sports":
      return [...base, "PhysicsSystem", "CollisionSystem", "TimerSystem", "ScoreSystem"];
    case "platformer":
      return [...base, "PhysicsSystem", "CollisionSystem", "ScoreSystem"];
    case "topdown":
      return [...base, "PhysicsSystem", "CollisionSystem", "AISystem", "SpawnerSystem", "ScoreSystem", "TimerSystem"];
    case "shooter":
      return [...base, "PhysicsSystem", "CollisionSystem", "AISystem", "SpawnerSystem", "ScoreSystem", "TimerSystem"];
    default:
      return [...base, "PhysicsSystem", "CollisionSystem", "ScoreSystem", "TimerSystem", "AISystem", "SpawnerSystem"];
  }
}

function requiredEntitiesForGenre(gameType: OrdaxGameType): string[] {
  const base = ["player"];
  switch (gameType) {
    case "platformer":
      return [...base, "spawner", "enemy", "pickup"];
    case "shooter":
      return [...base, "spawner", "enemy", "pickup"];
    case "topdown":
      return [...base, "spawner", "enemy", "pickup"];
    case "puzzle":
      return [...base, "pickup"];
    case "racing":
    case "sports":
      return [...base, "pickup"];
    default:
      return [...base, "spawner", "enemy", "pickup"];
  }
}

function sanitizeEntities(entities: unknown): string[] {
  const list = Array.isArray(entities) ? entities.filter((e) => typeof e === "string") : [];
  const allowed = new Set(["player", "spawner", "enemy", "pickup", "goal"]);
  return uniq(list.map((s) => s.trim().toLowerCase()).filter((s) => allowed.has(s)));
}

function detectLoopType(coreLoop: string): GamePlan["loopType"] {
  const t = (coreLoop || "").toLowerCase();
  if (containsAny(t, ["sobreviver", "survive", "ondas", "wave", "tempo", "time"])) return "survival";
  if (containsAny(t, ["vencer", "vitória", "vitoria", "derrota", "perder", "ganhar", "win", "lose"])) return "winlose";
  return "objective";
}

function promptRequiredSystems(prompt: string): string[] {
  const systems: string[] = [];
  if (containsAny(prompt, ["diálogo", "dialogo", "npc", "conversa"])) systems.push("DialogueSystem");
  if (containsAny(prompt, ["inventário", "inventario", "loot", "itens", "items"])) systems.push("InventorySystem");
  if (containsAny(prompt, ["salvar", "save", "checkpoint"])) systems.push("SaveSystem");
  if (containsAny(prompt, ["áudio", "audio", "som", "música", "musica", "sfx", "music"])) systems.push("AudioSystem");
  if (containsAny(prompt, ["partícula", "particula", "poeira", "explosão", "explosao", "fx"])) systems.push("ParticleSystem");
  return uniq(systems);
}

function sanitizeSystems(systems: unknown): string[] {
  const list = Array.isArray(systems) ? systems.filter((s) => typeof s === "string") : [];
  return uniq(list.filter((s) => ALLOWED_SYSTEM_SET.has(s)));
}

type LifecycleSignal = "player_health" | "objective_progress" | "timer";
type LifecycleState = "start" | "playing" | "gameover";
type LifecycleTransition = "start->playing" | "playing->gameover" | "gameover->restart";
type LifecycleUI = "hud" | "gameover_screen";
type LifecycleControl = "start_game" | "restart_game";

function pickDefaultSignal(loopType: GamePlan["loopType"], mustHave: GamePlan["mustHave"], requiredEntities: string[]): LifecycleSignal {
  if (mustHave.hasEnemies || requiredEntities.includes("enemy")) return "player_health";
  if (loopType === "objective") return "objective_progress";
  return "timer";
}

function defaultLoseCondition(gameType: OrdaxGameType, signal: LifecycleSignal, loopType: GamePlan["loopType"]): string {
  if (signal === "player_health") return "player_health <= 0";
  if (signal === "timer") return "timer <= 0";
  if (loopType === "objective") return "timer <= 0";
  if (gameType === "puzzle") return "timer <= 0";
  return "timer <= 0";
}

function defaultWinCondition(loopType: GamePlan["loopType"], signal: LifecycleSignal, mustHave: GamePlan["mustHave"]): string | undefined {
  if (loopType === "survival") return undefined;
  if (signal === "objective_progress") return "objective_progress >= 1";
  if (loopType === "winlose" && mustHave.hasScore) return "score >= 10";
  return undefined;
}

function defaultScoreRule(gameType: OrdaxGameType, loopType: GamePlan["loopType"], mustHave: GamePlan["mustHave"]): string {
  if (!mustHave.hasScore) return "score opcional";
  switch (gameType) {
    case "platformer":
      return loopType === "survival" ? "score = tempo sobrevivido + moedas" : "score = moedas + objetivos";
    case "shooter":
      return loopType === "survival" ? "score = kills + tempo" : "score = kills + objetivos";
    case "topdown":
      return loopType === "survival" ? "score = kills + tempo" : "score = objetivos + pickups";
    case "racing":
      return "score = checkpoints/laps (tempo menor é melhor)";
    case "sports":
      return "score = pontos da partida";
    case "puzzle":
      return "score = objetivo concluído (tempo menor é melhor)";
    default:
      return "score = objetivos + tempo";
  }
}

function normalizeLifecycle(input: unknown) {
  const p = (input ?? {}) as any;
  const allowedStates = new Set<LifecycleState>(["start", "playing", "gameover"]);
  const allowedTransitions = new Set<LifecycleTransition>(["start->playing", "playing->gameover", "gameover->restart"]);
  const allowedUI = new Set<LifecycleUI>(["hud", "gameover_screen"]);
  const allowedControls = new Set<LifecycleControl>(["start_game", "restart_game"]);
  const allowedSignals = new Set<LifecycleSignal>(["player_health", "objective_progress", "timer"]);

  const states = Array.isArray(p.requiredStates)
    ? (p.requiredStates as unknown[]).filter((s): s is LifecycleState => typeof s === "string" && allowedStates.has(s as any))
    : [];
  const transitions = Array.isArray(p.requiredTransitions)
    ? (p.requiredTransitions as unknown[]).filter((t): t is LifecycleTransition => typeof t === "string" && allowedTransitions.has(t as any))
    : [];
  const ui = Array.isArray(p.requiredUI)
    ? (p.requiredUI as unknown[]).filter((u): u is LifecycleUI => typeof u === "string" && allowedUI.has(u as any))
    : [];
  const controls = Array.isArray(p.requiredControls)
    ? (p.requiredControls as unknown[]).filter((c): c is LifecycleControl => typeof c === "string" && allowedControls.has(c as any))
    : [];
  const anyOf = Array.isArray(p.requiredSignalsAnyOf)
    ? (p.requiredSignalsAnyOf as unknown[]).filter((s): s is LifecycleSignal => typeof s === "string" && allowedSignals.has(s as any))
    : [];

  const signal = typeof p.signal === "string" && allowedSignals.has(p.signal as any) ? (p.signal as LifecycleSignal) : undefined;
  const startCondition = typeof p.startCondition === "string" && p.startCondition.trim() ? p.startCondition.trim() : undefined;
  const loseCondition = typeof p.loseCondition === "string" && p.loseCondition.trim() ? p.loseCondition.trim() : undefined;
  const winCondition = typeof p.winCondition === "string" && p.winCondition.trim() ? p.winCondition.trim() : undefined;
  const scoreRule = typeof p.scoreRule === "string" && p.scoreRule.trim() ? p.scoreRule.trim() : undefined;

  return {
    states: uniq(states),
    transitions: uniq(transitions),
    ui: uniq(ui),
    controls: uniq(controls),
    requiredSignalsAnyOf: uniq(anyOf),
    signal,
    startCondition,
    loseCondition,
    winCondition,
    scoreRule,
  };
}

function validateAndCompletePlan(
  input: unknown,
  userPrompt: string
): { plan: GamePlan; warnings: string[]; diff: PlanDiff } {
  const warnings: string[] = [];
  const p = (input ?? {}) as Partial<GamePlan>;
  const gameType = (p.gameType ?? "unknown") as OrdaxGameType;
  const genreReq = requiredSystemsForGenre(gameType);
  const promptReq = promptRequiredSystems(userPrompt);

  const genreEntities = requiredEntitiesForGenre(gameType);
  const rawEntities = sanitizeEntities((p as any).requiredEntities);
  let requiredEntities = uniq([...rawEntities, ...genreEntities]);

  const rawSystems = sanitizeSystems(p.requiredSystems);
  let requiredSystems = uniq([...rawSystems, ...genreReq, ...promptReq]);

  for (const s of genreReq) {
    if (!requiredSystems.includes(s)) {
      requiredSystems.push(s);
      warnings.push(`Plano incompleto: adicionado system obrigatório do gênero: ${s}`);
    }
  }
  for (const s of promptReq) {
    if (!requiredSystems.includes(s)) {
      requiredSystems.push(s);
      warnings.push(`Plano incompleto: adicionado system exigido pelo prompt: ${s}`);
    }
  }

  const mustHave = {
    hasHUD: true,
    hasScore: requiredSystems.includes("ScoreSystem"),
    hasSpawner: requiredSystems.includes("SpawnerSystem"),
    hasAI: requiredSystems.includes("AISystem"),
    hasEnemies: gameType === "topdown" || gameType === "shooter" || gameType === "platformer" ? true : false,
  };

  if (mustHave.hasEnemies && !requiredSystems.includes("AISystem")) {
    requiredSystems.push("AISystem");
    warnings.push("Plano incompleto: ação requer AI → AISystem adicionado");
    mustHave.hasAI = true;
  }
  if (mustHave.hasEnemies && !requiredSystems.includes("SpawnerSystem")) {
    requiredSystems.push("SpawnerSystem");
    warnings.push("Plano incompleto: ação requer spawns → SpawnerSystem adicionado");
    mustHave.hasSpawner = true;
  }
  if (mustHave.hasEnemies && !requiredSystems.includes("CollisionSystem")) {
    requiredSystems.push("CollisionSystem");
    warnings.push("Plano incompleto: ação requer colisão → CollisionSystem adicionado");
  }
  if (mustHave.hasEnemies && !requiredSystems.includes("PhysicsSystem")) {
    requiredSystems.push("PhysicsSystem");
    warnings.push("Plano incompleto: ação requer movimento/contato → PhysicsSystem adicionado");
  }
  if (!requiredSystems.includes("ScoreSystem")) {
    requiredSystems.push("ScoreSystem");
    warnings.push("Plano incompleto: loop exige score → ScoreSystem adicionado");
    mustHave.hasScore = true;
  }
  if (!requiredSystems.includes("TimerSystem")) {
    requiredSystems.push("TimerSystem");
    warnings.push("Plano incompleto: loop exige timer → TimerSystem adicionado");
  }

  for (const e of genreEntities) {
    if (!requiredEntities.includes(e)) {
      requiredEntities.push(e);
      warnings.push(`Plano incompleto: adicionado entity obrigatório do gênero: ${e}`);
    }
  }

  requiredSystems = uniq(requiredSystems.filter((s) => ALLOWED_SYSTEM_SET.has(s)));
  requiredEntities = uniq(requiredEntities);

  const title = typeof p.title === "string" && p.title.trim() ? p.title.trim() : "Jogo";
  const description = typeof p.description === "string" ? p.description : "";

  const coreLoopAutoGenerated = !(typeof p.coreLoop === "string" && p.coreLoop.trim());
  const coreLoop = coreLoopAutoGenerated
    ? (mustHave.hasEnemies
        ? "Sobreviver o máximo possível: derrotar inimigos, ganhar pontos, evitar dano."
        : "Vencer ao completar objetivos e ganhar pontos antes do tempo acabar.")
    : p.coreLoop!.trim();

  const detected = detectLoopType(coreLoop);
  let loopType: GamePlan["loopType"] = typeof (p as any).loopType === "string" ? ((p as any).loopType as any) : detected;
  let loopTypeAutoFixed = false;
  if (mustHave.hasEnemies) {
    if (loopType !== "survival" && loopType !== "winlose") {
      loopType = "survival";
      loopTypeAutoFixed = true;
      warnings.push("Plano incompleto: ação exige loop survival/winlose → loopType=survival");
    }
  } else {
    if (loopType !== "objective" && loopType !== "winlose") {
      loopType = "objective";
      loopTypeAutoFixed = true;
      warnings.push("Plano incompleto: loop básico ajustado → loopType=objective");
    }
  }

  // =====================
  // Constitutional lifecycle validation/auto-complete
  // =====================
  const rawLifecycle = normalizeLifecycle((p as any).lifecycle);
  const baseStates: LifecycleState[] = ["start", "playing", "gameover"];
  const baseTransitions: LifecycleTransition[] = ["start->playing", "playing->gameover", "gameover->restart"];
  const baseUI: LifecycleUI[] = ["hud", "gameover_screen"];
  const baseControls: LifecycleControl[] = ["start_game", "restart_game"];
  const baseSignalsAnyOf: LifecycleSignal[] = ["player_health", "objective_progress", "timer"];

  const states = uniq([...(rawLifecycle.states as string[]), ...baseStates]) as LifecycleState[];
  const transitions = uniq([...(rawLifecycle.transitions as string[]), ...baseTransitions]) as LifecycleTransition[];
  const ui = uniq([...(rawLifecycle.ui as string[]), ...baseUI]) as LifecycleUI[];
  const controls = uniq([...(rawLifecycle.controls as string[]), ...baseControls]) as LifecycleControl[];
  const requiredSignalsAnyOf = uniq([...(rawLifecycle.requiredSignalsAnyOf as string[]), ...baseSignalsAnyOf]) as LifecycleSignal[];

  const computedSignal = rawLifecycle.signal ?? pickDefaultSignal(loopType, mustHave, requiredEntities);
  if (!rawLifecycle.signal) warnings.push(`Lifecycle: sinal mínimo ausente → signal=${computedSignal} (auto)`);

  const startCondition = rawLifecycle.startCondition ?? "on start_game";
  if (!rawLifecycle.startCondition) warnings.push("Lifecycle: startCondition ausente → 'on start_game' (auto)");

  const loseCondition = rawLifecycle.loseCondition ?? defaultLoseCondition(gameType, computedSignal, loopType);
  if (!rawLifecycle.loseCondition) warnings.push(`Lifecycle: loseCondition ausente → '${loseCondition}' (auto)`);

  const winCondition = rawLifecycle.winCondition ?? defaultWinCondition(loopType, computedSignal, mustHave);
  if (!rawLifecycle.winCondition && winCondition) warnings.push(`Lifecycle: winCondition ausente → '${winCondition}' (auto)`);

  const scoreRule = rawLifecycle.scoreRule ?? defaultScoreRule(gameType, loopType, mustHave);
  if (!rawLifecycle.scoreRule) warnings.push(`Lifecycle: scoreRule ausente → '${scoreRule}' (auto)`);

  if (computedSignal === "timer" && !requiredSystems.includes("TimerSystem")) {
    requiredSystems.push("TimerSystem");
    warnings.push("Lifecycle: signal=timer exige TimerSystem → TimerSystem adicionado");
  }

  if (requiredEntities.includes("enemy")) {
    if (!requiredSystems.includes("AISystem")) {
      requiredSystems.push("AISystem");
      warnings.push("Plano incompleto: enemy exige AI → AISystem adicionado");
      mustHave.hasAI = true;
    }
    if (!requiredSystems.includes("SpawnerSystem")) {
      requiredSystems.push("SpawnerSystem");
      warnings.push("Plano incompleto: enemy exige spawner → SpawnerSystem adicionado");
      mustHave.hasSpawner = true;
    }
  }

  requiredSystems = uniq(requiredSystems.filter((s) => ALLOWED_SYSTEM_SET.has(s)));

  return {
    plan: {
      kind: "GAME_PLAN",
      gameType,
      title,
      description,
      coreLoop,
      requiredSystems,
      requiredEntities,
      loopType,
      lifecycle: {
        requiredStates: states,
        requiredTransitions: transitions,
        requiredUI: ui,
        requiredSignalsAnyOf,
        signal: computedSignal,
        requiredControls: controls,
        startCondition,
        loseCondition,
        ...(winCondition ? { winCondition } : {}),
        scoreRule,
      },
      mustHave,
    },
    warnings: uniq(warnings),
    diff: {
      autoAddedSystems: uniq(requiredSystems.filter((s) => !rawSystems.includes(s))),
      autoAddedEntities: uniq(requiredEntities.filter((e) => !rawEntities.includes(e))),
      coreLoopAutoGenerated,
      loopTypeAutoFixed,
      lifecycle: {
        autoAddedStates: uniq(states.filter((s) => !(rawLifecycle.states as string[]).includes(s))),
        autoAddedTransitions: uniq(transitions.filter((t) => !(rawLifecycle.transitions as string[]).includes(t))),
        autoAddedUI: uniq(ui.filter((u) => !(rawLifecycle.ui as string[]).includes(u))),
        autoAddedControls: uniq(controls.filter((c) => !(rawLifecycle.controls as string[]).includes(c))),
        requiredSignalsAnyOfAutoAdded: (rawLifecycle.requiredSignalsAnyOf?.length ?? 0) === 0,
        signalAutoChosen: !rawLifecycle.signal,
        startConditionAutoAdded: !rawLifecycle.startCondition,
        loseConditionAutoAdded: !rawLifecycle.loseCondition,
        winConditionAutoAdded: !rawLifecycle.winCondition && !!winCondition,
        scoreRuleAutoAdded: !rawLifecycle.scoreRule,
      },
    },
  };
}

serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: corsHeaders });

  try {
    const { messages, currentSpec, phase, approvedPlan, approvedPlanHuman, mode, targetGameId, projectFiles, userId, sessionId } = await req.json();

    const LOVABLE_API_KEY = Deno.env.get("LOVABLE_API_KEY");
    if (!LOVABLE_API_KEY) throw new Error("LOVABLE_API_KEY is not configured");

    const SUPABASE_URL = Deno.env.get("SUPABASE_URL");
    const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
    if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) {
      throw new Error("Supabase credentials not configured");
    }

    // ============================================================================
    // COMPILER PROTOCOL VALIDATION (CRÍTICO)
    // ============================================================================
    
    const resolvedMode = (mode ?? "spec") as "spec" | "code_patch";
    const isNewGame = resolvedMode === "spec" && !currentSpec;

    // Se for NEW_GAME, validar protocolo do compilador
    if (isNewGame && sessionId) {
      const sessionStore = new CompilerSessionStore(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);
      const session = await sessionStore.loadSession(sessionId);

      if (!session) {
        // Sessão não encontrada - bloquear streaming
        const encoder = new TextEncoder();
        const stream = new ReadableStream({
          start(controller) {
            const error = JSON.stringify({
              error: "COMPILER_PROTOCOL_VIOLATION",
              message: "Session not found. Cannot stream without valid compiler session.",
              protocol: "ORDAX_COMPILER_PROTOCOL_V1"
            });
            controller.enqueue(encoder.encode(error));
            controller.close();
          }
        });

        return new Response(stream, {
          headers: {
            ...corsHeaders,
            "Content-Type": "text/plain; charset=utf-8",
          },
        });
      }

      // Validar fase e aprovação
      if (session.phase !== "compilation" || !session.approvedByUser) {
        // Protocolo violado - bloquear streaming
        const encoder = new TextEncoder();
        const stream = new ReadableStream({
          start(controller) {
            const error = JSON.stringify({
              error: "COMPILER_PROTOCOL_VIOLATION",
              message: `Cannot stream compilation. Current phase: ${session.phase}, Approved: ${session.approvedByUser}. Must be in compilation phase with user approval.`,
              currentPhase: session.phase,
              approvedByUser: session.approvedByUser,
              protocol: "ORDAX_COMPILER_PROTOCOL_V1"
            });
            controller.enqueue(encoder.encode(error));
            controller.close();
          }
        });

        return new Response(stream, {
          headers: {
            ...corsHeaders,
            "Content-Type": "text/plain; charset=utf-8",
          },
        });
      }

      // Protocolo validado - pode continuar com streaming
      console.log(`✅ Compiler protocol validated for session ${sessionId}`);
    }

    // ============================================================================
    // CONTINUAR COM STREAMING NORMAL
    // ============================================================================

    const userPrompt = (messages ?? []).slice().reverse().find((m: any) => m?.role === "user")?.content ?? "";
    let planWarnings: string[] = [];
    let validatedPlan: GamePlan | null = null;
    let planDiff: PlanDiff | null = null;
    if (isNewGame) {
      // This endpoint is only for runtimeSpec streaming; planning is handled by the non-stream endpoint.
      if (phase && phase !== "spec") {
        return new Response(JSON.stringify({ error: "Streaming suporta apenas phase=spec." }), {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }
      if (!approvedPlan) {
        return new Response(JSON.stringify({ error: "GAME_PLAN obrigatório: envie approvedPlan para gerar runtimeSpec (stream)." }), {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }

      const completed = validateAndCompletePlan(approvedPlan, userPrompt);
      validatedPlan = completed.plan;
      planWarnings = uniq([...planWarnings, ...completed.warnings]);
      planDiff = completed.diff;
    }

    if (resolvedMode === "code_patch") {
      if (!targetGameId || typeof targetGameId !== "string") {
        return new Response(JSON.stringify({ error: "targetGameId obrigatório no mode=code_patch" }), {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }
    }

    // Keep streaming output as plain text chunks; the frontend accumulates and parses at the end.
    // IMPORTANT: Keep the same generation rules as the non-streaming endpoint for consistency.
    const baseSpecPrompt = `Você é a IA do Ordax (engine de jogos). Gere APENAS um JSON válido, sem markdown nem cercas de código.

Objetivo: inferir um gameType explícito e devolver uma especificação completa e visual, executável pelo preview.

⚠️ CONTRATO CONSTITUCIONAL ORDAX V1 (OBRIGATÓRIO):
Todo jogo DEVE cumprir os 7 pilares operacionais mínimos:

1. TIME MANAGEMENT: Usar deltaTime em todo movimento/física
2. FSM: GameState enum com START, PLAYING, PAUSED, GAME_OVER
3. UI SYSTEM: StartScreen + HUD + GameOverScreen (obrigatórios)
4. INPUT SYSTEM: InputManager centralizado (keyboard + mouse/touch)
5. SAVE SYSTEM: SaveManager com localStorage para highScore
6. VIEWPORT MANAGEMENT: Resize handler para canvas responsivo
7. GAME LOOP: requestAnimationFrame + separação update()/render()

🚫 PROIBIDO:
- Movimento sem deltaTime (ex: player.x += 5)
- Jogo sem FSM ou estados explícitos
- UI incompleta (faltando StartScreen, HUD ou GameOverScreen)
- Input desorganizado (listeners espalhados)
- Sem persistência (score que desaparece)
- Canvas fixo sem adaptação
- setInterval/setTimeout para game loop

✅ ESTRUTURA MÍNIMA OBRIGATÓRIA:
- enum GameState { START, PLAYING, PAUSED, GAME_OVER }
- InputManager com keys Map e mouse/touch
- SaveManager com saveHighScore() e loadHighScore()
- renderStartScreen(), renderHUD(), renderGameOverScreen()
- gameLoop(timestamp) com deltaTime
- window.addEventListener('resize', handleResize)

Formato de saída (JSON):
{
  "gameType": "platformer"|"topdown"|"shooter"|"puzzle"|"racing"|"sports"|"unknown",
  "title": string,
  "description": string,
  "systems": string[],
  "visual": {
    "theme": {
      "background": "hsl(...)", // cor de fundo base
      "primary": "hsl(...)",    // cor primária para player/UI
      "accent": "hsl(...)",     // cor de destaque (inimigos, etc.)
      "font": "ui-sans-serif, system-ui, sans-serif" // CSS font stack
    },
    "background": {
      "layers": [
        { "type": "starfield"|"gradient"|"nebula"|"solid", "parallax": 0..1, "density": 100-500, "speedY": -5..50 }
      ]
    }
  },
  "scene": {
    "gravity": { "x": 0, "y": 0 },
    "entities": [
      { "id": string, "type": string, "x": number, "y": number, "w": number, "h": number, "props"?: {} }
    ]
  }
}

Regras IMPORTANTES:
- gameType obrigatório (um dos valores listados).
- systems: usar apenas nomes de módulos Ordax que existem no runtime (PhysicsSystem, CollisionSystem, ParticleSystem, AnimationSystem, AudioSystem, CameraSystem, AISystem, ScoreSystem, UISystem, TimerSystem, DialogueSystem, InventorySystem, SaveSystem, SpawnerSystem).
- visual.theme: sempre especificar cores HSL (ex: hsl(200, 80%, 50%)) para background/primary/accent.

REGRAS DE BACKGROUND POR TIPO DE JOGO:
- "shooter" ou "space": usar "starfield" + "nebula" (2 layers) com parallax/density/speedY
- "racing": usar "gradient" com cores de pista (cinza, verde, marrom) - NUNCA starfield
- "platformer": usar "gradient" com cores de céu/terra - NUNCA starfield
- "topdown": usar "solid" ou "gradient" apropriado ao tema - NUNCA starfield
- "puzzle": usar "solid" ou "gradient" suave - NUNCA starfield
- "sports": usar "gradient" apropriado ao esporte - NUNCA starfield

- entities: não inventar assets reais; descrever com props simples (ex: speed, health).

CONTEXTO / EDIÇÃO:
- Se currentSpec existir, sua tarefa é EDITAR o projeto atual: mantenha o máximo possível e altere APENAS o necessário para atender o pedido do usuário.
- Retorne o JSON COMPLETO atualizado.

⚠️ VALIDAÇÃO CONSTITUCIONAL:
Seu código será validado automaticamente. Se falhar, você DEVE corrigir TODAS as violações CRÍTICAS.
NÃO responda "jogo pronto" ou sugira "adicionar depois". Gere TUDO desde o início.`;

    const wrapperHint = `\n\nCONTRATO DE SAÍDA (SEMPRE): retorne um JSON com o seguinte formato (sem markdown):\n{\n  "spec": <OrdaxSpec>,\n  "assistantSummary": string,\n  "appliedEdits": string[],\n  "semanticPatch": { "kind": "SEMANTIC_PATCH", "ops": any[] },\n  "report": {\n    "whatWasRequested": string,\n    "whatWasApplied": string[],\n    "whatCouldNotBeAppliedAndWhy": string[],\n    "engineLimitationsHit": string[]\n  }${isNewGame ? ",\n  \"planWarnings\": string[]" : ""}\n}\n\nRegras do contrato:\n- spec: deve ser o JSON COMPLETO atualizado (não retorne apenas dicas).\n- assistantSummary: 2-5 linhas dizendo exatamente o que foi implementado.\n- appliedEdits: lista curta (3-10) de mudanças concretas (ex: "Player: adicionada prop shield=50").\n- semanticPatch: obrigatório; descreve semanticamente o que mudou (ops devem corresponder ao que você aplicou).\n- report: obrigatório; responda de forma objetiva.\n\nSe você NÃO conseguir aplicar o pedido, retorne um JSON de erro: { "error": "COMPILER_ERROR", "message": "...", "engineLimitationsHit": string[] } (sem spec).\n${isNewGame ? "- planWarnings: copie exatamente o array fornecido em planWarnings (do backend) — não invente novos." : ""}`;

    const codePatchPrompt = `Você é um Code Mutator Agent do Ordax. Gere APENAS um JSON válido (sem markdown) contendo um patch estrutural de código TypeScript.

REGRAS CRÍTICAS:
- Você NUNCA deve retornar runtimeSpec/OrdaxSpec.
- Você NUNCA deve tocar no template canônico.
- Você só pode criar/editar/renomear/deletar arquivos dentro de: /vfs/games/<gameId>/
- Extensões permitidas: .ts, .tsx, .json
- Não use imports para @/lib, @/components, supabase, etc. Apenas @/games/_template é permitido.

MAPA SEMÂNTICO (NÃO INVENTAR DIRETÓRIOS):
- Na raiz: apenas /codeGame.ts
- Diretórios permitidos: systems/, entities/, ui/, state/, input/, audio/, spawn/, utils/, _derived/

PADRÕES CANÔNICOS DE MUTAÇÃO:
- Adicionar sistema => create_file systems/<Foo>System.ts + update_file codeGame.ts registrando collector.useSystem("FooSystem")
- Adicionar entidade => create_file entities/<Thing>.ts + update_file codeGame.ts registrando collector.addEntity(...)
- Adicionar HUD/UI => create_file ui/HUD.tsx + update_file codeGame.ts registrando entidade/ui
- Lifecycle start/play/gameover => create_file state/lifecycle.ts + update_file codeGame.ts para usar no runtime (NUNCA violar o lifecycle)

Se você NÃO conseguir aplicar o pedido com segurança, retorne: { "error": "COMPILER_ERROR", "message": "...", "engineLimitationsHit": string[] }
`.trim();

    const wrapperHintPatch = `\n\nCONTRATO DE SAÍDA (SEMPRE): retorne um JSON com o seguinte formato (sem markdown):\n{\n  "patch": {\n    "kind": "CODE_SEMANTIC_PATCH",\n    "version": "1",\n    "gameId": "${String(targetGameId ?? "")}",\n    "ops": [\n      { "op": "create_file", "path": "/vfs/games/<gameId>/...", "content": "..." },\n      { "op": "update_file", "path": "/vfs/games/<gameId>/...", "content": "..." },\n      { "op": "rename_file", "from": "/vfs/games/<gameId>/a.ts", "to": "/vfs/games/<gameId>/b.ts" },\n      { "op": "delete_file", "path": "/vfs/games/<gameId>/..." }\n    ]\n  },\n  "assistantSummary": string,\n  "appliedEdits": string[],\n  "report": {\n    "whatWasRequested": string,\n    "whatWasApplied": string[],\n    "whatCouldNotBeAppliedAndWhy": string[],\n    "engineLimitationsHit": string[]\n  }\n}\n\nRegras do contrato:\n- patch é obrigatório e deve ser aplicável.\n- Não retorne spec/JSON de runtime.\n- Use paths ABSOLUTOS e sempre dentro de /vfs/games/${String(targetGameId ?? "<gameId>")}/\n`;

   const planContext = validatedPlan
       ? `\n\nGAME_PLAN (validado): ${JSON.stringify(validatedPlan)}\n\nRegras do contrato:\n- O output deve implementar o coreLoop do GAME_PLAN (loopType=${validatedPlan.loopType}).\n- requiredEntities do plano DEVEM existir na scene.entities (player/spawner/enemy/pickup quando aplicável).\n- Se mustHave.hasEnemies=true, inclua inimigos + AI + spawner.\n- Sempre inclua ScoreSystem + UISystem + TimerSystem e UI mínima.\n- Lifecycle constitucional (obrigatório): start → playing → gameover (com restart), HUD + gameover_screen, controles start_game/restart_game, condições start/lose/(opcional) win; signal=${validatedPlan.lifecycle.signal} deve ser visível na HUD.\n- Não gere jogo vazio.\n\nplanWarnings (do backend): ${JSON.stringify(planWarnings)}\n\nPLANO HUMANO (checklist semântico; linguagem natural):\n${typeof approvedPlanHuman === "string" && approvedPlanHuman.trim() ? approvedPlanHuman.trim() : "(não fornecido)"}\n\nRegra: se houver conflito entre o PLANO HUMANO e o GAME_PLAN JSON, siga o GAME_PLAN JSON.`
       : "";

    const entryFile = Array.isArray(projectFiles)
      ? projectFiles.find((f: any) => typeof f?.path === "string" && f.path.endsWith("/codeGame.ts"))
      : null;
    const codeContext = resolvedMode === "code_patch"
      ? `\n\nTARGET_GAME_ID: ${String(targetGameId ?? "")}\n` +
        (entryFile?.content ? `\nCURRENT_CODE (codeGame.ts):\n${String(entryFile.content).slice(0, 12000)}\n` : "") +
        (Array.isArray(projectFiles)
          ? `\nPROJECT_FILES (paths):\n${projectFiles
              .map((f: any) => (typeof f?.path === "string" ? f.path : ""))
              .filter(Boolean)
              .slice(0, 200)
              .join("\n")}`
          : "")
      : "";

    const systemPrompt =
      resolvedMode === "code_patch"
        ? (codePatchPrompt + codeContext + wrapperHintPatch).trim()
        : (baseSpecPrompt + (currentSpec ? "" : planContext) + wrapperHint).trim();

    const response = await fetch("https://ai.gateway.lovable.dev/v1/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${LOVABLE_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "google/gemini-3-flash-preview",
        messages: [
          { role: "system", content: systemPrompt },
          ...(resolvedMode === "spec" && currentSpec
            ? [{ role: "system", content: `currentSpec (JSON): ${JSON.stringify(currentSpec)}` }]
            : []),
          ...(messages ?? []),
        ],
        temperature: 0.2,
        // For code_patch we intentionally disable gateway streaming so we can validate server-side.
        stream: resolvedMode === "code_patch" ? false : true,
      }),
    });

    if (!response.ok) {
      if (response.status === 429) {
        return new Response(JSON.stringify({ error: "Rate limits exceeded, please try again later." }), {
          status: 429,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }
      if (response.status === 402) {
        return new Response(JSON.stringify({ error: "Payment required, please add credits to your Lovable AI workspace." }), {
          status: 402,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }

      const t = await response.text();
      console.error("AI gateway error:", response.status, t);
      return new Response(JSON.stringify({ error: "AI gateway error" }), {
        status: 500,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    // code_patch: validate on server and return as SSE (single chunk) for client compatibility.
    if (resolvedMode === "code_patch") {
      const gatewayPayload = (await response.json()) as any;
      const text = gatewayPayload?.choices?.[0]?.message?.content as string | undefined;
      const cleaned = (text ?? "").replace(/^```[a-zA-Z]*\n?/, "").replace(/\n?```$/, "").trim();

      let outText = cleaned;
      try {
        const parsed = JSON.parse(cleaned);
        if (!parsed?.error) {
          validateCodeSemanticPatchOrThrow(parsed?.patch, String(targetGameId ?? ""));
        }
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        outText = JSON.stringify({
          error: "COMPILER_ERROR",
          message: `Patch rejeitado pelo backend: ${msg}`,
          engineLimitationsHit: ["mutation_guide_violation"],
        });
      }

      return new Response(toSseFromFullText(outText), {
        headers: { ...corsHeaders, "Content-Type": "text/event-stream" },
      });
    }

    // spec: pass-through streaming SSE response.
    return new Response(response.body, {
      headers: { ...corsHeaders, "Content-Type": "text/event-stream" },
    });
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    return new Response(JSON.stringify({ error: msg }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
