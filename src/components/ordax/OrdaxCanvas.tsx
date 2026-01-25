import { forwardRef, useEffect, useImperativeHandle, useMemo, useRef, useState } from "react";
import type { OrdaxEntity, OrdaxSpec } from "@/lib/ordax/types";
import { PhysicsSystem } from "@/lib/ordax/systems/PhysicsSystem";
import { CollisionSystem } from "@/lib/ordax/systems/CollisionSystem";
import { ParticleSystem } from "@/lib/ordax/systems/ParticleSystem";
import { ScoreSystem } from "@/lib/ordax/systems/ScoreSystem";
import { AudioSystem } from "@/lib/ordax/systems/AudioSystem";
import { CameraSystem } from "@/lib/ordax/systems/CameraSystem";
import { UISystem } from "@/lib/ordax/systems/UISystem";
import { TimerSystem } from "@/lib/ordax/systems/TimerSystem";
import { AISystem } from "@/lib/ordax/systems/AISystem";
import { AnimationSystem } from "@/lib/ordax/systems/AnimationSystem";
import { toast } from "sonner";

type Props = {
  spec?: OrdaxSpec;
  running: boolean;
};

export type OrdaxCanvasHandle = {
  reset: () => void;
  getDebugInfo: () => DebugInfo;
};

type DebugInfo = {
  systems: {
    physics: boolean;
    collision: boolean;
    particles: boolean;
    particleCount: number;
    score: boolean;
    ai: boolean;
    camera: boolean;
    audio: boolean;
    ui: boolean;
    timer: boolean;
    animation: boolean;
  };
  entities: {
    total: number;
    spawned: number;
  };
  player: {
    health: number;
    x: number;
    y: number;
  } | null;
  score: {
    current: number;
    multiplier: number;
    combo: number;
  } | null;
};

type Keys = {
  ArrowUp?: boolean;
  ArrowDown?: boolean;
  ArrowLeft?: boolean;
  ArrowRight?: boolean;
  w?: boolean;
  a?: boolean;
  s?: boolean;
  d?: boolean;
  " "?: boolean;
};

const WORLD = { w: 800, h: 600 };

function hslToHsla(hsl: string, alpha: number) {
  // Converts "hsl(h, s%, l%)" -> "hsla(h, s%, l%, a)".
  // If it's already hsla(...) or not hsl, just return as-is.
  const a = Math.max(0, Math.min(1, alpha));
  const t = (hsl || "").trim();
  if (t.startsWith("hsla(")) return t;

  // Accept Tailwind-style HSL triplet strings: "210 100% 50%"
  // (common when someone accidentally passes CSS var content).
  const triplet = t.match(/^(-?\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)%\s+(\d+(?:\.\d+)?)%$/);
  if (triplet) {
    const [, h, s, l] = triplet;
    return `hsla(${h}, ${s}%, ${l}%, ${a})`;
  }

  if (!t.startsWith("hsl(")) return t;
  return t.replace(/^hsl\(/, "hsla(").replace(/\)\s*$/, `, ${a})`);
}

function normalizeCssColor(input: unknown, fallback: string): string {
  if (typeof input !== "string") return fallback;
  const t = input.trim();
  if (!t) return fallback;
  if (t.startsWith("hsl(") || t.startsWith("hsla(") || t.startsWith("#") || t.startsWith("rgb(")) return t;
  // Tailwind-style HSL triplet
  const triplet = t.match(/^(-?\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)%\s+(\d+(?:\.\d+)?)%$/);
  if (triplet) {
    const [, h, s, l] = triplet;
    return `hsl(${h}, ${s}%, ${l}%)`;
  }
  return fallback;
}

type Spawned = {
  id: string;
  type: string;
  x: number;
  y: number;
  w: number;
  h: number;
  vy: number;
  vx?: number;
  hp?: number;
  variant?: "scout" | "tank" | "sniper";
  kind?: "shield" | "spread";
  dead?: boolean;
};

type Bullet = {
  id: string;
  type: "bullet";
  x: number;
  y: number;
  w: number;
  h: number;
  vx: number;
  vy: number;
  dead?: boolean;
};

function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(max, n));
}

function isFiniteNumber(n: unknown): n is number {
  return typeof n === "number" && Number.isFinite(n);
}

export const OrdaxCanvas = forwardRef<OrdaxCanvasHandle, Props>(({ spec, running }, ref) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const keysRef = useRef<Keys>({});
  const resetRef = useRef<() => void>(() => undefined);
  const playerRef = useRef<{ x: number; y: number; health: number } | null>(null);
  const shieldRef = useRef<{ value: number; max: number; regenPerSec: number } | null>(null);
  const spawnedRef = useRef<Spawned[]>([]);
  const bulletsRef = useRef<Bullet[]>([]);
  const spawnTimerRef = useRef<number>(0);
  const powerupTimerRef = useRef<number>(0);
  const fireCooldownRef = useRef<number>(0);
  const buffsRef = useRef<{ shield: number; spread: number }>({ shield: 0, spread: 0 });
  const lastTRef = useRef<number>(0);
  const gameOverRef = useRef(false);

  const fallbackAudioRef = useRef<AudioContext | null>(null);

  const playFallbackSfx = (kind: "shoot" | "hit" | "power" | "score" | "gameover") => {
    try {
      const Ctx = (window.AudioContext || (window as any).webkitAudioContext) as typeof AudioContext | undefined;
      if (!Ctx) return;
      if (!fallbackAudioRef.current) fallbackAudioRef.current = new Ctx();
      const ac = fallbackAudioRef.current;
      if (ac.state === "suspended") void ac.resume();

      const osc = ac.createOscillator();
      const gain = ac.createGain();

      const now = ac.currentTime;
      const freq =
        kind === "shoot" ? 820 :
        kind === "hit" ? 140 :
        kind === "power" ? 520 :
        kind === "score" ? 660 :
        90;

      osc.type = kind === "hit" || kind === "gameover" ? "sawtooth" : "triangle";
      osc.frequency.setValueAtTime(freq, now);

      gain.gain.setValueAtTime(0.0001, now);
      gain.gain.exponentialRampToValueAtTime(0.12, now + 0.01);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + (kind === "gameover" ? 0.25 : 0.09));

      osc.connect(gain);
      gain.connect(ac.destination);
      osc.start(now);
      osc.stop(now + (kind === "gameover" ? 0.26 : 0.1));
    } catch {
      // ignore
    }
  };

  const playSfx = (id: "shoot" | "collision" | "score" | "gameOver" | "powerup") => {
    if (hasAudioSystem) {
      audioSystemRef.current.playSound(id);
      return;
    }
    // Fallback procedural (no assets required)
    if (id === "shoot") playFallbackSfx("shoot");
    else if (id === "collision") playFallbackSfx("hit");
    else if (id === "score") playFallbackSfx("score");
    else if (id === "gameOver") playFallbackSfx("gameover");
    else playFallbackSfx("power");
  };
  
  // Sprite loading
  const [spritesLoaded, setSpritesLoaded] = useState(false);
  const spritesRef = useRef<Map<string, HTMLImageElement>>(new Map());
  
  // System instances
  const physicsSystemRef = useRef<PhysicsSystem>(new PhysicsSystem());
  const collisionSystemRef = useRef<CollisionSystem>(new CollisionSystem());
  const particleSystemRef = useRef<ParticleSystem>(new ParticleSystem());
  const scoreSystemRef = useRef<ScoreSystem>(new ScoreSystem());
  const audioSystemRef = useRef<AudioSystem>(new AudioSystem());
  const cameraSystemRef = useRef<CameraSystem>(new CameraSystem(WORLD.w, WORLD.h));
  const uiSystemRef = useRef<UISystem>(new UISystem());
  const timerSystemRef = useRef<TimerSystem>(new TimerSystem());
  const aiSystemRef = useRef<AISystem>(new AISystem());
  const animationSystemRef = useRef<AnimationSystem>(new AnimationSystem());

  const scene = spec?.scene ?? { gravity: { x: 0, y: 0 }, entities: [] as OrdaxEntity[] };
  const entities = scene.entities;

  const initialPlayer = useMemo(
    () => entities.find((e) => e.type === "player" || e.id === "player"),
    [entities]
  );
  const spawners = useMemo(() => entities.filter((e) => e.type === "spawner"), [entities]);

  const hasSpawner = spawners.length > 0;
  const visual = spec?.visual;
  const bgLayers = visual?.background?.layers ?? [];
  const theme = visual?.theme;
  const gameType = spec?.gameType ?? "unknown";
  
  // Check which systems are enabled
  const systems = spec?.systems ?? [];
  const hasPhysicsSystem = systems.includes("PhysicsSystem");
  const hasCollisionSystem = systems.includes("CollisionSystem");
  const hasParticleSystem = systems.includes("ParticleSystem");
  const hasScoreSystem = systems.includes("ScoreSystem");
  const hasAudioSystem = systems.includes("AudioSystem");
  const hasCameraSystem = systems.includes("CameraSystem");
  const hasUISystem = systems.includes("UISystem");
  const hasTimerSystem = systems.includes("TimerSystem");
  const hasAISystem = systems.includes("AISystem");
  const hasAnimationSystem = systems.includes("AnimationSystem");

  // Load sprites
  useEffect(() => {
    if (!spec) {
      spritesRef.current = new Map();
      setSpritesLoaded(false);
      return;
    }
    const loadSprites = async () => {
      const sprites = new Map<string, HTMLImageElement>();
      const promises: Promise<void>[] = [];

      for (const entity of entities) {
        if (entity.sprite?.url) {
          const promise = new Promise<void>((resolve, reject) => {
            const img = new Image();
            img.onload = () => {
              sprites.set(entity.id, img);
              resolve();
            };
            img.onerror = () => {
              console.warn(`Failed to load sprite: ${entity.sprite?.url}`);
              resolve(); // Continue even if sprite fails
            };
            img.src = entity.sprite.url;
          });
          promises.push(promise);
        }
      }

      await Promise.all(promises);
      spritesRef.current = sprites;
      setSpritesLoaded(true);
    };

    loadSprites();
  }, [spec, entities]);

  // Load audio
  useEffect(() => {
    if (!spec || !hasAudioSystem || !spec.audio) return;

    const audio = audioSystemRef.current;

    // Load music
    if (spec.audio.music) {
      audio.loadMusic("bgm", spec.audio.music).catch((e) => {
        console.warn("Failed to load music:", e);
      });
    }

    // Load sounds
    if (spec.audio.sounds) {
      Object.entries(spec.audio.sounds).forEach(([key, url]) => {
        if (url) {
          audio.loadSound(key, url).catch((e) => {
            console.warn(`Failed to load sound ${key}:`, e);
          });
        }
      });
    }
  }, [spec, hasAudioSystem]);

  const reset = () => {
    if (!spec) return;
    gameOverRef.current = false;
    if (initialPlayer) {
      const shieldMax = (initialPlayer.props?.shield as number | undefined) ?? 0;
      const shieldRegen = (initialPlayer.props?.shieldRegen as number | undefined) ?? 0;

      playerRef.current = { 
        x: initialPlayer.x, 
        y: initialPlayer.y,
        health: (initialPlayer.props?.health as number) ?? 100
      };

      shieldRef.current = shieldMax > 0
        ? { value: shieldMax, max: shieldMax, regenPerSec: Math.max(0, shieldRegen) }
        : null;
    }
    spawnedRef.current = [];
    bulletsRef.current = [];
    spawnTimerRef.current = 0;
    powerupTimerRef.current = 0;
    fireCooldownRef.current = 0;
    buffsRef.current = { shield: 0, spread: 0 };
    lastTRef.current = performance.now();
    
    // Reset systems
    if (hasScoreSystem) {
      scoreSystemRef.current.reset();
      scoreSystemRef.current.loadHighScore();
    }
    if (hasParticleSystem) {
      particleSystemRef.current.clear();
    }
    if (hasTimerSystem) {
      timerSystemRef.current.clear();
    }
    if (hasPhysicsSystem) {
      physicsSystemRef.current.clear();
    }
    
    // Setup physics for player
    if (hasPhysicsSystem && initialPlayer) {
      physicsSystemRef.current.register(initialPlayer.id, 1, 0.2, 0.5);
      physicsSystemRef.current.setMaxVelocity(initialPlayer.id, 400, 600);
    }
    
    // Setup camera follow
    if (hasCameraSystem && initialPlayer) {
      cameraSystemRef.current.follow("player", 5);
      cameraSystemRef.current.setBounds(0, 0, WORLD.w, WORLD.h);
    }
    
    // Play music
    if (hasAudioSystem && spec?.audio?.music) {
      audioSystemRef.current.playMusic("bgm", true);
    }
  };

  // Keep an up-to-date reset reference (used by global key handlers).
  useEffect(() => {
    resetRef.current = reset;
  });

  useImperativeHandle(ref, () => ({ 
    reset,
    getDebugInfo: () => ({
      systems: {
        physics: hasPhysicsSystem,
        collision: hasCollisionSystem,
        particles: hasParticleSystem,
        particleCount: hasParticleSystem ? particleSystemRef.current.getCount() : 0,
        score: hasScoreSystem,
        ai: hasAISystem,
        camera: hasCameraSystem,
        audio: hasAudioSystem,
        ui: hasUISystem,
        timer: hasTimerSystem,
        animation: hasAnimationSystem,
      },
      entities: {
        total: entities.length,
        spawned: spawnedRef.current.length,
      },
      player: playerRef.current ? {
        health: playerRef.current.health,
        x: Math.round(playerRef.current.x),
        y: Math.round(playerRef.current.y),
      } : null,
      score: hasScoreSystem ? {
        current: scoreSystemRef.current.getScore(),
        multiplier: scoreSystemRef.current.getMultiplier(),
        combo: scoreSystemRef.current.getCombo(),
      } : null,
    })
  }), [initialPlayer, hasPhysicsSystem, hasCollisionSystem, hasParticleSystem, hasScoreSystem, hasAISystem, hasCameraSystem, hasAudioSystem, hasUISystem, hasTimerSystem, hasAnimationSystem, entities, spec]);

  useEffect(() => {
    if (!spec) return;
    reset();
    
    // Setup collision callbacks
    if (hasCollisionSystem) {
      const collision = collisionSystemRef.current;

      const applyDamage = (amount: number) => {
        if (!playerRef.current) return;

        // Shield points (from spec) absorb damage first.
        if (shieldRef.current && shieldRef.current.value > 0) {
          const absorbed = Math.min(shieldRef.current.value, amount);
          shieldRef.current.value = Math.max(0, shieldRef.current.value - absorbed);
          playSfx("collision");
          amount = amount - absorbed;
          if (amount <= 0) return;
        }

        // Timed shield buff (powerup) absorbs a hit.
        if (buffsRef.current.shield > 0) {
          buffsRef.current.shield = 0;
          playSfx("collision");
          return;
        }

        playerRef.current.health -= amount;
        if (playerRef.current.health <= 0) {
          toast.error("💥 Game Over!");
          playerRef.current.health = 0;
          gameOverRef.current = true;
          playSfx("gameOver");
        } else {
          playSfx("collision");
        }
      };
      
      // Player vs Enemy/Asteroid collision
      collision.on("player", "enemy", (player, enemy) => {
        const spawned = spawnedRef.current.find(s => s.id === enemy.id);
        if (spawned && !spawned.dead) {
          spawned.dead = true;
          
          // Damage player (shield absorbs one hit)
          applyDamage(20);
          
          // Particles
          if (hasParticleSystem) {
            particleSystemRef.current.emit(enemy.x, enemy.y, 20, {
              life: 0.5,
              speed: 150,
              size: 3,
              color: (theme?.accent && typeof theme.accent === 'string') ? theme.accent : "hsl(300, 70%, 50%)",
              spread: Math.PI * 2,
              direction: 0,
            });
          }
          
          // Camera shake
          if (hasCameraSystem) {
            cameraSystemRef.current.shake(10, 200);
          }
        }
      });
      
      collision.on("player", "asteroid", (player, asteroid) => {
        const spawned = spawnedRef.current.find(s => s.id === asteroid.id);
        if (spawned && !spawned.dead) {
          spawned.dead = true;
          
          // Damage player (shield absorbs one hit)
          applyDamage(10);
          
          // Particles
          if (hasParticleSystem) {
            particleSystemRef.current.emit(asteroid.x, asteroid.y, 15, {
              life: 0.8,
              speed: 100,
              size: 4,
              color: "rgba(150, 150, 150, 0.8)",
              spread: Math.PI * 2,
              direction: 0,
            });
          }
          
          // Score
          if (hasScoreSystem) {
            scoreSystemRef.current.addScore(10, "asteroid");
            playSfx("score");
          }
          
          // Camera shake
          if (hasCameraSystem) {
            cameraSystemRef.current.shake(5, 150);
          }
        }
      });

      // Bullet collisions (shooter)
      collision.on("bullet", "enemy", (bullet, enemy) => {
        const b = bulletsRef.current.find((x) => x.id === bullet.id);
        const s = spawnedRef.current.find((x) => x.id === enemy.id);
        if (b && !b.dead) b.dead = true;

        // Tank enemies take 2 hits
        if (s && !s.dead) {
          if (s.variant === "tank" && (s.hp ?? 2) > 1) {
            s.hp = (s.hp ?? 2) - 1;
          } else {
            s.dead = true;
          }
        }

        if (hasParticleSystem) {
          particleSystemRef.current.emit(enemy.x, enemy.y, 18, {
            life: 0.5,
            speed: 180,
            size: 3,
            color: (theme?.accent && typeof theme.accent === "string") ? theme.accent : "hsl(300, 70%, 50%)",
            spread: Math.PI * 2,
            direction: 0,
          });
        }

        if (hasScoreSystem) {
          if (s?.dead) scoreSystemRef.current.addScore(25, "enemy");
          playSfx("score");
        }

        if (hasCameraSystem) cameraSystemRef.current.shake(6, 140);
      });

      collision.on("bullet", "asteroid", (bullet, asteroid) => {
        const b = bulletsRef.current.find((x) => x.id === bullet.id);
        const s = spawnedRef.current.find((x) => x.id === asteroid.id);
        if (b && !b.dead) b.dead = true;
        if (s && !s.dead) s.dead = true;

        if (hasParticleSystem) {
          particleSystemRef.current.emit(asteroid.x, asteroid.y, 14, {
            life: 0.6,
            speed: 140,
            size: 3,
            color: "rgba(200, 200, 200, 0.75)",
            spread: Math.PI * 2,
            direction: 0,
          });
        }

        if (hasScoreSystem) {
          scoreSystemRef.current.addScore(10, "asteroid");
          playSfx("score");
        }
      });

      // Powerups
      collision.on("player", "powerup", (player, powerup) => {
        const s = spawnedRef.current.find((x) => x.id === powerup.id);
        if (!s || s.dead) return;
        s.dead = true;

        if (s.kind === "shield") buffsRef.current.shield = 6;
        if (s.kind === "spread") buffsRef.current.spread = 6;
        playSfx("powerup");

        if (hasParticleSystem) {
          const primaryColor = (theme?.primary && typeof theme.primary === "string") ? theme.primary : "hsl(200, 80%, 50%)";
          particleSystemRef.current.emit(s.x, s.y, 22, {
            life: 0.7,
            speed: 180,
            size: 3,
            color: primaryColor,
            spread: Math.PI * 2,
            direction: 0,
          });
        }
      });
    }
    
    // Setup AI for enemies
    if (hasAISystem) {
      const enemies = entities.filter(e => e.type === "enemy");
      enemies.forEach(enemy => {
        aiSystemRef.current.register(enemy.id, "chase", 80);
      });
    }
  }, [spec, hasPhysicsSystem, hasCollisionSystem, hasParticleSystem, hasScoreSystem, hasCameraSystem, hasAISystem, hasAudioSystem, theme, entities]);

  useEffect(() => {
    const onDown = (e: KeyboardEvent) => {
      // Allow quick restart after game over.
      if (gameOverRef.current && (e.key === "r" || e.key === "R" || e.key === "Enter")) {
        e.preventDefault();
        // Clear key state to avoid sticky movement after restart.
        keysRef.current = {};
        resetRef.current();
        return;
      }
      keysRef.current[e.key as keyof Keys] = true;
    };
    const onUp = (e: KeyboardEvent) => {
      keysRef.current[e.key as keyof Keys] = false;
    };
    window.addEventListener("keydown", onDown);
    window.addEventListener("keyup", onUp);
    return () => {
      window.removeEventListener("keydown", onDown);
      window.removeEventListener("keyup", onUp);
    };
  }, []);

  useEffect(() => {
    let raf = 0;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // If we don't have a spec yet, just clear the canvas.
    if (!spec) {
      const drawEmpty = () => {
        const rect = canvas.getBoundingClientRect();
        const dpr = Math.max(1, Math.floor(window.devicePixelRatio || 1));
        const w = Math.max(1, Math.floor(rect.width));
        const h = Math.max(1, Math.floor(rect.height));
        if (canvas.width !== w * dpr || canvas.height !== h * dpr) {
          canvas.width = w * dpr;
          canvas.height = h * dpr;
        }
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        ctx.fillStyle = "hsl(0, 0%, 4%)";
        ctx.fillRect(0, 0, w, h);
      };
      drawEmpty();
      return;
    }

    let stars: { x: number; y: number; s: number }[] = [];
    const initStars = (count: number) => {
      stars = [];
      for (let i = 0; i < count; i++) {
        stars.push({ x: Math.random() * WORLD.w, y: Math.random() * WORLD.h, s: 1 + Math.random() * 2 });
      }
    };
    if (bgLayers.some((l) => l.type === "starfield")) {
      const density = bgLayers.find((l) => l.type === "starfield")?.density ?? 200;
      initStars(density);
    }

    const draw = (t: number) => {
      const dt = Math.min(0.05, (t - lastTRef.current) / 1000);
      lastTRef.current = t;

      // Fit canvas to container
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.max(1, Math.floor(window.devicePixelRatio || 1));
      const w = Math.max(1, Math.floor(rect.width));
      const h = Math.max(1, Math.floor(rect.height));
      if (canvas.width !== w * dpr || canvas.height !== h * dpr) {
        canvas.width = w * dpr;
        canvas.height = h * dpr;
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      const scale = Math.min(w / WORLD.w, h / WORLD.h);
      const ox = (w - WORLD.w * scale) / 2;
      const oy = (h - WORLD.h * scale) / 2;

      const worldPxW = WORLD.w * scale;
      const worldPxH = WORLD.h * scale;

      // Background
       const bgColor = normalizeCssColor(theme?.background, "hsl(0, 0%, 4%)");
      ctx.fillStyle = bgColor;
      ctx.fillRect(0, 0, w, h);

      // Subtle letterbox shading so the world frame feels intentional.
      ctx.fillStyle = "rgba(0,0,0,0.25)";
      ctx.fillRect(0, 0, w, Math.max(0, oy));
      ctx.fillRect(0, oy + WORLD.h * scale, w, Math.max(0, h - (oy + WORLD.h * scale)));
      ctx.fillRect(0, oy, Math.max(0, ox), WORLD.h * scale);
      ctx.fillRect(ox + WORLD.w * scale, oy, Math.max(0, w - (ox + WORLD.w * scale)), WORLD.h * scale);

      // Parallax layers (drawn FULL-CANVAS for better viewport fit)
      for (const layer of bgLayers) {
        const par = layer.parallax ?? 0;
        // Use player position as a cheap “camera” reference for parallax.
        const camX = (playerRef.current?.x ?? WORLD.w / 2) - WORLD.w / 2;
        const camY = (playerRef.current?.y ?? WORLD.h / 2) - WORLD.h / 2;
        const px = ox - camX * par * scale;
        const py = oy - camY * par * scale;

        if (layer.type === "starfield") {
          const speedY = layer.speedY ?? 0;
          stars.forEach((st) => {
            st.y += speedY * dt;
            if (st.y > WORLD.h) st.y = 0;
            if (st.y < 0) st.y = WORLD.h;
          });
          ctx.fillStyle = "rgba(255,255,255,0.8)";
          // Tile the starfield so it covers the whole canvas (even outside the 800x600 world frame).
          for (let tx = -worldPxW; tx <= w + worldPxW; tx += worldPxW) {
            for (let ty = -worldPxH; ty <= h + worldPxH; ty += worldPxH) {
              stars.forEach((st) => {
                const sx = px + tx + st.x * scale;
                const sy = py + ty + st.y * scale;
                if (sx < -10 || sx > w + 10 || sy < -10 || sy > h + 10) return;
                ctx.fillRect(sx, sy, st.s, st.s);
              });
            }
          }
        } else if (layer.type === "gradient") {
          if (gameType === "racing") {
            // Procedural road + lane markers (no assets)
            const roadW = WORLD.w * 0.52;
            const roadX = (WORLD.w - roadW) / 2;
            const scroll = (t / 1000) * 260;

            // grass
            ctx.fillStyle = "rgba(20, 90, 40, 0.35)";
            ctx.fillRect(px, py, WORLD.w * scale, WORLD.h * scale);

            // road
            ctx.fillStyle = "rgba(35, 35, 40, 0.85)";
            ctx.fillRect(px + roadX * scale, py, roadW * scale, WORLD.h * scale);

            // border lines
            ctx.strokeStyle = "rgba(255,255,255,0.18)";
            ctx.lineWidth = 2;
            ctx.strokeRect(px + roadX * scale, py, roadW * scale, WORLD.h * scale);

            // dashed center line
            ctx.fillStyle = "rgba(255,255,255,0.35)";
            const dashH = 26;
            const gap = 18;
            for (let y0 = -dashH; y0 < WORLD.h + dashH; y0 += dashH + gap) {
              const yy = y0 + (scroll % (dashH + gap));
              ctx.fillRect(
                px + (WORLD.w / 2 - 2) * scale,
                py + yy * scale,
                4 * scale,
                dashH * scale,
              );
            }
          } else if (gameType === "platformer") {
            const g = ctx.createLinearGradient(px, py, px, py + WORLD.h * scale);
            g.addColorStop(0, "rgba(120, 190, 255, 0.35)");
            g.addColorStop(1, "rgba(20, 40, 20, 0.35)");
            ctx.fillStyle = g;
            ctx.fillRect(0, 0, w, h);
          } else {
            // Generic gradient layer (works for shooter/topdown/puzzle/etc.)
            const bg = normalizeCssColor(theme?.background, "hsl(0, 0%, 4%)");
            const p = normalizeCssColor(theme?.primary, "hsl(200, 80%, 50%)");
            const a = normalizeCssColor(theme?.accent, "hsl(300, 70%, 50%)");

            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, hslToHsla(bg, 1));
            g.addColorStop(0.55, hslToHsla(p, 0.16));
            g.addColorStop(1, hslToHsla(a, 0.18));
            ctx.fillStyle = g;
            ctx.fillRect(0, 0, w, h);

            // subtle dunes/noise stripes for "desert" vibes (without adding new layer types)
            // Only if the palette looks warm (heuristic) and this isn't space.
            const maybeWarm = /hsl\(\s*(3\d|4\d|5\d)/.test(p) || /hsl\(\s*(3\d|4\d|5\d)/.test(a);
            const hasStarfield = bgLayers.some((l) => l.type === "starfield" || l.type === "nebula");
            if (maybeWarm && !hasStarfield) {
              ctx.save();
              ctx.globalAlpha = 0.18;
              ctx.strokeStyle = "rgba(255,255,255,0.12)";
              ctx.lineWidth = 2;
              for (let i = 0; i < 10; i++) {
                const yy = py + (WORLD.h * (0.45 + i * 0.06)) * scale;
                ctx.beginPath();
                ctx.moveTo(px - 40, yy);
                ctx.quadraticCurveTo(
                  px + WORLD.w * 0.5 * scale,
                  yy + (Math.sin((t / 1000) + i) * 12) * scale,
                  px + WORLD.w * scale + 40,
                  yy
                );
                ctx.stroke();
              }
              ctx.restore();
            }
          }
        } else if (layer.type === "nebula") {
           const accentColor = normalizeCssColor(theme?.accent, "hsl(300, 70%, 50%)");
          // NOTE: canvas does not accept "hsl(...)33"; must be hsla.
          ctx.fillStyle = hslToHsla(accentColor, 0.2);
          // Full-width band to avoid looking clipped/boxed on wide viewports.
          const bandY = h * 0.33 + Math.sin(t / 2200) * 12;
          ctx.fillRect(0, bandY, w, h * 0.34);
        }
        // Note: "solid" layer type doesn't need extra drawing; background is already filled at the start.
      }

      // Clip all world drawing to the world rect (entities/particles/etc.)
      ctx.save();
      ctx.beginPath();
      ctx.rect(ox, oy, worldPxW, worldPxH);
      ctx.clip();

      // Update player with physics or direct control
      const p = playerRef.current;
      if (running && p && initialPlayer) {
        const keys = keysRef.current;
        const up = keys.ArrowUp || keys.w;
        const down = keys.ArrowDown || keys.s;
        const left = keys.ArrowLeft || keys.a;
        const right = keys.ArrowRight || keys.d;
        const space = keys[" "];

        if (hasPhysicsSystem) {
          // Physics-based movement
          const physics = physicsSystemRef.current;
          const speed = (initialPlayer.props?.speed as number | undefined) ?? 220;
          
          let fx = 0;
          if (left) fx -= speed * 5;
          if (right) fx += speed * 5;
          
          physics.applyForce(initialPlayer.id, fx, 0);
          
          // Jump (platformer)
          if (gameType === "platformer" && space && physics.isGrounded(initialPlayer.id)) {
            physics.applyImpulse(initialPlayer.id, 0, -300);
            if (hasAudioSystem) audioSystemRef.current.playSound("jump");
          }
        } else {
          // Direct movement (old way)
          const speed = (initialPlayer.props?.speed as number | undefined) ?? 220;
          let vx = 0;
          let vy = 0;
          if (left) vx -= 1;
          if (right) vx += 1;
          if (up) vy -= 1;
          if (down) vy += 1;
          const len = Math.hypot(vx, vy) || 1;
          vx /= len;
          vy /= len;
          p.x += vx * speed * dt;
          p.y += vy * speed * dt;
        }
        
        p.x = clamp(p.x, initialPlayer.w / 2, WORLD.w - initialPlayer.w / 2);
        p.y = clamp(p.y, initialPlayer.h / 2, WORLD.h - initialPlayer.h / 2);

        // Shooting (arcade shooter)
        if (gameType === "shooter") {
          fireCooldownRef.current = Math.max(0, fireCooldownRef.current - dt);
          const fireRate = (initialPlayer.props?.fireRate as number | undefined) ?? 7;
          const fireInterval = fireRate > 0 ? 1 / fireRate : 0.14;
          if (space && fireCooldownRef.current <= 0) {
            fireCooldownRef.current = fireInterval;
            const bulletSpeed = (initialPlayer.props?.bulletSpeed as number | undefined) ?? 520;

            const spawnBullet = (vx: number, vy: number) => {
              bulletsRef.current.push({
                id: `b_${Date.now()}_${Math.floor(Math.random() * 9999)}`,
                type: "bullet",
                x: p.x,
                y: p.y - initialPlayer.h * 0.7,
                w: 6,
                h: 14,
                vx,
                vy,
                dead: false,
              });
            };

            if (buffsRef.current.spread > 0) {
              spawnBullet(-140, -Math.abs(bulletSpeed) * 0.95);
              spawnBullet(0, -Math.abs(bulletSpeed));
              spawnBullet(140, -Math.abs(bulletSpeed) * 0.95);
            } else {
              spawnBullet(0, -Math.abs(bulletSpeed));
            }

            playSfx("shoot");

            if (hasParticleSystem) {
              const primaryColor = (theme?.primary && typeof theme.primary === "string") ? theme.primary : "hsl(200, 80%, 50%)";
              particleSystemRef.current.emit(p.x, p.y - initialPlayer.h * 0.85, 6, {
                life: 0.25,
                speed: 220,
                size: 2,
                color: primaryColor,
                spread: Math.PI * 0.7,
                direction: -Math.PI / 2,
              });
            }
          }
        }
      }

      const canSimulate = running && !gameOverRef.current;

      // Update buffs
      if (canSimulate) {
        buffsRef.current.shield = Math.max(0, buffsRef.current.shield - dt);
        buffsRef.current.spread = Math.max(0, buffsRef.current.spread - dt);

        // Regenerate shield (spec-based)
        if (shieldRef.current && shieldRef.current.max > 0 && shieldRef.current.regenPerSec > 0) {
          shieldRef.current.value = Math.min(
            shieldRef.current.max,
            shieldRef.current.value + shieldRef.current.regenPerSec * dt,
          );
        }
      }

      // Update spawners
      if (canSimulate && hasSpawner && spawners.length > 0) {
        spawnTimerRef.current += dt;
        powerupTimerRef.current += dt;
        const sp = spawners[0];
        const baseRate = (sp.props?.spawnRate as number | undefined) ?? 1.5;

        // Waves + difficulty: scale by score.
        const score = hasScoreSystem ? scoreSystemRef.current.getScore() : 0;
        const wave = 1 + Math.floor(score / 200);
        const rate = baseRate + wave * 0.25;
        const interval = 1 / rate;
        if (spawnTimerRef.current >= interval) {
          spawnTimerRef.current = 0;
          const sx = sp.x + (Math.random() - 0.5) * sp.w;

          // Mix enemies + asteroids. More enemies over time.
          const enemyChance = Math.min(0.85, 0.45 + wave * 0.06);
          const spawnType = (Math.random() < enemyChance)
            ? "enemy"
            : "asteroid";

          // Enemy variants
          const roll = Math.random();
          const variant: Spawned["variant"] =
            roll < 0.55 ? "scout" :
            roll < 0.85 ? "tank" :
            "sniper";

          const speed = spawnType === "asteroid"
            ? 70 + wave * 6 + Math.random() * 30
            : 90 + wave * 8 + Math.random() * 35;

          const size = spawnType === "asteroid"
            ? 20 + Math.random() * 18
            : (variant === "tank" ? 30 : variant === "sniper" ? 22 : 24);

          const hp = spawnType === "enemy" ? (variant === "tank" ? 2 : 1) : 1;

          // Optional lateral movement for enemies
          const vx = spawnType === "enemy"
            ? (variant === "sniper" ? (Math.random() < 0.5 ? -60 : 60) : (Math.random() - 0.5) * 90)
            : 0;

          spawnedRef.current.push({
            id: `spawn_${Date.now()}`,
            type: spawnType,
            x: clamp(sx, 0, WORLD.w),
            y: -30, // Spawn above screen
            w: size,
            h: size,
            vy: speed,
            vx,
            hp,
            variant: spawnType === "enemy" ? variant : undefined,
            dead: false,
          });
        }

        // Powerups: rare + only if not already buffed
        const hasAnyBuff = buffsRef.current.shield > 0 || buffsRef.current.spread > 0;
        if (!hasAnyBuff && powerupTimerRef.current >= 6.5 && Math.random() < 0.22) {
          powerupTimerRef.current = 0;
          const kind: Spawned["kind"] = Math.random() < 0.5 ? "shield" : "spread";
          spawnedRef.current.push({
            id: `pu_${Date.now()}`,
            type: "powerup",
            kind,
            x: clamp(sp.x + (Math.random() - 0.5) * sp.w, 30, WORLD.w - 30),
            y: -20,
            w: 20,
            h: 20,
            vy: 85,
            vx: (Math.random() - 0.5) * 40,
            dead: false,
          });
        }

        spawnedRef.current = spawnedRef.current.filter((e) => {
          e.y += e.vy * dt;
          if (e.vx) {
            e.x = clamp(e.x + e.vx * dt, 10, WORLD.w - 10);
            // Simple bounce to keep things on-screen
            if (e.x <= 10 || e.x >= WORLD.w - 10) e.vx *= -1;
          }
          return e.y < WORLD.h + 50 && !e.dead;
        });
      }

      // Update bullets
      if (canSimulate && bulletsRef.current.length > 0) {
        bulletsRef.current = bulletsRef.current
          .map((b) => ({ ...b, x: b.x + b.vx * dt, y: b.y + b.vy * dt }))
          .filter((b) => !b.dead && b.y > -80 && b.x > -80 && b.x < WORLD.w + 80);
      }

      // Update systems
      if (canSimulate) {
        const allEntities = [
          ...(p && initialPlayer ? [{ ...initialPlayer, x: p.x, y: p.y }] : []),
          ...spawnedRef.current,
          ...bulletsRef.current,
        ];
        
        // Physics system
        if (hasPhysicsSystem && spec?.scene) {
          physicsSystemRef.current.update(dt, allEntities, spec.scene.gravity);
        }
        
        // Particle system
        if (hasParticleSystem) {
          particleSystemRef.current.update(dt);
        }
        
        // Score system
        if (hasScoreSystem) {
          scoreSystemRef.current.update(dt);
        }
        
        // Timer system
        if (hasTimerSystem) {
          timerSystemRef.current.update(dt);
        }
        
        // AI system
        if (hasAISystem) {
          aiSystemRef.current.update(dt, allEntities);
        }
        
        // Animation system
        if (hasAnimationSystem) {
          animationSystemRef.current.update(dt);
        }
        
        // Camera system
        if (hasCameraSystem) {
          cameraSystemRef.current.update(dt, allEntities);
        }
        
        // Collision detection
        if (hasCollisionSystem) {
          const collisionEntities: OrdaxEntity[] = allEntities.map(e => ({
            id: e.id,
            type: e.type,
            x: e.x,
            y: e.y,
            w: e.w,
            h: e.h,
          }));
          collisionSystemRef.current.update(collisionEntities);
        }
      }

      const drawEntity = (e: OrdaxEntity) => {
          if (!isFiniteNumber(e.x) || !isFiniteNumber(e.y) || !isFiniteNumber(e.w) || !isFiniteNumber(e.h)) return;

          const x = ox + (e.x - e.w / 2) * scale;
          const y = oy + (e.y - e.h / 2) * scale;
          const ew = e.w * scale;
          const eh = e.h * scale;

          if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(ew) || !Number.isFinite(eh)) return;
          if (ew <= 0 || eh <= 0) return;

        // Check if entity has sprite
        const sprite = spritesRef.current.get(e.id);
        if (sprite && spritesLoaded && e.sprite) {
          // Draw sprite
          const frame = hasAnimationSystem 
            ? animationSystemRef.current.getCurrentFrame(e.id)
            : null;
          
          if (frame) {
            ctx.drawImage(
              sprite,
              frame.x, frame.y, frame.w, frame.h,
              x, y, ew, eh
            );
          } else {
            // Draw full sprite
            ctx.drawImage(sprite, x, y, ew, eh);
          }
        } else {
          // Procedural fallback visuals (no external assets needed)
           const primaryColor = normalizeCssColor(theme?.primary, "hsl(180, 80%, 50%)");
           const accentColor = normalizeCssColor(theme?.accent, "hsl(300, 70%, 50%)");
          const fontFamily = (theme?.font && typeof theme.font === 'string') ? theme.font : "ui-monospace, monospace";

          const isPlayer = e.type === "player" || e.id === "player";
          const isOtherPlayer = e.type === "player" && e.id !== "player";
          // Many AI specs use type "sprite" for enemies in racing.
          const isEnemy = e.type.includes("enemy") || e.id.includes("enemy") || e.type === "sprite";

          if (isPlayer) {
            if (gameType === "racing") {
              // Top-down car (player + extra players)
              const cx = x + ew / 2;
              const cy = y + eh / 2;
              const bodyW = ew * 0.72;
              const bodyH = eh * 0.92;
              const bodyX = cx - bodyW / 2;
              const bodyY = cy - bodyH / 2;

              const secondary = (theme as any)?.secondary;
              const carColor = isOtherPlayer && typeof secondary === "string" ? secondary : primaryColor;

              ctx.fillStyle = hslToHsla(carColor, 0.55);
              ctx.strokeStyle = hslToHsla(carColor, 0.95);
              ctx.lineWidth = 2;
              ctx.beginPath();
              ctx.roundRect(bodyX, bodyY, bodyW, bodyH, 8);
              ctx.fill();
              ctx.stroke();

              // windshield
              ctx.fillStyle = "rgba(10, 20, 30, 0.55)";
              ctx.beginPath();
              ctx.roundRect(bodyX + bodyW * 0.18, bodyY + bodyH * 0.18, bodyW * 0.64, bodyH * 0.22, 6);
              ctx.fill();

              // headlights
              ctx.fillStyle = "rgba(255, 255, 255, 0.55)";
              ctx.fillRect(bodyX + bodyW * 0.12, bodyY + bodyH * 0.06, bodyW * 0.14, bodyH * 0.06);
              ctx.fillRect(bodyX + bodyW * 0.74, bodyY + bodyH * 0.06, bodyW * 0.14, bodyH * 0.06);

              // tires
              ctx.fillStyle = "rgba(0,0,0,0.6)";
              const tw = bodyW * 0.16;
              const th = bodyH * 0.18;
              ctx.fillRect(bodyX - tw * 0.25, bodyY + bodyH * 0.18, tw, th);
              ctx.fillRect(bodyX + bodyW - tw * 0.75, bodyY + bodyH * 0.18, tw, th);
              ctx.fillRect(bodyX - tw * 0.25, bodyY + bodyH * 0.64, tw, th);
              ctx.fillRect(bodyX + bodyW - tw * 0.75, bodyY + bodyH * 0.64, tw, th);
              return;
            }

            // Ship-like silhouette (pointing UP)
            const cx = x + ew / 2;
            const cy = y + eh / 2;
            const r = Math.max(10, Math.min(ew, eh) / 2);

            if (!Number.isFinite(cx) || !Number.isFinite(cy) || !Number.isFinite(r)) return;

            const grad = ctx.createRadialGradient(cx, cy - r * 0.25, r * 0.15, cx, cy, r);
            grad.addColorStop(0, hslToHsla(primaryColor, 0.95));
            grad.addColorStop(1, hslToHsla(primaryColor, 0.25));

            ctx.fillStyle = grad;
            ctx.strokeStyle = hslToHsla(primaryColor, 0.9);
            ctx.lineWidth = 2;

            ctx.beginPath();
            // Nose pointing UP
            ctx.moveTo(cx, cy - r * 0.95);
            // Left wing
            ctx.lineTo(cx - r * 0.75, cy + r * 0.25);
            // Center back
            ctx.lineTo(cx, cy + r * 0.1);
            // Right wing
            ctx.lineTo(cx + r * 0.75, cy + r * 0.25);
            ctx.closePath();
            ctx.fill();
            ctx.stroke();

            // Cockpit
            ctx.fillStyle = hslToHsla(accentColor, 0.55);
            ctx.beginPath();
            ctx.ellipse(cx, cy - r * 0.1, r * 0.18, r * 0.28, 0, 0, Math.PI * 2);
            ctx.fill();

            // Thruster glow (at the back)
            ctx.fillStyle = hslToHsla(accentColor, 0.22);
            ctx.beginPath();
            ctx.arc(cx, cy + r * 0.35, r * 0.35, 0, Math.PI * 2);
            ctx.fill();
          } else {
            let fill = hslToHsla(primaryColor, 0.14);
            let stroke = hslToHsla(primaryColor, 0.6);
            if (isEnemy) {
              fill = hslToHsla(accentColor, 0.16);
              stroke = hslToHsla(accentColor, 0.85);
            } else if (e.type === "static") {
              fill = "rgba(255,255,255,0.06)";
              stroke = "rgba(255,255,255,0.18)";
            }

            ctx.fillStyle = fill;
            ctx.strokeStyle = stroke;
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.roundRect(x, y, Math.max(1, ew), Math.max(1, eh), 6);
            ctx.fill();
            ctx.stroke();

            // Avoid noisy labels like "enemy_car_1"; label only unknown entities.
            const isKnown = isEnemy || e.type === "wall" || e.type === "obstacle" || e.type === "coin";
            if (!isKnown) {
              ctx.fillStyle = "rgba(255,255,255,0.35)";
              ctx.font = `10px ${fontFamily}`;
              ctx.fillText(e.id, x + 6, y + 16);
            }
          }
        }
      };

      const drawSpawned = (s: Spawned) => {
        if (s.dead) return;

        if (!isFiniteNumber(s.x) || !isFiniteNumber(s.y) || !isFiniteNumber(s.w) || !isFiniteNumber(s.h)) return;

        const x = ox + (s.x - s.w / 2) * scale;
        const y = oy + (s.y - s.h / 2) * scale;
        const ew = s.w * scale;
        const eh = s.h * scale;

        if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(ew) || !Number.isFinite(eh)) return;
        if (ew <= 0 || eh <= 0) return;
        
         const accentColor = normalizeCssColor(theme?.accent, "hsl(300, 70%, 50%)");
        
        if (s.type === "powerup") {
          const primaryColor = (theme?.primary && typeof theme.primary === "string") ? theme.primary : "hsl(200, 80%, 50%)";
          const col = s.kind === "shield" ? primaryColor : accentColor;
          ctx.fillStyle = hslToHsla(col, 0.2);
          ctx.strokeStyle = hslToHsla(col, 0.95);
          ctx.lineWidth = 2;
          const cx = x + ew / 2;
          const cy = y + eh / 2;
          ctx.beginPath();
          ctx.moveTo(cx, cy - eh * 0.55);
          ctx.lineTo(cx + ew * 0.55, cy);
          ctx.lineTo(cx, cy + eh * 0.55);
          ctx.lineTo(cx - ew * 0.55, cy);
          ctx.closePath();
          ctx.fill();
          ctx.stroke();
          return;
        }

        if (s.type === "asteroid") {
          // Asteroid visual
          ctx.fillStyle = "rgba(150, 150, 150, 0.4)";
          ctx.strokeStyle = "rgba(200, 200, 200, 0.8)";
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.arc(x + ew / 2, y + eh / 2, Math.max(1, ew / 2), 0, Math.PI * 2);
          ctx.fill();
          ctx.stroke();
          
          // Add some detail
          ctx.fillStyle = "rgba(100, 100, 100, 0.6)";
          ctx.beginPath();
          ctx.arc(x + ew / 2 - ew * 0.2, y + eh / 2 - eh * 0.15, ew * 0.15, 0, Math.PI * 2);
          ctx.fill();
        } else if (s.type === "enemy") {
          // Enemy ship visual (pointing DOWN)
          const cx = x + ew / 2;
          const cy = y + eh / 2;
          const r = Math.max(8, Math.min(ew, eh) / 2);

          if (!Number.isFinite(cx) || !Number.isFinite(cy) || !Number.isFinite(r)) return;
          
          const grad = ctx.createRadialGradient(cx, cy + r * 0.25, r * 0.15, cx, cy, r);
          grad.addColorStop(0, hslToHsla(accentColor, 0.95));
          grad.addColorStop(1, hslToHsla(accentColor, 0.25));
          
          ctx.fillStyle = grad;
          ctx.strokeStyle = hslToHsla(accentColor, 0.9);
          ctx.lineWidth = 2;
          
          ctx.beginPath();
          // Nose pointing DOWN
          ctx.moveTo(cx, cy + r * 0.95);
          // Left wing
          ctx.lineTo(cx - r * 0.75, cy - r * 0.25);
          // Center back
          ctx.lineTo(cx, cy - r * 0.1);
          // Right wing
          ctx.lineTo(cx + r * 0.75, cy - r * 0.25);
          ctx.closePath();
          ctx.fill();
          ctx.stroke();
          
          // Cockpit
          ctx.fillStyle = hslToHsla(accentColor, 0.55);
          ctx.beginPath();
          ctx.ellipse(cx, cy + r * 0.1, r * 0.18, r * 0.28, 0, 0, Math.PI * 2);
          ctx.fill();

          // Variant detail (tiny stripe)
          if (s.variant) {
            ctx.fillStyle = "rgba(255,255,255,0.22)";
            const stripeW = s.variant === "tank" ? r * 0.65 : r * 0.45;
            ctx.fillRect(cx - stripeW / 2, cy - r * 0.15, stripeW, 3);
          }
        } else {
          // Generic enemy
          ctx.fillStyle = hslToHsla(accentColor, 0.25);
          ctx.strokeStyle = hslToHsla(accentColor, 0.9);
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.arc(x + ew / 2, y + eh / 2, Math.max(1, ew / 2), 0, Math.PI * 2);
          ctx.fill();
          ctx.stroke();
        }
      };

      const drawBullet = (b: Bullet) => {
        if (b.dead) return;
        if (!isFiniteNumber(b.x) || !isFiniteNumber(b.y) || !isFiniteNumber(b.w) || !isFiniteNumber(b.h)) return;

        const x = ox + (b.x - b.w / 2) * scale;
        const y = oy + (b.y - b.h / 2) * scale;
        const ew = b.w * scale;
        const eh = b.h * scale;

        if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(ew) || !Number.isFinite(eh)) return;
        if (ew <= 0 || eh <= 0) return;

         const primaryColor = normalizeCssColor(theme?.primary, "hsl(200, 80%, 50%)");
        ctx.fillStyle = hslToHsla(primaryColor, 0.85);
        ctx.strokeStyle = hslToHsla(primaryColor, 0.95);
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.roundRect(x, y, ew, eh, 3);
        ctx.fill();
        ctx.stroke();
      };

      // World frame
       const primaryColor = normalizeCssColor(theme?.primary, "hsl(180, 80%, 50%)");
      ctx.strokeStyle = hslToHsla(primaryColor, 0.18);
      ctx.lineWidth = 2;
      ctx.strokeRect(ox, oy, WORLD.w * scale, WORLD.h * scale);

      // Render entities (with player override, skip spawners)
      if (spec?.scene?.entities) {
        for (const e of spec.scene.entities) {
          // Skip spawners - they are invisible
          if (e.type === "spawner") continue;
          
          if ((e.type === "player" || e.id === "player") && playerRef.current) {
            drawEntity({ ...e, x: playerRef.current.x, y: playerRef.current.y });
          } else {
            drawEntity(e);
          }
        }
      }

      // Render spawned objects
      spawnedRef.current.forEach(drawSpawned);

      // Render bullets
      bulletsRef.current.forEach(drawBullet);
      
      // Render particles (in world space)
      if (hasParticleSystem) {
        ctx.save();
        ctx.translate(ox, oy);
        ctx.scale(scale, scale);
        particleSystemRef.current.render(ctx);
        ctx.restore();
      }

      // End world clip
      ctx.restore();

      // HUD do jogo (apenas gameplay info)
      ctx.save();
      ctx.fillStyle = "rgba(255,255,255,0.9)";
      const fontFamily = (theme?.font && typeof theme.font === 'string') ? theme.font : "ui-monospace, monospace";
      ctx.font = `14px ${fontFamily}`;
      
      const hudX = ox + 15;
      let hudY = oy + 25;
      
      // Score
      if (hasScoreSystem) {
        const score = scoreSystemRef.current.getScore();
        const multiplier = scoreSystemRef.current.getMultiplier();
        ctx.fillText(
          `Score: ${score}${multiplier > 1 ? ` x${multiplier.toFixed(1)}` : ''}`,
          hudX,
          hudY
        );
        hudY += 25;
      }
      
      // Health
      if (playerRef.current) {
        const health = Math.max(0, playerRef.current.health);
        ctx.fillText(`Health: ${health}`, hudX, hudY);
        hudY += 10;
        
        // Health bar
        const barWidth = 150;
        const barHeight = 12;
        const barX = hudX;
        const barY = hudY;
        
        ctx.fillStyle = "rgba(0,0,0,0.6)";
        ctx.fillRect(barX, barY, barWidth, barHeight);
        
        const healthPercent = health / 100;
         const primaryColor = normalizeCssColor(theme?.primary, "hsl(186, 100%, 45%)");
        const secondaryColor = ((theme as any)?.secondary && typeof (theme as any).secondary === "string") ? (theme as any).secondary : "hsl(300, 100%, 45%)";
        const dangerColor = "hsl(0, 84%, 60%)";

        const fillColor = health > 50 ? primaryColor : health > 25 ? secondaryColor : dangerColor;
        ctx.fillStyle = hslToHsla(fillColor, 0.9);
        ctx.fillRect(barX, barY, barWidth * healthPercent, barHeight);
        
        ctx.strokeStyle = "rgba(255,255,255,0.6)";
        ctx.lineWidth = 2;
        ctx.strokeRect(barX, barY, barWidth, barHeight);

        // Shield bar (if enabled)
        if (shieldRef.current && shieldRef.current.max > 0) {
          const sy = barY + barHeight + 10;
          const sWidth = barWidth;
          const sHeight = 10;
          const shieldPercent = clamp(shieldRef.current.value / shieldRef.current.max, 0, 1);

          // background
          ctx.fillStyle = "rgba(0,0,0,0.5)";
          ctx.fillRect(barX, sy, sWidth, sHeight);

          // fill (use primary color for coherence)
          const shieldFill = hslToHsla(primaryColor, 0.75);
          ctx.fillStyle = shieldFill;
          ctx.fillRect(barX, sy, sWidth * shieldPercent, sHeight);

          // border
          ctx.strokeStyle = "rgba(255,255,255,0.5)";
          ctx.lineWidth = 2;
          ctx.strokeRect(barX, sy, sWidth, sHeight);

          // label
          ctx.fillStyle = "rgba(255,255,255,0.75)";
          ctx.font = `12px ${fontFamily}`;
          ctx.fillText(`Shield: ${Math.round(shieldRef.current.value)}`, barX, sy + 26);
        }
      }
      
      ctx.restore();
      
      // Controls hint
      ctx.fillStyle = "rgba(255,255,255,0.5)";
      ctx.font = `11px ${fontFamily}`;
      const showSpace = gameType === "shooter" || gameType === "platformer" || hasPhysicsSystem;
      const hint = gameOverRef.current
        ? "Game Over — pressione Enter ou R para reiniciar"
        : "WASD / Arrows" + (showSpace ? " + Space" : "");
      ctx.fillText(hint, ox + 15, oy + WORLD.h * scale - 15);

      raf = requestAnimationFrame(draw);
    };

    raf = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(raf);
      // Cleanup audio
      if (hasAudioSystem) {
        audioSystemRef.current.stopMusic();
      }
    };
  }, [initialPlayer, running, spec, spawners, hasSpawner, bgLayers, theme, hasPhysicsSystem, hasCollisionSystem, hasParticleSystem, hasScoreSystem, hasAISystem, hasUISystem, hasTimerSystem, hasCameraSystem, hasAudioSystem, hasAnimationSystem, spritesLoaded]);

  return <canvas ref={canvasRef} className="h-full w-full" />;
});
OrdaxCanvas.displayName = "OrdaxCanvas";
