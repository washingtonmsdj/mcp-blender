import { forwardRef, useEffect, useImperativeHandle, useMemo, useRef } from "react";
import type { OrdaxEntity, OrdaxSpec } from "@/lib/ordax/types";
import { CollisionSystem } from "@/lib/ordax/systems/CollisionSystem";
import { ParticleSystem } from "@/lib/ordax/systems/ParticleSystem";
import { ScoreSystem } from "@/lib/ordax/systems/ScoreSystem";
import { AudioSystem } from "@/lib/ordax/systems/AudioSystem";
import { CameraSystem } from "@/lib/ordax/systems/CameraSystem";
import { UISystem } from "@/lib/ordax/systems/UISystem";
import { TimerSystem } from "@/lib/ordax/systems/TimerSystem";
import { AISystem } from "@/lib/ordax/systems/AISystem";
import { toast } from "sonner";

type Props = {
  spec: OrdaxSpec;
  running: boolean;
};

export type OrdaxCanvasHandle = {
  reset: () => void;
  getDebugInfo: () => DebugInfo;
};

type DebugInfo = {
  systems: {
    collision: boolean;
    particles: boolean;
    particleCount: number;
    score: boolean;
    ai: boolean;
    camera: boolean;
    audio: boolean;
    ui: boolean;
    timer: boolean;
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
};

const WORLD = { w: 800, h: 600 };

type Spawned = {
  id: string;
  type: string;
  x: number;
  y: number;
  w: number;
  h: number;
  vy: number;
  dead?: boolean;
};

function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(max, n));
}

export const OrdaxCanvas = forwardRef<OrdaxCanvasHandle, Props>(({ spec, running }, ref) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const keysRef = useRef<Keys>({});
  const playerRef = useRef<{ x: number; y: number; health: number } | null>(null);
  const spawnedRef = useRef<Spawned[]>([]);
  const spawnTimerRef = useRef<number>(0);
  const lastTRef = useRef<number>(0);
  
  // System instances
  const collisionSystemRef = useRef<CollisionSystem>(new CollisionSystem());
  const particleSystemRef = useRef<ParticleSystem>(new ParticleSystem());
  const scoreSystemRef = useRef<ScoreSystem>(new ScoreSystem());
  const audioSystemRef = useRef<AudioSystem>(new AudioSystem());
  const cameraSystemRef = useRef<CameraSystem>(new CameraSystem(WORLD.w, WORLD.h));
  const uiSystemRef = useRef<UISystem>(new UISystem());
  const timerSystemRef = useRef<TimerSystem>(new TimerSystem());
  const aiSystemRef = useRef<AISystem>(new AISystem());

  const initialPlayer = useMemo(() => spec.scene.entities.find((e) => e.type === "player" || e.id === "player"), [spec]);
  const spawners = useMemo(() => spec.scene.entities.filter((e) => e.type === "spawner"), [spec]);

  const hasSpawner = spawners.length > 0;
  const visual = spec.visual;
  const bgLayers = visual?.background?.layers ?? [];
  const theme = visual?.theme;
  
  // Check which systems are enabled
  const hasCollisionSystem = spec.systems.includes("CollisionSystem");
  const hasParticleSystem = spec.systems.includes("ParticleSystem");
  const hasScoreSystem = spec.systems.includes("ScoreSystem");
  const hasAudioSystem = spec.systems.includes("AudioSystem");
  const hasCameraSystem = spec.systems.includes("CameraSystem");
  const hasUISystem = spec.systems.includes("UISystem");
  const hasTimerSystem = spec.systems.includes("TimerSystem");
  const hasAISystem = spec.systems.includes("AISystem");

  const reset = () => {
    if (initialPlayer) {
      playerRef.current = { 
        x: initialPlayer.x, 
        y: initialPlayer.y,
        health: (initialPlayer.props?.health as number) ?? 100
      };
    }
    spawnedRef.current = [];
    spawnTimerRef.current = 0;
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
    if (hasUISystem) {
      // Setup UI elements - NÃO renderizar, apenas manter dados
      // O HUD é desenhado manualmente no canvas
    }
  };

  useImperativeHandle(ref, () => ({ 
    reset,
    getDebugInfo: () => ({
      systems: {
        collision: hasCollisionSystem,
        particles: hasParticleSystem,
        particleCount: hasParticleSystem ? particleSystemRef.current.getCount() : 0,
        score: hasScoreSystem,
        ai: hasAISystem,
        camera: hasCameraSystem,
        audio: hasAudioSystem,
        ui: hasUISystem,
        timer: hasTimerSystem,
      },
      entities: {
        total: spec.scene.entities.length,
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
  }), [initialPlayer, hasCollisionSystem, hasParticleSystem, hasScoreSystem, hasAISystem, hasCameraSystem, hasAudioSystem, hasUISystem, hasTimerSystem, spec]);

  useEffect(() => {
    reset();
    
    // Setup collision callbacks
    if (hasCollisionSystem) {
      const collision = collisionSystemRef.current;
      
      // Player vs Enemy/Asteroid collision
      collision.on("player", "enemy", (player, enemy) => {
        const spawned = spawnedRef.current.find(s => s.id === enemy.id);
        if (spawned && !spawned.dead) {
          spawned.dead = true;
          
          // Damage player
          if (playerRef.current) {
            playerRef.current.health -= 20;
            if (playerRef.current.health <= 0) {
              toast.error("💥 Game Over!");
              playerRef.current.health = 0;
            }
          }
          
          // Particles
          if (hasParticleSystem) {
            particleSystemRef.current.emit(enemy.x, enemy.y, 20, {
              life: 0.5,
              speed: 150,
              size: 3,
              color: theme?.accent ?? "hsl(300, 70%, 50%)",
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
          
          // Damage player
          if (playerRef.current) {
            playerRef.current.health -= 10;
            if (playerRef.current.health <= 0) {
              toast.error("💥 Game Over!");
              playerRef.current.health = 0;
            }
          }
          
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
          }
          
          // Camera shake
          if (hasCameraSystem) {
            cameraSystemRef.current.shake(5, 150);
          }
        }
      });
    }
    
    // Setup AI for enemies
    if (hasAISystem) {
      const enemies = spec.scene.entities.filter(e => e.type === "enemy");
      enemies.forEach(enemy => {
        aiSystemRef.current.register(enemy.id, "chase", 80);
      });
    }
  }, [spec, hasCollisionSystem, hasParticleSystem, hasScoreSystem, hasCameraSystem, hasAISystem, theme]);

  useEffect(() => {
    const onDown = (e: KeyboardEvent) => {
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

      // Background
      const bgColor = theme?.background ?? "hsl(0, 0%, 4%)";
      ctx.fillStyle = bgColor;
      ctx.fillRect(0, 0, w, h);

      // Parallax layers
      for (const layer of bgLayers) {
        if (layer.type === "starfield") {
          const speedY = layer.speedY ?? 0;
          const p = layer.parallax ?? 0.3;
          stars.forEach((st) => {
            st.y += speedY * dt;
            if (st.y > WORLD.h) st.y = 0;
            if (st.y < 0) st.y = WORLD.h;
          });
          ctx.fillStyle = "rgba(255,255,255,0.8)";
          stars.forEach((st) => {
            const sx = ox + st.x * scale;
            const sy = oy + st.y * scale;
            ctx.fillRect(sx, sy, st.s, st.s);
          });
        } else if (layer.type === "gradient") {
          const grad = ctx.createLinearGradient(ox, oy, ox, oy + WORLD.h * scale);
          grad.addColorStop(0, theme?.primary ?? "hsl(200, 80%, 50%)");
          grad.addColorStop(1, theme?.background ?? "hsl(0, 0%, 4%)");
          ctx.fillStyle = grad;
          ctx.fillRect(ox, oy, WORLD.w * scale, WORLD.h * scale);
        } else if (layer.type === "nebula") {
          ctx.fillStyle = `${theme?.accent ?? "hsl(300, 70%, 50%)"}33`;
          ctx.fillRect(ox, oy + (WORLD.h / 3) * scale, WORLD.w * scale, (WORLD.h / 3) * scale);
        }
      }

      // Update player
      const p = playerRef.current;
      const speed = (initialPlayer?.props?.speed as number | undefined) ?? 220;
      if (running && p && initialPlayer) {
        const keys = keysRef.current;
        const up = keys.ArrowUp || keys.w;
        const down = keys.ArrowDown || keys.s;
        const left = keys.ArrowLeft || keys.a;
        const right = keys.ArrowRight || keys.d;
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
        p.x = clamp(p.x, 0, WORLD.w);
        p.y = clamp(p.y, 0, WORLD.h);
      }

      // Update spawners
      if (running && hasSpawner && spawners.length > 0) {
        spawnTimerRef.current += dt;
        const sp = spawners[0];
        const rate = (sp.props?.spawnRate as number | undefined) ?? 1.5;
        const interval = 1 / rate;
        if (spawnTimerRef.current >= interval) {
          spawnTimerRef.current = 0;
          const sx = sp.x + (Math.random() - 0.5) * sp.w;
          const spawnType = sp.props?.spawnType as string | undefined ?? "enemy";
          spawnedRef.current.push({
            id: `spawn_${Date.now()}`,
            type: spawnType,
            x: clamp(sx, 0, WORLD.w),
            y: sp.y,
            w: 24,
            h: 24,
            vy: 80,
            dead: false,
          });
        }
        spawnedRef.current = spawnedRef.current.filter((e) => {
          e.y += e.vy * dt;
          return e.y < WORLD.h + 50 && !e.dead;
        });
      }

      // Update systems
      if (running) {
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
        if (hasAISystem && p && initialPlayer) {
          const allEntities = [
            { ...initialPlayer, x: p.x, y: p.y },
            ...spawnedRef.current
          ];
          aiSystemRef.current.update(dt, allEntities);
        }
        
        // Camera system
        if (hasCameraSystem && p && initialPlayer) {
          const allEntities = [
            { ...initialPlayer, x: p.x, y: p.y, id: "player", type: "player" }
          ];
          cameraSystemRef.current.update(dt, allEntities);
        }
      }

      // Collision detection
      if (running && hasCollisionSystem && p && initialPlayer) {
        const allEntities: OrdaxEntity[] = [
          { ...initialPlayer, x: p.x, y: p.y, type: "player" },
          ...spawnedRef.current.map(s => ({
            id: s.id,
            type: s.type,
            x: s.x,
            y: s.y,
            w: s.w,
            h: s.h,
          }))
        ];
        collisionSystemRef.current.update(allEntities);
      }
      
      // Update UI - Apenas atualizar dados internos, não renderizar
      if (hasUISystem) {
        const score = hasScoreSystem ? scoreSystemRef.current.getScore() : 0;
        const health = playerRef.current?.health ?? 100;
        const multiplier = hasScoreSystem ? scoreSystemRef.current.getMultiplier() : 1;
        
        // Dados disponíveis para debug, mas não renderizados
      }

      const drawEntity = (e: OrdaxEntity) => {
        const x = ox + (e.x - e.w / 2) * scale;
        const y = oy + (e.y - e.h / 2) * scale;
        const ew = e.w * scale;
        const eh = e.h * scale;

        // type-based styling
        let fill = `${theme?.primary ?? "hsl(180, 80%, 50%)"}20`;
        let stroke = `${theme?.primary ?? "hsl(180, 80%, 50%)"}55`;
        if (e.type === "player" || e.id === "player") {
          fill = `${theme?.primary ?? "hsl(180, 80%, 50%)"}25`;
          stroke = `${theme?.primary ?? "hsl(180, 80%, 50%)"}`;
        } else if (e.type.includes("enemy") || e.id.includes("enemy")) {
          fill = `${theme?.accent ?? "hsl(300, 70%, 50%)"}20`;
          stroke = `${theme?.accent ?? "hsl(300, 70%, 50%)"}`;
        } else if (e.type === "static") {
          fill = "rgba(255,255,255,0.06)";
          stroke = "rgba(255,255,255,0.18)";
        } else if (e.type === "spawner") {
          fill = "rgba(255,255,0,0.06)";
          stroke = "rgba(255,255,0,0.25)";
        }

        ctx.fillStyle = fill;
        ctx.strokeStyle = stroke;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.roundRect(x, y, Math.max(1, ew), Math.max(1, eh), 4);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = "rgba(255,255,255,0.6)";
        ctx.font = `10px ${theme?.font ?? "ui-monospace, monospace"}`;
        ctx.fillText(e.id, x + 6, y + 16);
      };

      const drawSpawned = (s: Spawned) => {
        if (s.dead) return;
        const x = ox + (s.x - s.w / 2) * scale;
        const y = oy + (s.y - s.h / 2) * scale;
        const ew = s.w * scale;
        const eh = s.h * scale;
        
        // Different colors for different types
        let fillColor = `${theme?.accent ?? "hsl(300, 70%, 50%)"}40`;
        let strokeColor = `${theme?.accent ?? "hsl(300, 70%, 50%)"}`;
        
        if (s.type === "asteroid") {
          fillColor = "rgba(150, 150, 150, 0.4)";
          strokeColor = "rgba(200, 200, 200, 0.8)";
        }
        
        ctx.fillStyle = fillColor;
        ctx.strokeStyle = strokeColor;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(x + ew / 2, y + eh / 2, Math.max(1, ew / 2), 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
      };

      // World frame
      ctx.strokeStyle = `${theme?.primary ?? "hsl(180, 80%, 50%)"}25`;
      ctx.lineWidth = 2;
      ctx.strokeRect(ox, oy, WORLD.w * scale, WORLD.h * scale);

      // Render entities (with player override)
      for (const e of spec.scene.entities) {
        if ((e.type === "player" || e.id === "player") && playerRef.current) {
          drawEntity({ ...e, x: playerRef.current.x, y: playerRef.current.y });
        } else {
          drawEntity(e);
        }
      }

      // Render spawned objects
      spawnedRef.current.forEach(drawSpawned);
      
      // Render particles (in world space)
      if (hasParticleSystem) {
        ctx.save();
        ctx.translate(ox, oy);
        ctx.scale(scale, scale);
        particleSystemRef.current.render(ctx);
        ctx.restore();
      }

      // HUD do jogo (apenas gameplay info) - Posicionado no canto superior esquerdo
      ctx.save();
      ctx.fillStyle = "rgba(255,255,255,0.9)";
      ctx.font = `14px ${theme?.font ?? "ui-monospace, monospace"}`;
      
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
        
        // Background
        ctx.fillStyle = "rgba(0,0,0,0.6)";
        ctx.fillRect(barX, barY, barWidth, barHeight);
        
        // Fill
        const healthPercent = health / 100;
        const fillColor = health > 50 ? "#0f0" : health > 25 ? "#ff0" : "#f00";
        ctx.fillStyle = fillColor;
        ctx.fillRect(barX, barY, barWidth * healthPercent, barHeight);
        
        // Border
        ctx.strokeStyle = "rgba(255,255,255,0.6)";
        ctx.lineWidth = 2;
        ctx.strokeRect(barX, barY, barWidth, barHeight);
      }
      
      ctx.restore();
      
      // Controls hint (canto inferior esquerdo)
      ctx.fillStyle = "rgba(255,255,255,0.5)";
      ctx.font = `11px ${theme?.font ?? "ui-monospace, monospace"}`;
      ctx.fillText("WASD / Arrows", ox + 15, oy + WORLD.h * scale - 15);

      raf = requestAnimationFrame(draw);
    };

    raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf);
  }, [initialPlayer, running, spec, spawners, hasSpawner, bgLayers, theme, hasCollisionSystem, hasParticleSystem, hasScoreSystem, hasAISystem, hasUISystem, hasTimerSystem, hasCameraSystem]);

  return <canvas ref={canvasRef} className="h-full w-full" />;
});
OrdaxCanvas.displayName = "OrdaxCanvas";
