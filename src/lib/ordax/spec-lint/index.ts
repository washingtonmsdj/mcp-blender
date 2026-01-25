import type { OrdaxEntity, OrdaxSpec } from "@/lib/ordax/types";
import { COMMON_SYSTEM_ALIASES, ORDAX_ALLOWED_SYSTEMS, WORLD_BOUNDS } from "./constants";
import type { OrdaxSpecFix, OrdaxSpecIssue } from "./types";

function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(max, n));
}

function isHslString(v: unknown): boolean {
  if (typeof v !== "string") return false;
  const t = v.trim();
  // Keep it permissive; normalize() will enforce defaults.
  return t.startsWith("hsl(") || t.startsWith("hsla(");
}

function ensurePlayer(entities: OrdaxEntity[]): { entities: OrdaxEntity[]; fix?: OrdaxSpecFix } {
  const hasPlayer = entities.some((e) => e.id === "player" || e.type === "player");
  if (hasPlayer) return { entities };
  return {
    entities: [
      {
        id: "player",
        type: "player",
        x: WORLD_BOUNDS.w / 2,
        y: WORLD_BOUNDS.h * 0.8,
        w: 32,
        h: 32,
        props: { health: 100, speed: 260 },
      },
      ...entities,
    ],
    fix: {
      code: "ADD_PLAYER",
      message: "Player ausente → adicionado player padrão.",
    },
  };
}

function renameDuplicateIds(entities: OrdaxEntity[]): { entities: OrdaxEntity[]; fix?: OrdaxSpecFix } {
  const seen = new Map<string, number>();
  let changed = false;

  const out = entities.map((e) => {
    const base = e.id || "entity";
    const count = (seen.get(base) ?? 0) + 1;
    seen.set(base, count);
    if (count === 1) return e;
    changed = true;
    const newId = `${base}_${count}`;
    // keep player id stable if collision happens
    if (base === "player") return { ...e, id: "player" };
    return { ...e, id: newId };
  });

  return changed
    ? {
        entities: out,
        fix: {
          code: "RENAME_DUPLICATE_IDS",
          message: "IDs duplicados → renomeados automaticamente.",
        },
      }
    : { entities };
}

function clampEntitiesToWorld(entities: OrdaxEntity[]): { entities: OrdaxEntity[]; fix?: OrdaxSpecFix } {
  let changed = false;
  const out = entities.map((e) => {
    const w = Math.max(1, e.w);
    const h = Math.max(1, e.h);
    const x = clamp(e.x, w / 2, WORLD_BOUNDS.w - w / 2);
    const y = clamp(e.y, h / 2, WORLD_BOUNDS.h - h / 2);
    if (x !== e.x || y !== e.y) changed = true;
    return x !== e.x || y !== e.y ? { ...e, x, y } : e;
  });

  return changed
    ? {
        entities: out,
        fix: {
          code: "CLAMP_ENTITIES_TO_WORLD",
          message: "Entidades fora do mundo → ajustadas para dentro do frame.",
        },
      }
    : { entities };
}

function fixSystems(systems: unknown): { systems: string[]; fix?: OrdaxSpecFix } {
  const list = Array.isArray(systems) ? systems.filter((s) => typeof s === "string") : [];
  const out: string[] = [];
  const allowed = new Set<string>(ORDAX_ALLOWED_SYSTEMS);

  let changed = false;
  for (const s of list) {
    if (allowed.has(s)) {
      out.push(s);
      continue;
    }
    const alias = COMMON_SYSTEM_ALIASES[String(s).toLowerCase().replace(/\s+/g, "")];
    if (alias) {
      out.push(alias);
      changed = true;
      continue;
    }
    // drop unknown
    changed = true;
  }

  // de-dupe, keep order
  const deduped: string[] = [];
  const seen = new Set<string>();
  for (const s of out) {
    if (seen.has(s)) continue;
    seen.add(s);
    deduped.push(s);
  }

  return changed
    ? {
        systems: deduped,
        fix: {
          code: "FILTER_OR_MAP_SYSTEMS",
          message: "Systems inválidos → removidos/mapeados para módulos suportados.",
        },
      }
    : { systems: deduped };
}

export function lintOrdaxSpec(spec: unknown): OrdaxSpecIssue[] {
  const s = (spec ?? {}) as Partial<OrdaxSpec>;
  const issues: OrdaxSpecIssue[] = [];

  if (!s.gameType) {
    issues.push({
      code: "MISSING_GAME_TYPE",
      severity: "warn",
      message: "gameType ausente (será inferido/normalizado).",
    });
  }

  if (!s.title || !String(s.title).trim()) {
    issues.push({
      code: "MISSING_TITLE",
      severity: "warn",
      message: "title ausente (será preenchido).",
    });
  }

  const entities = s.scene?.entities;
  if (!Array.isArray(entities) || entities.length === 0) {
    issues.push({
      code: "MISSING_ENTITIES",
      severity: "error",
      message: "scene.entities vazio (jogo não renderiza corretamente).",
    });
  } else {
    const ids = entities.map((e) => (e as any)?.id).filter((id) => typeof id === "string");
    const duplicates = ids.filter((id, idx) => ids.indexOf(id) !== idx);
    if (duplicates.length) {
      issues.push({
        code: "DUPLICATE_ENTITY_IDS",
        severity: "error",
        message: "Existem IDs duplicados em entities (causa bugs em colisão/spawn).",
        details: `Duplicados: ${Array.from(new Set(duplicates)).join(", ")}`,
      });
    }

    // Bounds check (best-effort)
    const outOfBounds = entities.some((e) => {
      const x = (e as any)?.x;
      const y = (e as any)?.y;
      const w = (e as any)?.w;
      const h = (e as any)?.h;
      if (![x, y, w, h].every((n) => typeof n === "number")) return false;
      return x < w / 2 || x > WORLD_BOUNDS.w - w / 2 || y < h / 2 || y > WORLD_BOUNDS.h - h / 2;
    });
    if (outOfBounds) {
      issues.push({
        code: "ENTITY_OUT_OF_BOUNDS",
        severity: "warn",
        message: "Há entidades fora dos bounds do mundo (serão ajustadas).",
      });
    }
  }

  // Systems validation
  const systems = Array.isArray(s.systems) ? s.systems : [];
  const allowed = new Set<string>(ORDAX_ALLOWED_SYSTEMS);
  const invalid = systems.filter((sys) => typeof sys === "string" && !allowed.has(sys));
  if (invalid.length) {
    issues.push({
      code: "INVALID_SYSTEMS",
      severity: "warn",
      message: "Há systems não suportados pelo runtime (serão removidos/mapeados).",
      details: `Inválidos: ${Array.from(new Set(invalid)).join(", ")}`,
    });
  }

  // Theme sanity (warn only; normalize will default)
  const theme = s.visual?.theme as any;
  if (theme) {
    const bgOk = isHslString(theme.background);
    const pOk = isHslString(theme.primary);
    const aOk = isHslString(theme.accent);
    if (!bgOk || !pOk || !aOk) {
      issues.push({
        code: "THEME_NOT_HSL",
        severity: "warn",
        message: "Cores do theme não estão em HSL; normalize aplicará defaults.",
      });
    }
  }

  return issues;
}

export function autoFixOrdaxSpec(
  spec: unknown,
  issues?: OrdaxSpecIssue[]
): { spec: OrdaxSpec; fixes: OrdaxSpecFix[]; issues: OrdaxSpecIssue[] } {
  const detected = issues ?? lintOrdaxSpec(spec);
  const fixes: OrdaxSpecFix[] = [];

  const s = (spec ?? {}) as any;
  const base: OrdaxSpec = {
    gameType: s.gameType ?? "unknown",
    title: typeof s.title === "string" && s.title.trim() ? s.title.trim() : "Jogo",
    description: typeof s.description === "string" ? s.description : "",
    systems: Array.isArray(s.systems) ? s.systems : [],
    visual: s.visual,
    audio: s.audio,
    scene: {
      gravity: s.scene?.gravity ?? { x: 0, y: 0 },
      entities: Array.isArray(s.scene?.entities) ? s.scene.entities : [],
    },
  };

  // Systems
  const sysFixed = fixSystems(base.systems);
  base.systems = sysFixed.systems;
  if (sysFixed.fix) fixes.push(sysFixed.fix);

  // Entities
  const ensured = ensurePlayer(base.scene.entities);
  base.scene.entities = ensured.entities;
  if (ensured.fix) fixes.push(ensured.fix);

  const renamed = renameDuplicateIds(base.scene.entities);
  base.scene.entities = renamed.entities;
  if (renamed.fix) fixes.push(renamed.fix);

  const clamped = clampEntitiesToWorld(base.scene.entities);
  base.scene.entities = clamped.entities;
  if (clamped.fix) fixes.push(clamped.fix);

  if (!base.visual) {
    fixes.push({
      code: "FILL_DEFAULTS",
      message: "visual ausente → será preenchido na normalização.",
    });
  }

  return { spec: base, fixes, issues: detected };
}

export type { OrdaxSpecIssue, OrdaxSpecFix } from "./types";
