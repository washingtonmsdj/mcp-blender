import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { CompilerSessionStore, type CompilerSessionState } from "../_shared/compiler-session-store.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

// ============================================================================
// COMPILER SESSION STATE (Parte 1 - Máquina de Estados com Persistência)
// ============================================================================

function getSessionId(messages: any[], userId?: string): string {
  // Gera ID baseado no userId + primeiras mensagens
  const msgHash = JSON.stringify(messages.slice(0, 2));
  return `${userId || "anon"}_${btoa(msgHash).slice(0, 32)}`;
}

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

type ChatMessage = { role: "user" | "assistant"; content: string };

type Mode = "spec" | "coach" | "code_patch";

// Constitutional Validation Rules
const VALIDATION_RULES = [
  // PILAR 1: Time Management
  {
    id: 'TIME_001',
    level: 'CRITICAL' as ViolationLevel,
    pilar: 'Time Management',
    rule: 'deltaTime must be used in all movement/physics updates',
    check: (spec: RuntimeSpec) => {
      const hasUpdateWithDelta = /update\s*\(\s*deltaTime\s*:\s*number\s*\)/.test(spec.code);
      const usesDeltaInMovement = /[+\-*\/]=?\s*.*\s*\*\s*deltaTime/.test(spec.code);
      return hasUpdateWithDelta && usesDeltaInMovement;
    },
    message: 'Game must use deltaTime for frame-independent movement',
    fix: 'Add deltaTime parameter to update() and multiply all movement by deltaTime'
  },
  // PILAR 2: FSM
  {
    id: 'FSM_001',
    level: 'CRITICAL' as ViolationLevel,
    pilar: 'FSM',
    rule: 'GameState enum must exist with minimum 4 states',
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
    rule: 'StateManager must exist',
    check: (spec: RuntimeSpec) => spec.hasStateManager === true || /currentState/.test(spec.code),
    message: 'StateManager is required for game state management',
    fix: 'Add StateManager to core systems'
  },
  // PILAR 3: UI System
  {
    id: 'UI_001',
    level: 'CRITICAL' as ViolationLevel,
    pilar: 'UI System',
    rule: 'StartScreen must exist',
    check: (spec: RuntimeSpec) => spec.hasStartScreen === true || /StartScreen|renderStartScreen/.test(spec.code),
    message: 'StartScreen is required for game initialization',
    fix: 'Add StartScreen component with render() and handleClick()'
  },
  {
    id: 'UI_002',
    level: 'CRITICAL' as ViolationLevel,
    pilar: 'UI System',
    rule: 'GameOverScreen must exist',
    check: (spec: RuntimeSpec) => spec.hasGameOverScreen === true || /GameOverScreen|renderGameOverScreen/.test(spec.code),
    message: 'GameOverScreen is required for game completion',
    fix: 'Add GameOverScreen component with score display and restart option'
  },
  {
    id: 'UI_003',
    level: 'SEVERE' as ViolationLevel,
    pilar: 'UI System',
    rule: 'HUD must exist',
    check: (spec: RuntimeSpec) => spec.hasHUD === true || /HUD|renderHUD/.test(spec.code),
    message: 'HUD is required for displaying game information',
    fix: 'Add HUD component to display score, lives, or other game info'
  },
  // PILAR 4: Input System
  {
    id: 'INPUT_001',
    level: 'CRITICAL' as ViolationLevel,
    pilar: 'Input System',
    rule: 'InputManager must exist',
    check: (spec: RuntimeSpec) => spec.hasInputManager === true || /keys\s*[:=].*Map/.test(spec.code),
    message: 'InputManager is required for centralized input handling',
    fix: 'Add InputManager to core systems'
  },
  {
    id: 'INPUT_002',
    level: 'SEVERE' as ViolationLevel,
    pilar: 'Input System',
    rule: 'InputManager must support keyboard and mouse/touch',
    check: (spec: RuntimeSpec) => {
      const hasKeyboard = /keydown|keyup/.test(spec.code);
      const hasMouseOrTouch = /mousedown|mouseup|touchstart|touchend|click/.test(spec.code);
      return hasKeyboard && hasMouseOrTouch;
    },
    message: 'InputManager must support at least keyboard and mouse/touch',
    fix: 'Add event listeners for keyboard and mouse/touch'
  },
  // PILAR 5: Save System
  {
    id: 'SAVE_001',
    level: 'CRITICAL' as ViolationLevel,
    pilar: 'Save System',
    rule: 'SaveManager must exist',
    check: (spec: RuntimeSpec) => spec.hasSaveManager === true || /localStorage/.test(spec.code),
    message: 'SaveManager is required for data persistence',
    fix: 'Add SaveManager to core systems'
  },
  {
    id: 'SAVE_002',
    level: 'CRITICAL' as ViolationLevel,
    pilar: 'Save System',
    rule: 'HighScore must be saved to localStorage',
    check: (spec: RuntimeSpec) => {
      const hasSave = /localStorage\.setItem/.test(spec.code) || /saveHighScore/.test(spec.code);
      const hasLoad = /localStorage\.getItem/.test(spec.code) || /loadHighScore/.test(spec.code);
      return hasSave && hasLoad;
    },
    message: 'HighScore must be persisted using localStorage',
    fix: 'Add saveHighScore() and loadHighScore() methods'
  },
  // PILAR 6: Viewport Management
  {
    id: 'VIEWPORT_001',
    level: 'CRITICAL' as ViolationLevel,
    pilar: 'Viewport Management',
    rule: 'Resize handler must exist',
    check: (spec: RuntimeSpec) => /addEventListener\s*\(\s*['"]resize['"]/.test(spec.code) || /handleResize/.test(spec.code),
    message: 'Resize handler is required for responsive canvas',
    fix: 'Add window resize event listener'
  },
  // PILAR 7: Game Loop
  {
    id: 'LOOP_001',
    level: 'CRITICAL' as ViolationLevel,
    pilar: 'Game Loop',
    rule: 'Must use requestAnimationFrame',
    check: (spec: RuntimeSpec) => /requestAnimationFrame/.test(spec.code),
    message: 'Game loop must use requestAnimationFrame',
    fix: 'Replace setInterval/setTimeout with requestAnimationFrame'
  },
  {
    id: 'LOOP_002',
    level: 'CRITICAL' as ViolationLevel,
    pilar: 'Game Loop',
    rule: 'Must separate update() and render()',
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
          rule: rule.rule,
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

function formatViolationsForAI(result: ValidationResult): string {
  if (result.isValid && result.violations.length === 0) {
    return 'CONSTITUTIONAL_VALIDATION_PASSED';
  }

  let output = 'CONSTITUTIONAL_VALIDATION_FAILED\n\n';
  output += `violations: [\n`;
  
  result.violations.forEach(v => {
    output += `  { id: '${v.id}', level: '${v.level}', pilar: '${v.pilar}', message: '${v.message}', fix: '${v.fix}' },\n`;
  });
  
  output += `]\n\n`;
  output += `REQUIRED_ACTION: Fix all CRITICAL violations and regenerate code.\n`;
  output += `PROHIBITED: Responding "game ready" or suggesting "add later".\n`;

  return output;
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

type OrdaxGameType = "platformer" | "topdown" | "shooter" | "puzzle" | "racing" | "sports" | "unknown";

type GamePlan = {
  kind: "GAME_PLAN";
  gameType: OrdaxGameType;
  title: string;
  description: string;
  // minimal contract: guarantees a playable loop
  coreLoop: string;
  requiredSystems: string[];
  requiredEntities: string[];
  loopType: "winlose" | "survival" | "objective";
  // constitutional lifecycle contract: prevents “silent sandbox”
  lifecycle: {
    requiredStates: ("start" | "playing" | "gameover")[];
    requiredTransitions: ("start->playing" | "playing->gameover" | "gameover->restart")[];
    requiredUI: ("hud" | "gameover_screen")[];
    /** any-of: at least one must exist; signal chooses the one used by the minimal loop */
    requiredSignalsAnyOf: ("player_health" | "objective_progress" | "timer")[];
    signal: "player_health" | "objective_progress" | "timer";
    requiredControls: ("start_game" | "restart_game")[];
    startCondition: string;
    loseCondition: string;
    winCondition?: string;
    scoreRule: string;
  };
  // minimal content expectations so the spec can't be "empty"
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

function promptRequiredSystems(prompt: string): { systems: string[]; notes: string[] } {
  const notes: string[] = [];
  const systems: string[] = [];

  if (containsAny(prompt, ["diálogo", "dialogo", "npc", "conversa"])) {
    systems.push("DialogueSystem");
    notes.push("Prompt menciona diálogo/NPC → exigir DialogueSystem");
  }
  if (containsAny(prompt, ["inventário", "inventario", "loot", "itens", "items"])) {
    systems.push("InventorySystem");
    notes.push("Prompt menciona inventário/itens → exigir InventorySystem");
  }
  if (containsAny(prompt, ["salvar", "save", "checkpoint"])) {
    systems.push("SaveSystem");
    notes.push("Prompt menciona salvar/checkpoint → exigir SaveSystem");
  }
  if (containsAny(prompt, ["áudio", "audio", "som", "música", "musica", "sfx", "music"])) {
    systems.push("AudioSystem");
    notes.push("Prompt menciona áudio → exigir AudioSystem");
  }
  if (containsAny(prompt, ["partícula", "particula", "poeira", "explosão", "explosao", "fx"])) {
    systems.push("ParticleSystem");
    notes.push("Prompt menciona efeitos/partículas → exigir ParticleSystem");
  }

  return { systems: uniq(systems), notes };
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
  // objective_progress
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
  let requiredSystems = uniq([...rawSystems, ...genreReq, ...promptReq.systems]);

  // auto-complete missing essentials (contract)
  for (const s of genreReq) {
    if (!requiredSystems.includes(s)) {
      requiredSystems.push(s);
      warnings.push(`Plano incompleto: adicionado system obrigatório do gênero: ${s}`);
    }
  }
  for (const s of promptReq.systems) {
    if (!requiredSystems.includes(s)) {
      requiredSystems.push(s);
      warnings.push(`Plano incompleto: adicionado system exigido pelo prompt: ${s}`);
    }
  }

  // must-have mechanics derived from systems/profile
  const mustHave = {
    hasHUD: true,
    hasScore: requiredSystems.includes("ScoreSystem"),
    hasSpawner: requiredSystems.includes("SpawnerSystem"),
    hasAI: requiredSystems.includes("AISystem"),
    // for puzzle/racing/sports, enemies are optional; for action genres, force enemies
    hasEnemies: gameType === "topdown" || gameType === "shooter" || gameType === "platformer" ? true : false,
  };

  // Ensure contract essentials for action genres
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

  // Entity/system alignment (prevents "enemy but no AI/spawns")
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

  // carry prompt requirement notes into warnings (helps debugging)
  for (const n of promptReq.notes) warnings.push(`Validação: ${n}`);

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

function systemPrompt() {
  return `
Você é a IA do Ordax (engine de jogos). Gere APENAS um JSON válido, sem markdown nem cercas de código.

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

 CONTRATO DE SAÍDA (SEMPRE):
{
  "spec": {
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
  },
  "assistantSummary": string,
   "appliedEdits": string[],
   "semanticPatch": { "kind": "SEMANTIC_PATCH", "ops": any[] },
   "report": {
     "whatWasRequested": string,
     "whatWasApplied": string[],
     "whatCouldNotBeAppliedAndWhy": string[],
     "engineLimitationsHit": string[]
   }
}

 Regras do contrato:
- spec deve ser o JSON COMPLETO atualizado (não devolva dicas soltas).
- assistantSummary: 2-5 linhas dizendo exatamente o que foi implementado.
- appliedEdits: lista curta (3-10) de mudanças concretas.
 - semanticPatch: obrigatório; descreve semanticamente o que mudou (ops devem corresponder ao que você aplicou).
 - report: obrigatório; responda de forma objetiva.
 
 Se você NÃO conseguir aplicar o pedido, retorne um JSON de erro: { "error": "COMPILER_ERROR", "message": "...", "engineLimitationsHit": string[] } (sem spec).

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

EXEMPLOS DE BACKGROUNDS CORRETOS:
- Racing: { "type": "gradient", "parallax": 0 } com background: "hsl(120, 20%, 30%)" (pista verde)
- Platformer: { "type": "gradient", "parallax": 0.2 } com background: "hsl(200, 60%, 60%)" (céu azul)
- Shooter/Space: { "type": "starfield", "density": 200, "speedY": 50, "parallax": 0.3 }
- Puzzle: { "type": "solid", "parallax": 0 } com background: "hsl(240, 30%, 20%)" (fundo escuro)

- entities: não inventar assets reais; descrever com props simples (ex: speed, health).
- Se o usuário pedir algo fora de escopo, ainda devolver gameType coerente, scene mínima + visual completo.

⚠️ VALIDAÇÃO CONSTITUCIONAL:
Seu código será validado automaticamente. Se falhar, você DEVE corrigir TODAS as violações CRÍTICAS.
NÃO responda "jogo pronto" ou sugira "adicionar depois". Gere TUDO desde o início.
`.trim();
}

function coachPrompt() {
  return `
Você é o Ordax AI Coach. O usuário JÁ TEM um jogo gerado e quer melhorar o projeto atual.

Tarefa:
- Analise o currentSpec (JSON do projeto) e devolva APENAS texto (sem JSON, sem markdown).
- Seja direto e prático: no máximo 3 bullets curtos (1 linha cada).
- Foque em: (1) experiência do jogador (game loop), (2) feedback visual/sonoro, (3) equilíbrio (score/dificuldade), (4) robustez (erros comuns no spec), (5) próximos passos concretos.
- Quando sugerir mudanças, cite os módulos da engine pelo nome (ex: PhysicsSystem, CollisionSystem, ParticleSystem, UISystem, ScoreSystem, TimerSystem, AISystem, CameraSystem, AudioSystem, AnimationSystem, SpawnerSystem).

Formato:
1 linha de contexto + 2-3 bullets.
`.trim();
}

function codePatchPrompt(targetGameId: string | undefined) {
  return `
Você é um Code Mutator Agent do Ordax. Gere APENAS um JSON válido (sem markdown) contendo um patch estrutural de código TypeScript.

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

CONTRATO DE SAÍDA (SEMPRE):
{
  "patch": {
    "kind": "CODE_SEMANTIC_PATCH",
    "version": "1",
    "gameId": "${String(targetGameId ?? "")}",
    "ops": [
      { "op": "create_file", "path": "/vfs/games/<gameId>/...", "content": "..." },
      { "op": "update_file", "path": "/vfs/games/<gameId>/...", "content": "..." },
      { "op": "rename_file", "from": "/vfs/games/<gameId>/a.ts", "to": "/vfs/games/<gameId>/b.ts" },
      { "op": "delete_file", "path": "/vfs/games/<gameId>/..." }
    ]
  },
  "assistantSummary": string,
  "appliedEdits": string[],
  "report": {
    "whatWasRequested": string,
    "whatWasApplied": string[],
    "whatCouldNotBeAppliedAndWhy": string[],
    "engineLimitationsHit": string[]
  }
}

Se você NÃO conseguir aplicar o pedido com segurança, retorne:
{ "error": "COMPILER_ERROR", "message": "...", "engineLimitationsHit": string[] }
`.trim();
}

serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: corsHeaders });

  try {
    const { messages, currentSpec, mode, phase, approvedPlan, approvedPlanHuman, targetGameId, projectFiles, userId, action } = (await req.json()) as {
      messages: ChatMessage[];
      currentSpec?: unknown;
      mode?: Mode;
      phase?: "plan" | "spec";
      approvedPlan?: unknown;
      approvedPlanHuman?: unknown;
      targetGameId?: unknown;
      projectFiles?: unknown;
      userId?: string;
      action?: string;
    };

    const resolvedMode: Mode = mode ?? "spec";

    const LOVABLE_API_KEY = Deno.env.get("LOVABLE_API_KEY");
    if (!LOVABLE_API_KEY) throw new Error("LOVABLE_API_KEY is not configured");

    const SUPABASE_URL = Deno.env.get("SUPABASE_URL");
    const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
    if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) {
      throw new Error("Supabase credentials not configured");
    }

    // Inicializar store de sessões
    const sessionStore = new CompilerSessionStore(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

    // ============================================================================
    // PARTE 2: VALIDAÇÃO DE FASE DO COMPILADOR (Protocolo Obrigatório)
    // ============================================================================
    
    // Obter ou criar sessão do compilador (com persistência)
    const sessionId = getSessionId(messages, userId);
    const isNewGame = resolvedMode === "spec" && !currentSpec;
    const session = await sessionStore.getOrCreateSession(sessionId, isNewGame, userId, typeof targetGameId === "string" ? targetGameId : undefined);

    // Processar ação de aprovação
    if (action === "APPROVE_PLAN" && session.gamePlan) {
      await sessionStore.updateSession(sessionId, {
        approvedByUser: true,
        phase: "compilation"
      });
      
      // Recarregar sessão atualizada
      const updatedSession = await sessionStore.loadSession(sessionId);
      if (updatedSession) {
        Object.assign(session, updatedSession);
      }
    }

    // Validar fase atual antes de permitir geração
    if (isNewGame) {
      // Para NEW_GAME, protocolo de 5 fases é OBRIGATÓRIO
      
      // Se tentando compilar sem passar pelas fases anteriores
      if (phase === "spec" && session.phase !== "compilation") {
        return new Response(JSON.stringify({
          error: "COMPILER_PROTOCOL_VIOLATION",
          message: `Cannot compile game. Current phase: ${session.phase}. Must complete all phases: interpretation → plan → validation → confirmation → compilation`,
          currentPhase: session.phase,
          requiredPhase: "compilation",
          protocol: "ORDAX_COMPILER_PROTOCOL_V1"
        }), {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }

      // Se tentando compilar sem aprovação do usuário
      if (phase === "spec" && !session.approvedByUser) {
        return new Response(JSON.stringify({
          error: "COMPILER_PROTOCOL_VIOLATION",
          message: "Cannot compile game without user approval. User must explicitly approve the game plan.",
          currentPhase: session.phase,
          approvedByUser: session.approvedByUser,
          protocol: "ORDAX_COMPILER_PROTOCOL_V1"
        }), {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }
    }

    if (resolvedMode === "coach" && !currentSpec) {
      return new Response(JSON.stringify({ error: "currentSpec é obrigatório no modo coach" }), {
        status: 400,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    // ============================================================================
    // PARTE 3: LÓGICA DE FASES DO COMPILADOR (Protocolo de 5 Fases)
    // ============================================================================
    
    const userPrompt = (messages ?? []).slice().reverse().find((m) => m.role === "user")?.content ?? "";
    let planWarnings: string[] = [];
    let validatedPlan: GamePlan | null = null;
    let planDiff: PlanDiff | null = null;
    
    if (isNewGame) {
      // Determinar fase atual baseado no input
      const currentPhase = session.phase;
      
      // FASE 1: INTERPRETATION
      if (currentPhase === "interpretation") {
        // Gerar interpretação do pedido
        const interpretationPrompt = `Você é o Ordax Interpreter. Analise o pedido do usuário e retorne APENAS um JSON válido (sem markdown).

Formato obrigatório:
{
  "phase": "interpretation",
  "interpretation": {
    "gameType": "platformer"|"topdown"|"shooter"|"puzzle"|"racing"|"sports"|"unknown",
    "mechanics": ["mecânica 1", "mecânica 2", ...],
    "restrictions": ["restrição 1", "restrição 2", ...],
    "objective": "descrição do objetivo do jogador em 1 frase"
  }
}

Regras:
- Identifique o tipo de jogo explicitamente
- Liste TODAS as mecânicas mencionadas pelo usuário
- Identifique restrições (ex: "sem inimigos", "tempo limitado")
- Descreva o objetivo do jogador claramente
- NÃO assuma mecânicas não mencionadas
- NÃO invente restrições`;

        const interpretationResp = await fetch("https://ai.gateway.lovable.dev/v1/chat/completions", {
          method: "POST",
          headers: {
            Authorization: `Bearer ${LOVABLE_API_KEY}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            model: "google/gemini-3-flash-preview",
            messages: [{ role: "system", content: interpretationPrompt }, ...(messages ?? [])],
            temperature: 0.2,
          }),
        });

        if (!interpretationResp.ok) {
          const t = await interpretationResp.text();
          console.error("AI gateway (interpretation) error:", interpretationResp.status, t);
          return new Response(JSON.stringify({ error: "AI gateway error (interpretation)" }), {
            status: 500,
            headers: { ...corsHeaders, "Content-Type": "application/json" },
          });
        }

        const interpretationPayload = (await interpretationResp.json()) as any;
        const interpretationText = interpretationPayload?.choices?.[0]?.message?.content as string | undefined;
        const cleanedInterpretation = (interpretationText ?? "").replace(/^```[a-zA-Z]*\n?/, "").replace(/\n?```$/, "").trim();
        
        let interpretationResult: any;
        try {
          interpretationResult = JSON.parse(cleanedInterpretation);
        } catch {
          return new Response(JSON.stringify({ error: "Failed to parse interpretation result" }), {
            status: 500,
            headers: { ...corsHeaders, "Content-Type": "application/json" },
          });
        }

        // Atualizar sessão com interpretação e avançar para próxima fase
        await sessionStore.updateSession(sessionId, {
          interpretationResult: interpretationResult.interpretation,
          phase: "plan"
        });

        return new Response(JSON.stringify({
          kind: "INTERPRETATION_RESULT",
          phase: "interpretation",
          interpretation: interpretationResult.interpretation,
          nextPhase: "plan",
          sessionId
        }), {
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }
      
      // FASE 2: PLAN CONSTRUCTION
      if (currentPhase === "plan" && !approvedPlan) {
        const planPrompt = `Você é o Ordax Planner. Gere APENAS um JSON válido (sem markdown) do tipo GAME_PLAN.

Regras:
- O output DEVE ter: kind="GAME_PLAN", gameType, title, description, coreLoop, requiredSystems (array).
- requiredSystems deve usar apenas módulos suportados: ${ORDAX_ALLOWED_SYSTEMS.join(", ")}.
- O plano deve incluir um coreLoop jogável e evitar jogos vazios.

Formato:
{
  "phase": "plan",
  "kind": "GAME_PLAN",
  "gameType": "platformer"|"topdown"|"shooter"|"puzzle"|"racing"|"sports"|"unknown",
  "title": string,
  "description": string,
  "coreLoop": string,
  "requiredSystems": string[],
  "requiredEntities": string[],
  "loopType": "winlose"|"survival"|"objective",
  "lifecycle": {
    "requiredStates": ["start", "playing", "gameover"],
    "requiredTransitions": ["start->playing", "playing->gameover", "gameover->restart"],
    "requiredUI": ["hud", "gameover_screen"],
    "requiredSignalsAnyOf": ["player_health", "objective_progress", "timer"],
    "signal": "player_health"|"objective_progress"|"timer",
    "requiredControls": ["start_game", "restart_game"],
    "startCondition": string,
    "loseCondition": string,
    "winCondition": string (opcional),
    "scoreRule": string
  },
  "mustHave": {
    "hasEnemies": boolean,
    "hasAI": boolean,
    "hasScore": boolean,
    "hasHUD": boolean,
    "hasSpawner": boolean
  }
}`;

        const planResp = await fetch("https://ai.gateway.lovable.dev/v1/chat/completions", {
          method: "POST",
          headers: {
            Authorization: `Bearer ${LOVABLE_API_KEY}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            model: "google/gemini-3-flash-preview",
            messages: [
              { role: "system", content: planPrompt },
              { role: "system", content: `INTERPRETATION: ${JSON.stringify(session.interpretation)}` },
              ...(messages ?? [])
            ],
            temperature: 0.2,
          }),
        });

        if (!planResp.ok) {
          const t = await planResp.text();
          console.error("AI gateway (plan) error:", planResp.status, t);
          return new Response(JSON.stringify({ error: "AI gateway error (plan)" }), {
            status: 500,
            headers: { ...corsHeaders, "Content-Type": "application/json" },
          });
        }

        const planPayload = (await planResp.json()) as any;
        const planText = planPayload?.choices?.[0]?.message?.content as string | undefined;
        const cleanedPlan = (planText ?? "").replace(/^```[a-zA-Z]*\n?/, "").replace(/\n?```$/, "").trim();
        
        let planJson: any;
        try {
          planJson = JSON.parse(cleanedPlan);
        } catch {
          planWarnings.push("Planner retornou JSON inválido; plano foi auto-gerado no backend.");
          planJson = {
            kind: "GAME_PLAN",
            gameType: "unknown",
            title: "Jogo",
            description: "",
            coreLoop: "",
            requiredSystems: [],
            requiredEntities: [],
          };
        }

        // Validar e completar o plano
        const completed = validateAndCompletePlan(planJson, userPrompt);
        validatedPlan = completed.plan;
        planWarnings = uniq([...planWarnings, ...completed.warnings]);
        planDiff = completed.diff;

        // Atualizar sessão com plano e avançar para validação
        await sessionStore.updateSession(sessionId, {
          gamePlan: validatedPlan,
          phase: "validation"
        });

        return new Response(JSON.stringify({
          kind: "GAME_PLAN_RESULT",
          phase: "plan",
          plan: validatedPlan,
          planWarnings,
          planDiff,
          nextPhase: "validation",
          sessionId
        }), {
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }

      // FASE 3: CONSTITUTIONAL VALIDATION
      if (currentPhase === "validation") {
        // Obter plano da sessão
        const planToValidate = session.gamePlan;
        if (!planToValidate) {
          return new Response(JSON.stringify({ error: "No game plan found in session" }), {
            status: 400,
            headers: { ...corsHeaders, "Content-Type": "application/json" },
          });
        }

        // Criar um runtimeSpec simulado para validação
        const mockSpec: RuntimeSpec = {
          code: JSON.stringify(planToValidate),
          hasTimeManager: true, // Assumir que será gerado
          hasStateManager: true,
          hasInputManager: true,
          hasSaveManager: true,
          hasViewportManager: true,
          hasStartScreen: true,
          hasHUD: planToValidate.mustHave?.hasHUD ?? true,
          hasGameOverScreen: true
        };

        const validationResult = validateConstitutionalCompliance(mockSpec);

        // Atualizar sessão com resultado da validação
        await sessionStore.updateSession(sessionId, {
          validationReport: validationResult,
          phase: "confirmation"
        });

        return new Response(JSON.stringify({
          kind: "VALIDATION_RESULT",
          phase: "validation",
          validation: validationResult,
          plan: planToValidate,
          nextPhase: "confirmation",
          sessionId
        }), {
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }

      // FASE 4: USER CONFIRMATION
      if (currentPhase === "confirmation" && !session.approvedByUser) {
        // Retornar plano para confirmação do usuário
        const planToConfirm = session.gamePlan;
        const validationReport = session.validationReport;

        return new Response(JSON.stringify({
          kind: "CONFIRMATION_REQUIRED",
          phase: "confirmation",
          plan: planToConfirm,
          validation: validationReport,
          message: "Please review and approve the game plan before compilation",
          nextPhase: "compilation",
          sessionId
        }), {
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }

      // FASE 5: COMPILATION
      // Se chegou aqui com approvedPlan, significa que o usuário aprovou
      if (approvedPlan || session.approvedByUser) {
        // Usar plano da sessão se já foi aprovado
        const planSource = approvedPlan || session.gamePlan;
        let planJson: unknown = planSource ?? {};

        const completed = validateAndCompletePlan(planJson, userPrompt);
        validatedPlan = completed.plan;
        planWarnings = uniq([...planWarnings, ...completed.warnings]);
        planDiff = completed.diff;
      }
    }

    // ============================================================================
    // COMPILAÇÃO (Fase 5 ou edição de jogo existente)
    // ============================================================================

    if (isNewGame && !validatedPlan) {
      // Se chegou aqui sem plano validado, algo deu errado
      return new Response(JSON.stringify({
        error: "COMPILER_PROTOCOL_VIOLATION",
        message: "Cannot compile without validated plan",
        currentPhase: session.phase
      }), {
        status: 400,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    if (resolvedMode === "coach" && !currentSpec) {
      return new Response(JSON.stringify({ error: "currentSpec é obrigatório no modo coach" }), {
        status: 400,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const editHint =
      resolvedMode === "spec" && currentSpec
        ? `\n\nCONTEXTO: Existe um JSON atual do projeto (currentSpec). Sua tarefa é EDITAR o projeto atual: mantenha o máximo possível e altere APENAS o necessário para atender o pedido do usuário. Preencha appliedEdits com as mudanças que VOCÊ realmente fez e escreva assistantSummary com o resultado implementado.`
        : "";

     const codeCtx =
       resolvedMode === "code_patch"
         ? `\n\nTARGET_GAME_ID: ${String(targetGameId ?? "")}\n` +
           (Array.isArray(projectFiles)
             ? `\nPROJECT_FILES (paths):\n${(projectFiles as any[])
                 .map((f) => (typeof f?.path === "string" ? f.path : ""))
                 .filter(Boolean)
                 .slice(0, 200)
                 .join("\n")}`
             : "")
         : "";

     const response = await fetch("https://ai.gateway.lovable.dev/v1/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${LOVABLE_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "google/gemini-3-flash-preview",
        messages: [
          {
            role: "system",
            content:
               resolvedMode === "coach"
                ? coachPrompt()
                 : resolvedMode === "code_patch"
                   ? (codePatchPrompt(typeof targetGameId === "string" ? (targetGameId as string) : undefined) + codeCtx)
                   : (systemPrompt() +
                     editHint +
                      (validatedPlan
                        ? `\n\nGAME_PLAN (validado): ${JSON.stringify(validatedPlan)}\n\nRegras adicionais do contrato NEW_GAME:\n- O runtimeSpec DEVE implementar o coreLoop do GAME_PLAN (loopType=${validatedPlan.loopType}).\n- requiredEntities do plano DEVEM existir na scene.entities (player/spawner/enemy/pickup quando aplicável).\n- Se mustHave.hasEnemies=true, inclua inimigos + AI + spawner.\n- Sempre inclua ScoreSystem + UISystem + TimerSystem e UI mínima.\n- Lifecycle constitucional (obrigatório):\n  - Estados: start → playing → gameover, com transição gameover → restart.\n  - Controles: start_game e restart_game.\n  - UI: hud + gameover_screen.\n  - Condições explícitas: startCondition, loseCondition e (opcional) winCondition.\n  - signal=${validatedPlan.lifecycle.signal} deve ser visível na HUD e dirigir o loop.\n- Não gere jogo vazio.\n\nPLANO HUMANO (checklist semântico; linguagem natural):\n${typeof approvedPlanHuman === "string" && approvedPlanHuman.trim() ? approvedPlanHuman.trim() : "(não fornecido)"}\n\nRegra: se houver conflito entre o PLANO HUMANO e o GAME_PLAN JSON, siga o GAME_PLAN JSON.`
                        : (typeof approvedPlanHuman === "string" && approvedPlanHuman.trim()
                            ? `\n\nPLANO HUMANO (contrato aceito; checklist semântico):\n${approvedPlanHuman.trim()}\n\nRegra: suas mudanças (ADD_FEATURE/FIX_BUG) DEVEM obedecer o plano aceito. Se houver conflito, reporte em report.engineLimitationsHit e retorne COMPILER_ERROR se não puder aplicar.`
                            : ""))),
          },
          ...(currentSpec ? [{ role: "system", content: `currentSpec (JSON): ${JSON.stringify(currentSpec)}` }] : []),
          ...(messages ?? []),
        ],
        temperature: 0.2,
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
        return new Response(
          JSON.stringify({ error: "Payment required, please add credits to your Lovable AI workspace." }),
          {
            status: 402,
            headers: { ...corsHeaders, "Content-Type": "application/json" },
          },
        );
      }

      const t = await response.text();
      console.error("AI gateway error:", response.status, t);
      return new Response(JSON.stringify({ error: "AI gateway error" }), {
        status: 500,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const gatewayPayload = (await response.json()) as any;
    const text = gatewayPayload?.choices?.[0]?.message?.content as string | undefined;
    if (!text) {
      return new Response(JSON.stringify({ error: "Empty AI response" }), {
        status: 500,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    // A IA foi instruída a devolver JSON puro, mas ainda sanitizamos cercas de código por segurança.
    const cleaned = text.replace(/^```[a-zA-Z]*\n?/, "").replace(/\n?```$/, "").trim();

    // Backend guard-rails (code_patch): valida patch contra o mapa semântico.
    if (resolvedMode === "code_patch") {
      if (typeof targetGameId !== "string" || !targetGameId.trim()) {
        return new Response(JSON.stringify({ error: "targetGameId obrigatório no mode=code_patch" }), {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }
      let parsed: any;
      try {
        parsed = JSON.parse(cleaned);
      } catch {
        return new Response(
          JSON.stringify({
            error: "COMPILER_ERROR",
            message: "Saída do modelo não é JSON válido (code_patch).",
            engineLimitationsHit: ["model_output_invalid_json"],
          }),
          { headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
      }

      if (parsed?.error) {
        return new Response(JSON.stringify({ raw: cleaned }), {
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }

      try {
        validateCodeSemanticPatchOrThrow(parsed?.patch, targetGameId);
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        const outErr = {
          error: "COMPILER_ERROR",
          message: `Patch rejeitado pelo backend: ${msg}`,
          engineLimitationsHit: ["mutation_guide_violation"],
        };
        return new Response(JSON.stringify({ raw: JSON.stringify(outErr) }), {
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }
    }

    // CONSTITUTIONAL VALIDATION (Parte 3 - Integração)
    // Valida jogos gerados contra o Contrato Constitucional V1
    if (resolvedMode === "spec" && !currentSpec) {
      // Apenas valida NEW_GAME (não edições)
      let parsed: any;
      try {
        parsed = JSON.parse(cleaned);
      } catch {
        // Se não conseguir parsear, deixa passar (erro será tratado no frontend)
        console.warn("Could not parse spec for constitutional validation");
      }

      if (parsed && parsed.spec && !parsed.error) {
        const specCode = JSON.stringify(parsed.spec);
        const runtimeSpec: RuntimeSpec = {
          code: specCode,
          hasTimeManager: /TimeManager/.test(specCode),
          hasStateManager: /StateManager|currentState/.test(specCode),
          hasInputManager: /InputManager|keys.*Map/.test(specCode),
          hasSaveManager: /SaveManager|localStorage/.test(specCode),
          hasViewportManager: /ViewportManager|handleResize/.test(specCode),
          hasStartScreen: /StartScreen|renderStartScreen/.test(specCode),
          hasHUD: /HUD|renderHUD/.test(specCode),
          hasGameOverScreen: /GameOverScreen|renderGameOverScreen/.test(specCode)
        };

        const validation = validateConstitutionalCompliance(runtimeSpec);

        if (!validation.isValid) {
          console.warn("Constitutional validation failed:", validation);
          
          // Retorna erro constitucional para o AI corrigir
          const constitutionalError = {
            error: "CONSTITUTIONAL_ERROR",
            message: "Game violates Ordax Engine Contract V1",
            violations: validation.violations,
            summary: validation.summary,
            aiPrompt: formatViolationsForAI(validation)
          };

          return new Response(JSON.stringify({ raw: JSON.stringify(constitutionalError) }), {
            headers: { ...corsHeaders, "Content-Type": "application/json" },
          });
        }

        console.log("Constitutional validation passed ✅");
      }
    }

    // Mantém compatibilidade: no modo spec retornamos {raw}; no coach retornamos {text}.
    // Para NEW_GAME, retornamos também warnings do GAME_PLAN (fora do raw, para não quebrar parser do frontend).
    const out =
      resolvedMode === "coach"
        ? { text: cleaned }
        : isNewGame
          ? { raw: cleaned, planWarnings, planDiff }
          : { raw: cleaned };

    return new Response(JSON.stringify(out), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (e) {
    console.error("game-ai-chat error:", e);
    return new Response(JSON.stringify({ error: e instanceof Error ? e.message : "Unknown error" }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
