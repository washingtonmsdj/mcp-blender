import type { OrdaxBackgroundLayer, OrdaxEntity, OrdaxGameType, OrdaxSpec, OrdaxVisualTheme } from "@/lib/ordax/types";

const DEFAULT_THEME: Required<Pick<OrdaxVisualTheme, "background" | "primary" | "accent" | "font">> = {
  background: "hsl(0, 0%, 4%)",
  primary: "hsl(200, 80%, 50%)",
  accent: "hsl(300, 70%, 50%)",
  font: "ui-sans-serif, system-ui, sans-serif",
};

type HslObj = { h: number; s: number; l: number };
function isHslObj(v: unknown): v is HslObj {
  return !!v && typeof v === "object" &&
    typeof (v as any).h === "number" &&
    typeof (v as any).s === "number" &&
    typeof (v as any).l === "number";
}

function toHslString(v: unknown, fallback: string): string {
  if (typeof v === "string") return v;
  if (isHslObj(v)) return `hsl(${v.h}, ${v.s}%, ${v.l}%)`;
  return fallback;
}

function defaultLayersForGameType(gameType: OrdaxSpec["gameType"]): OrdaxBackgroundLayer[] {
  // These defaults are what make the system “template-less”: a single runtime + smart defaults.
  switch (gameType) {
    case "shooter":
      return [
        { type: "nebula", parallax: 0.15 },
        { type: "starfield", density: 220, speedY: 35, parallax: 0.35 },
      ];
    case "racing":
      return [{ type: "gradient", parallax: 0 }];
    case "platformer":
      return [{ type: "gradient", parallax: 0.1 }];
    case "topdown":
      return [{ type: "solid", parallax: 0 }];
    case "puzzle":
      return [{ type: "solid", parallax: 0 }];
    case "sports":
      return [{ type: "gradient", parallax: 0 }];
    default:
      return [{ type: "solid", parallax: 0 }];
  }
}

function ensureShooterBasics(entities: OrdaxEntity[]): OrdaxEntity[] {
  const out = [...entities];

  // Ensure a spawner exists so the loop is never “empty”.
  const hasSpawner = out.some((e) => e.type === "spawner" || e.id === "spawner");
  if (!hasSpawner) {
    out.push({
      id: "spawner",
      type: "spawner",
      x: 400,
      y: 40,
      w: 300,
      h: 40,
      props: {
        // enemies/second
        spawnRate: 1.2,
        spawnType: "enemy",
      },
    });
  }

  // Ensure player has shooter-friendly defaults.
  const playerIdx = out.findIndex((e) => e.id === "player" || e.type === "player");
  if (playerIdx >= 0) {
    const p = out[playerIdx];
    out[playerIdx] = {
      ...p,
      props: {
        ...(p.props ?? {}),
        health: (p.props as any)?.health ?? 100,
        speed: (p.props as any)?.speed ?? 260,
        // shots/second
        fireRate: (p.props as any)?.fireRate ?? 7,
        bulletSpeed: (p.props as any)?.bulletSpeed ?? 520,
      },
    };
  }

  return out;
}

function normalizeSystems(gameType: OrdaxSpec["gameType"], systems: string[]): string[] {
  const set = new Set(systems ?? []);

  // Always useful in our runtime
  set.add("CameraSystem");
  set.add("UISystem");

  // Gameplay defaults
  if (gameType === "shooter") {
    set.add("CollisionSystem");
    set.add("SpawnerSystem");
    set.add("ScoreSystem");
    set.add("ParticleSystem");
    // P0 shooter needs timers (powerups), AI behaviors, and audio hooks.
    set.add("TimerSystem");
    set.add("AISystem");
    set.add("AudioSystem");
  }

  if (gameType === "platformer") {
    set.add("PhysicsSystem");
    set.add("CollisionSystem");
  }

  return Array.from(set);
}

function ensureShooterAudioDefaults(spec: OrdaxSpec): OrdaxSpec {
  const hasAudioSystem = (spec.systems ?? []).includes("AudioSystem");
  if (!hasAudioSystem) return spec;

  // If audio block is missing, provide safe defaults.
  // NOTE: assets may not exist yet; runtime will fail gracefully.
  const audio = {
    ...(spec.audio ?? {}),
    music: spec.audio?.music ?? "/audio/bgm.mp3",
    sounds: {
      collision: spec.audio?.sounds?.collision ?? "/audio/hit.wav",
      score: spec.audio?.sounds?.score ?? "/audio/coin.wav",
      gameOver: spec.audio?.sounds?.gameOver ?? "/audio/gameover.wav",
      jump: spec.audio?.sounds?.jump ?? "/audio/jump.wav",
      shoot: spec.audio?.sounds?.shoot ?? "/audio/shoot.wav",
      ...(spec.audio?.sounds ?? {}),
    },
  } satisfies OrdaxSpec["audio"];

  return {
    ...spec,
    audio,
  };
}

/**
 * Makes the AI output robust: even if the model forgets visual/systems,
 * we still render a “real game” (background + parallax + coherent systems).
 */
export function normalizeOrdaxSpec(input: OrdaxSpec): OrdaxSpec {
  // Accept “alternate schema” outputs from the model and adapt them to OrdaxSpec.
  // IMPORTANT: even if the model returns something that *looks* like OrdaxSpec,
  // we still pass through the adapter to guarantee invariants (player, non-empty scene).
  const adapted = adaptToOrdaxSpec(input as unknown as any);
  const gameType = adapted.gameType ?? "unknown";
  const rawTheme = adapted.visual?.theme ?? {};
  const theme: OrdaxVisualTheme = {
    ...DEFAULT_THEME,
    ...(rawTheme as any),
    // Accept both string and {h,s,l} outputs from the model.
    background: toHslString((rawTheme as any).background, DEFAULT_THEME.background),
    primary: toHslString((rawTheme as any).primary, DEFAULT_THEME.primary),
    secondary: toHslString((rawTheme as any).secondary, DEFAULT_THEME.primary),
    accent: toHslString((rawTheme as any).accent, DEFAULT_THEME.accent),
  };

  const layers = adapted.visual?.background?.layers?.length
    ? adapted.visual.background.layers
    : defaultLayersForGameType(gameType);

  // Ensure we never end up with “no background” visually.
  const visual = {
    theme,
    background: {
      layers,
    },
  };

  // Ensure we always have at least 1 entity and that a player exists.
  let ensuredEntities = ensurePlayerEntity(adapted.scene?.entities ?? []);

  // Shooter must never be “empty”: we guarantee a spawner + player fire defaults.
  if (gameType === "shooter") {
    ensuredEntities = ensureShooterBasics(ensuredEntities);
  }

  const normalized: OrdaxSpec = {
    ...adapted,
    systems: normalizeSystems(gameType, adapted.systems ?? []),
    visual,
    scene: {
      gravity: adapted.scene?.gravity ?? { x: 0, y: gameType === "platformer" ? 500 : 0 },
      entities: ensuredEntities,
    },
  };

  // P0 shooter default audio wiring.
  if (normalized.gameType === "shooter") {
    return ensureShooterAudioDefaults(normalized);
  }

  return normalized;
}

// ------------------------
// Adapter (AI output → OrdaxSpec)
// ------------------------

type AnyObj = Record<string, any>;

function isOrdaxEntityLike(v: any): v is OrdaxEntity {
  return !!v && typeof v === "object" &&
    typeof v.id === "string" &&
    typeof v.type === "string" &&
    typeof v.x === "number" &&
    typeof v.y === "number" &&
    typeof v.w === "number" &&
    typeof v.h === "number";
}

function normalizeExistingEntities(entities: any[]): OrdaxEntity[] {
  const out: OrdaxEntity[] = [];
  for (const e of entities) {
    if (!isOrdaxEntityLike(e)) continue;
    out.push({
      id: e.id,
      type: e.type,
      x: e.x,
      y: e.y,
      w: Math.max(8, e.w),
      h: Math.max(8, e.h),
      // Preserve props/sprite if already provided by the model.
      props: (e.props && typeof e.props === "object") ? e.props : undefined,
      sprite: (e.sprite && typeof e.sprite === "object" && typeof e.sprite.url === "string")
        ? {
            url: e.sprite.url,
            frameWidth: Number(e.sprite.frameWidth ?? 0) || 0,
            frameHeight: Number(e.sprite.frameHeight ?? 0) || 0,
            currentAnimation: typeof e.sprite.currentAnimation === "string" ? e.sprite.currentAnimation : undefined,
          }
        : undefined,
    });
  }
  return out;
}

function guessGameTypeFromText(text: string): OrdaxGameType {
  const t = (text || "").toLowerCase();
  if (t.includes("plataforma") || t.includes("platform")) return "platformer";
  if (t.includes("corrida") || t.includes("racing")) return "racing";
  if (t.includes("puzzle") || t.includes("quebra")) return "puzzle";
  if (t.includes("top-down") || t.includes("topdown")) return "topdown";
  if (t.includes("nave") || t.includes("shooter") || t.includes("tiro") || t.includes("asteroid")) return "shooter";
  if (t.includes("sports") || t.includes("futebol") || t.includes("basquete")) return "sports";
  return "unknown";
}

function mapBackgroundLayers(layers: any[]): OrdaxBackgroundLayer[] {
  if (!Array.isArray(layers) || layers.length === 0) return [{ type: "solid", parallax: 0 }];

  const out: OrdaxBackgroundLayer[] = [];
  for (const l of layers) {
    const t = String(l?.type ?? "").toLowerCase();
    const parallax = typeof l?.parallax === "number" ? l.parallax : undefined;

    // Our runtime supports: starfield | gradient | nebula | solid
    if (t === "particles" || t === "starfield" || t === "stars") {
      const density = l?.config?.count ?? l?.density;
      out.push({ type: "starfield", parallax, density: typeof density === "number" ? density : 220, speedY: 35 });
      continue;
    }

    if (t === "gradient") {
      out.push({ type: "gradient", parallax: parallax ?? 0.1 });
      continue;
    }

    if (t === "nebula") {
      out.push({ type: "nebula", parallax: parallax ?? 0.15 });
      continue;
    }

    // “color”/unknown -> solid
    out.push({ type: "solid", parallax: parallax ?? 0 });
  }

  return out.length ? out : [{ type: "solid", parallax: 0 }];
}

function mapSystems(systems: any): string[] {
  const list = Array.isArray(systems) ? systems : [];
  const set = new Set<string>();

  for (const s of list) {
    const type = String(s?.type ?? s ?? "").toLowerCase();
    if (type.includes("physics") || type.includes("movement")) set.add("PhysicsSystem");
    if (type.includes("collision")) set.add("CollisionSystem");
    if (type.includes("particle")) set.add("ParticleSystem");
    if (type.includes("score")) set.add("ScoreSystem");
    if (type.includes("audio")) set.add("AudioSystem");
    if (type.includes("camera")) set.add("CameraSystem");
    if (type.includes("ui") || type.includes("hud")) set.add("UISystem");
    if (type.includes("timer")) set.add("TimerSystem");
    if (type.includes("ai")) set.add("AISystem");
    if (type.includes("anim")) set.add("AnimationSystem");
    if (type.includes("spawn")) set.add("SpawnerSystem");
  }

  return Array.from(set);
}

function mapEntities(entities: any[]): OrdaxEntity[] {
  if (!Array.isArray(entities)) return [];

  const out: OrdaxEntity[] = [];
  for (const e of entities) {
    const idRaw = String(e?.id ?? "entity");
    const typeRaw = String(e?.type ?? "entity");
    const c = (e?.components ?? e?.config ?? {}) as AnyObj;
    const pos = c.position ?? c.pos ?? {};
    const x = typeof pos.x === "number" ? pos.x : typeof e?.x === "number" ? e.x : 400;
    const y = typeof pos.y === "number" ? pos.y : typeof e?.y === "number" ? e.y : 300;

    // Size heuristics
    const sprite = c.sprite ?? {};
    const size = typeof sprite.size === "number" ? sprite.size : undefined;
    const collider = c.collider ?? {};
    const radius = typeof collider.radius === "number" ? collider.radius : undefined;
    const w = typeof e?.w === "number" ? e.w : typeof size === "number" ? size : typeof radius === "number" ? radius * 2 : 32;
    const h = typeof e?.h === "number" ? e.h : typeof size === "number" ? size : typeof radius === "number" ? radius * 2 : 32;

    const hasInput = !!c.input;
    const isPlayer = hasInput || idRaw.includes("player") || typeRaw === "player";

    out.push({
      id: isPlayer ? "player" : idRaw,
      type: isPlayer ? "player" : typeRaw,
      x,
      y,
      w: Math.max(8, w),
      h: Math.max(8, h),
      props: {
        ...(e?.props ?? {}),
        ...(hasInput ? { speed: 260 } : null),
      },
    });
  }

  // Ensure we always have a player for camera/controls.
  if (!out.some((e) => e.id === "player" || e.type === "player")) {
    out.unshift({ id: "player", type: "player", x: 400, y: 500, w: 32, h: 32, props: { health: 100, speed: 260 } });
  }

  // If there is a spawner with interval/entity_template, convert to runtime-friendly props
  for (const raw of entities) {
    if (String(raw?.type ?? "").toLowerCase() !== "spawner") continue;
    const interval = raw?.config?.interval;
    const template = raw?.config?.entity_template;
    const spawnType = template?.components?.sprite?.shape === "polygon" ? "asteroid" : "enemy";
    const spawnRate = typeof interval === "number" && interval > 0 ? 1 / interval : 1.5;
    const idx = out.findIndex((e) => e.type === "spawner" || e.id === raw?.id);
    if (idx >= 0) {
      out[idx] = {
        ...out[idx],
        type: "spawner",
        props: {
          ...(out[idx].props ?? {}),
          spawnRate,
          spawnType,
        },
      };
    }
  }

  return out;
}

function ensurePlayerEntity(entities: OrdaxEntity[]): OrdaxEntity[] {
  const out = Array.isArray(entities) ? [...entities] : [];
  const hasPlayer = out.some((e) => e && (e.id === "player" || e.type === "player"));
  if (!hasPlayer) {
    out.unshift({
      id: "player",
      type: "player",
      x: 400,
      y: 500,
      w: 32,
      h: 32,
      props: { health: 100, speed: 260 },
    });
  }
  return out;
}

function adaptToOrdaxSpec(input: AnyObj): OrdaxSpec {
  // NOTE: We intentionally do NOT early-return here, because many “almost valid” specs
  // still miss invariants our runtime expects (like a player entity).

  const title = input?.title ?? input?.metadata?.name ?? "Jogo";
  const description = input?.description ?? input?.metadata?.description ?? "";
  let gameType: OrdaxGameType = input?.gameType ?? guessGameTypeFromText(`${title} ${description}`);

  const layersRaw = input?.visual?.background?.layers ?? input?.visual?.backgroundLayers;
  const adaptedLayers = mapBackgroundLayers(layersRaw);

  // If the model forgot to set gameType but clearly generated “space” layers, infer shooter.
  if (
    gameType === "unknown" &&
    adaptedLayers.some((l) => l.type === "starfield" || l.type === "nebula")
  ) {
    gameType = "shooter";
  }

  // Some model variants send visual.background.layers with unsupported shapes (color/particles).
  const visual = {
    theme: input?.visual?.theme ?? {},
    background: { layers: adaptedLayers },
  } as OrdaxSpec["visual"];

  const entitiesRaw = input?.scene?.entities ?? input?.entities ?? [];
  const sceneEntities = ensurePlayerEntity(
    Array.isArray(entitiesRaw) && entitiesRaw.every(isOrdaxEntityLike)
      ? normalizeExistingEntities(entitiesRaw)
      : mapEntities(entitiesRaw)
  );

  const systems = Array.isArray(input?.systems)
    ? input.systems.every((s: any) => typeof s === "string")
      ? (input.systems as string[])
      : mapSystems(input.systems)
    : [];

  return {
    gameType,
    title,
    description,
    systems,
    visual,
    scene: {
      gravity: input?.scene?.gravity ?? { x: 0, y: gameType === "platformer" ? 500 : 0 },
      entities: sceneEntities,
    },
  };
}
