export type EngineGapReport = {
  title?: string;
  items?: { area: string; limitation: string; workaround?: string }[];
} | null;

type HumanSection = {
  id:
    | "title"
    | "mechanics"
    | "controls"
    | "systems"
    | "hud"
    | "flow"
    | "visual"
    | "audio"
    | "difficulty"
    | "auto_added"
    | "warnings"
    | "engine_gaps";
  title: string;
  bullets: string[];
};

function asString(v: unknown): string | undefined {
  return typeof v === "string" && v.trim() ? v.trim() : undefined;
}

function asStringArray(v: unknown): string[] {
  return Array.isArray(v)
    ? v
        .filter((x): x is string => typeof x === "string" && x.trim().length > 0)
        .map((s) => s.trim())
    : [];
}

function labelGameType(gameType: string | undefined): string {
  switch ((gameType ?? "").toLowerCase()) {
    case "platformer":
      return "Plataforma 2D";
    case "topdown":
      return "Top-down";
    case "shooter":
      return "Shooter";
    case "puzzle":
      return "Puzzle";
    case "racing":
      return "Corrida";
    case "sports":
      return "Esportes";
    default:
      return "Indefinido";
  }
}

const SYSTEM_HUMAN: Record<string, { label: string; desc: string }> = {
  PhysicsSystem: { label: "Movimento & física", desc: "Movimentação, gravidade e aceleração." },
  CollisionSystem: { label: "Colisões", desc: "Detecção e resposta a colisões entre entidades." },
  CameraSystem: { label: "Câmera", desc: "Enquadramento/seguimento do player e parallax." },
  UISystem: { label: "Interface (HUD)", desc: "HUD e telas (ex: game over)." },
  TimerSystem: { label: "Tempo", desc: "Cronômetro e regras baseadas em tempo." },
  ScoreSystem: { label: "Pontuação", desc: "Score e regras de pontuação." },
  SpawnerSystem: { label: "Spawns/ondas", desc: "Geração de inimigos/itens ao longo do jogo." },
  AISystem: { label: "IA de inimigos", desc: "Comportamento básico de inimigos." },
  ParticleSystem: { label: "Efeitos", desc: "Partículas e feedback visual (poeira/explosões)." },
  AnimationSystem: { label: "Animações", desc: "Transições/anim e feedback visual." },
  AudioSystem: { label: "Áudio", desc: "Música e SFX (se disponíveis)." },
  DialogueSystem: { label: "Diálogo", desc: "Conversas/NPCs e caixas de diálogo." },
  InventorySystem: { label: "Inventário", desc: "Itens/loot e gerenciamento de inventário." },
  SaveSystem: { label: "Salvar", desc: "Save/checkpoints (se aplicável)." },
};

const ENTITY_HUMAN: Record<string, string> = {
  player: "Jogador (player)",
  enemy: "Inimigos (enemy)",
  spawner: "Gerador de entidades (spawner)",
  pickup: "Coletáveis (pickup)",
  goal: "Objetivo/meta (goal)",
};

export type BuildHumanPlanInput = {
  plan: unknown;
  planDiff?: unknown;
  warnings?: string[];
  engineGapReport?: EngineGapReport;
};

export function buildHumanGamePlanSections(input: BuildHumanPlanInput): HumanSection[] {
  const plan = (input.plan ?? {}) as any;
  const planDiff = (input.planDiff ?? {}) as any;

  const title = asString(plan.title) ?? "Jogo";
  const gameType = asString(plan.gameType);
  const description = asString(plan.description);
  const coreLoop = asString(plan.coreLoop);
  const loopType = asString(plan.loopType);

  const requiredSystems = asStringArray(plan.requiredSystems);
  const requiredEntities = asStringArray(plan.requiredEntities);
  const lifecycle = (plan.lifecycle ?? {}) as any;

  const lifecycleSignal = asString(lifecycle.signal);
  const startCondition = asString(lifecycle.startCondition);
  const loseCondition = asString(lifecycle.loseCondition);
  const winCondition = asString(lifecycle.winCondition);
  const scoreRule = asString(lifecycle.scoreRule);

  const controls = asStringArray(lifecycle.requiredControls);
  const ui = asStringArray(lifecycle.requiredUI);
  const states = asStringArray(lifecycle.requiredStates);
  const transitions = asStringArray(lifecycle.requiredTransitions);

  const sections: HumanSection[] = [];

  sections.push({
    id: "title",
    title: "Título e gênero",
    bullets: [
      `Título: ${title}`,
      `Gênero: ${labelGameType(gameType)}` + (gameType ? ` (${gameType})` : ""),
      ...(description ? [`Descrição: ${description}`] : []),
      ...(loopType ? [`Tipo de loop: ${loopType}`] : []),
    ],
  });

  sections.push({
    id: "mechanics",
    title: "Mecânicas principais",
    bullets: [
      ...(coreLoop ? [`Core loop: ${coreLoop}`] : ["Core loop: (não especificado; será completado automaticamente)."]),
      ...(lifecycleSignal ? [`Sinal principal (HUD/loop): ${lifecycleSignal}`] : []),
      ...(scoreRule ? [`Regra de score: ${scoreRule}`] : []),
      ...(startCondition ? [`Condição de início: ${startCondition}`] : []),
      ...(loseCondition ? [`Condição de derrota: ${loseCondition}`] : []),
      ...(winCondition ? [`Condição de vitória: ${winCondition}`] : []),
    ],
  });

  sections.push({
    id: "controls",
    title: "Controles",
    bullets: controls.length
      ? controls.map((c) => `Ação: ${c}`)
      : ["Controles mínimos serão gerados (start/restart + movimento/ação conforme o gênero)."],
  });

  const systemBullets = requiredSystems.length
    ? requiredSystems.map((s) => {
        const h = SYSTEM_HUMAN[s];
        return h ? `${h.label}: ${h.desc} (${s})` : `System: ${s}`;
      })
    : ["Sistemas serão definidos automaticamente para garantir um jogo jogável."];

  sections.push({ id: "systems", title: "Sistemas do jogo", bullets: systemBullets });

  const hudBullets: string[] = [];
  if (ui.length) hudBullets.push(`UI obrigatória: ${ui.join(", ")}`);
  if (lifecycleSignal) hudBullets.push(`HUD deve mostrar: ${lifecycleSignal}`);
  if (!hudBullets.length) hudBullets.push("HUD mínimo será gerado (indicadores + tela de game over).");
  sections.push({ id: "hud", title: "HUD / Interface", bullets: hudBullets });

  const flowBullets: string[] = [];
  if (states.length) flowBullets.push(`Estados: ${states.join(" → ")}`);
  if (transitions.length) flowBullets.push(`Transições: ${transitions.join(", ")}`);
  if (!flowBullets.length) flowBullets.push("Fluxo mínimo: start → playing → gameover → restart.");
  sections.push({ id: "flow", title: "Fluxo do jogo", bullets: flowBullets });

  const entitiesBullets = requiredEntities.length
    ? requiredEntities.map((e) => ENTITY_HUMAN[e] ?? `Entidade: ${e}`)
    : ["Entidades mínimas (player/spawner/enemy/pickup) serão garantidas conforme o gênero."];
  sections.push({
    id: "difficulty",
    title: "Dificuldade / progressão",
    bullets: [
      "Progressão base (ondas/tempo/objetivo) será gerada; podemos adicionar níveis, escalonamento e balanceamento depois.",
      ...(requiredEntities.length ? [`Conteúdo mínimo: ${entitiesBullets.join("; ")}`] : []),
    ],
  });

  sections.push({
    id: "visual",
    title: "Visual",
    bullets: [
      "Paleta e tema serão gerados automaticamente (cores em HSL).",
      "Fonte padrão: ui-sans-serif (pode ser ajustada depois).",
      "Background seguirá regras por gênero (ex: shooter/space → starfield; racing/platformer/topdown → sem starfield).",
    ],
  });

  if (requiredSystems.includes("AudioSystem")) {
    sections.push({
      id: "audio",
      title: "Áudio",
      bullets: ["Áudio ativado: o jogo terá música e efeitos sonoros (assets podem ser placeholders)."],
    });
  }

  const autoSystems = asStringArray(planDiff?.autoAddedSystems);
  const autoEntities = asStringArray(planDiff?.autoAddedEntities);
  const lifecycleDiff = (planDiff?.lifecycle ?? {}) as any;
  const autoStates = asStringArray(lifecycleDiff?.autoAddedStates);
  const autoTransitions = asStringArray(lifecycleDiff?.autoAddedTransitions);
  const autoUI = asStringArray(lifecycleDiff?.autoAddedUI);
  const autoControls = asStringArray(lifecycleDiff?.autoAddedControls);

  const autoBullets: string[] = [];
  if (autoSystems.length) autoBullets.push(`Systems auto-adicionados: ${autoSystems.join(", ")}`);
  if (autoEntities.length) autoBullets.push(`Entities auto-adicionadas: ${autoEntities.join(", ")}`);
  if (autoStates.length) autoBullets.push(`States auto-adicionados: ${autoStates.join(", ")}`);
  if (autoTransitions.length) autoBullets.push(`Transitions auto-adicionadas: ${autoTransitions.join(", ")}`);
  if (autoUI.length) autoBullets.push(`UI auto-adicionada: ${autoUI.join(", ")}`);
  if (autoControls.length) autoBullets.push(`Controls auto-adicionados: ${autoControls.join(", ")}`);
  if (autoBullets.length) sections.push({ id: "auto_added", title: "Auto-adicionado pelo sistema", bullets: autoBullets });

  const warnings = (input.warnings ?? []).filter((w) => typeof w === "string" && w.trim());
  if (warnings.length) sections.push({ id: "warnings", title: "Avisos", bullets: warnings });

  const gaps = input.engineGapReport;
  const gapItems = gaps?.items ?? [];
  if (gapItems.length) {
    sections.push({
      id: "engine_gaps",
      title: "Limitações da engine",
      bullets: gapItems.map((it) => {
        const w = it.workaround ? ` (workaround: ${it.workaround})` : "";
        return `${it.area}: ${it.limitation}${w}`;
      }),
    });
  }

  return sections;
}

export function buildHumanGamePlanText(input: BuildHumanPlanInput): string {
  const sections = buildHumanGamePlanSections(input);
  const lines: string[] = [];
  lines.push("PLANO HUMANO (para revisão do usuário e base semântica da geração)");
  for (const s of sections) {
    lines.push("");
    lines.push(`${s.title}:`);
    for (const b of s.bullets) lines.push(`- ${b}`);
  }
  return lines.join("\n").trim();
}
