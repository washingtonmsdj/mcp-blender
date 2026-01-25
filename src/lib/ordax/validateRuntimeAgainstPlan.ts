import type { OrdaxSpec } from "@/lib/ordax/types";

export type RuntimePlanIssue = {
  code:
    | "MISSING_REQUIRED_SYSTEM"
    | "MISSING_REQUIRED_ENTITY"
    | "MISSING_SHOOTER_PROPS"
    | "MISSING_AUDIO_BLOCK"
    | "ENGINE_GAP";
  severity: "error" | "warn";
  message: string;
  details?: string;
};

export type ValidateRuntimeAgainstPlanResult = {
  issues: RuntimePlanIssue[];
  warnings: string[];
  engineGapReport: {
    title: string;
    items: { area: string; limitation: string; workaround?: string }[];
  } | null;
};

function uniq(list: string[]) {
  return Array.from(new Set(list.filter((s) => typeof s === "string" && s.trim())));
}

function asStringArray(v: unknown): string[] {
  return Array.isArray(v)
    ? v
        .filter((x): x is string => typeof x === "string" && x.trim().length > 0)
        .map((s) => s.trim())
    : [];
}

function hasSystem(spec: OrdaxSpec, sys: string): boolean {
  return Array.isArray(spec.systems) && spec.systems.includes(sys);
}

function hasEntity(spec: OrdaxSpec, entityKey: string): boolean {
  const ents = spec.scene?.entities ?? [];
  const key = entityKey.toLowerCase();
  return ents.some((e) => {
    const id = String(e.id ?? "").toLowerCase();
    const type = String(e.type ?? "").toLowerCase();
    if (type === key || id === key) return true;
    // tolerate common naming patterns (enemy_1, spawner_main, etc.)
    if (id.startsWith(`${key}_`) || type.startsWith(`${key}_`)) return true;
    return false;
  });
}

function shooterHasFireProps(spec: OrdaxSpec): boolean {
  const player = (spec.scene?.entities ?? []).find((e) => String(e.type).toLowerCase() === "player" || e.id === "player");
  const p = (player?.props ?? {}) as Record<string, unknown>;
  return typeof p.fireRate === "number" && typeof p.bulletSpeed === "number";
}

/**
 * Guard-rails: garante que o runtimeSpec não viole o plano aceito.
 * NOTA: algumas partes do lifecycle/controles não existem no schema atual do runtimeSpec;
 * nesses casos, emitimos ENGINE_GAP (sem bloquear), porque não podemos provar pelo JSON.
 */
export function validateRuntimeAgainstPlan(plan: unknown, runtimeSpec: OrdaxSpec): ValidateRuntimeAgainstPlanResult {
  const p = (plan ?? {}) as any;
  const requiredSystems = asStringArray(p.requiredSystems);
  const requiredEntities = asStringArray(p.requiredEntities);
  const mustHave = (p.mustHave ?? {}) as any;
  const lifecycle = (p.lifecycle ?? {}) as any;

  const issues: RuntimePlanIssue[] = [];
  const warnings: string[] = [];
  const gaps: { area: string; limitation: string; workaround?: string }[] = [];

  // Systems
  for (const sys of requiredSystems) {
    if (!hasSystem(runtimeSpec, sys)) {
      issues.push({
        code: "MISSING_REQUIRED_SYSTEM",
        severity: "error",
        message: `Plano exige o system '${sys}', mas ele não existe no runtimeSpec.systems.`,
      });
    }
  }

  // Entities
  for (const ent of requiredEntities) {
    if (!hasEntity(runtimeSpec, ent)) {
      issues.push({
        code: "MISSING_REQUIRED_ENTITY",
        severity: "error",
        message: `Plano exige a entidade '${ent}', mas ela não existe na scene.entities.`,
      });
    }
  }

  // Mechanics derived from mustHave
  if (mustHave?.hasHUD && !hasSystem(runtimeSpec, "UISystem")) {
    issues.push({
      code: "MISSING_REQUIRED_SYSTEM",
      severity: "error",
      message: "Plano exige HUD, mas UISystem não está presente.",
      details: "Adicione UISystem e elementos mínimos de UI/gameover.",
    });
  }
  if (mustHave?.hasEnemies && !hasEntity(runtimeSpec, "enemy")) {
    issues.push({
      code: "MISSING_REQUIRED_ENTITY",
      severity: "error",
      message: "Plano exige inimigos, mas não há nenhuma entidade do tipo 'enemy'.",
    });
  }
  if (mustHave?.hasEnemies && !hasSystem(runtimeSpec, "AISystem")) {
    issues.push({
      code: "MISSING_REQUIRED_SYSTEM",
      severity: "error",
      message: "Plano exige inimigos, mas AISystem não está presente.",
    });
  }
  if (mustHave?.hasSpawner && !hasSystem(runtimeSpec, "SpawnerSystem")) {
    issues.push({
      code: "MISSING_REQUIRED_SYSTEM",
      severity: "error",
      message: "Plano exige spawns/ondas, mas SpawnerSystem não está presente.",
    });
  }

  // Collision: plan often implies CollisionSystem.
  // If plan requires CollisionSystem explicitly, we already error above.
  // Here we add a more human-friendly warning if the loop implies it.
  if (requiredEntities.includes("enemy") && !hasSystem(runtimeSpec, "CollisionSystem")) {
    warnings.push("Plano inclui inimigos; normalmente isso exige CollisionSystem para contato/dano.");
  }

  // Shooter invariants: engine uses player.props.fireRate/bulletSpeed.
  if (String(p.gameType ?? "").toLowerCase() === "shooter") {
    if (!shooterHasFireProps(runtimeSpec)) {
      issues.push({
        code: "MISSING_SHOOTER_PROPS",
        severity: "error",
        message: "Shooter exige player.props.fireRate e player.props.bulletSpeed (tiro), mas não foram encontrados.",
      });
    }
  }

  // Audio
  if (requiredSystems.includes("AudioSystem")) {
    if (!hasSystem(runtimeSpec, "AudioSystem")) {
      issues.push({
        code: "MISSING_REQUIRED_SYSTEM",
        severity: "error",
        message: "Plano exige áudio (AudioSystem), mas AudioSystem não está presente.",
      });
    }
    if (!runtimeSpec.audio) {
      issues.push({
        code: "MISSING_AUDIO_BLOCK",
        severity: "warn",
        message: "Plano exige áudio, mas o bloco spec.audio não existe (assets podem ficar como placeholders).",
      });
    }
  }

  // Lifecycle/controls/UI contract: schema atual não modela isso como JSON explícito.
  const requiredStates = asStringArray(lifecycle.requiredStates);
  const requiredTransitions = asStringArray(lifecycle.requiredTransitions);
  const requiredUI = asStringArray(lifecycle.requiredUI);
  const requiredControls = asStringArray(lifecycle.requiredControls);
  const signal = typeof lifecycle.signal === "string" ? lifecycle.signal : undefined;

  if (requiredStates.length || requiredTransitions.length || requiredUI.length || requiredControls.length) {
    gaps.push({
      area: "Lifecycle",
      limitation:
        "O runtimeSpec atual não possui um campo 'lifecycle/controls/ui' explícito para validar estados/transições/controles diretamente pelo JSON.",
      workaround:
        "Validamos proxies (UISystem, TimerSystem/ScoreSystem, entidades). Para validação completa, adicionar uma seção lifecycle no schema (sem mudar engine) ou expor sinais no spec.",
    });
  }

  if (signal && !["player_health", "objective_progress", "timer"].includes(signal)) {
    warnings.push(`Lifecycle.signal inesperado no plano: '${signal}'.`);
  }

  return {
    issues,
    warnings: uniq(warnings),
    engineGapReport: gaps.length
      ? {
          title: "Engine gaps (validação runtime vs plano)",
          items: gaps,
        }
      : null,
  };
}
