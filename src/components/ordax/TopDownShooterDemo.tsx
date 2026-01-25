// Top-Down Shooter Demo - Integração completa Fases 4 + 5 + 6
import { useEffect, useRef, useState } from "react";
import { autofillTopDownShooter } from "@/lib/ordax/runtime-autofill/topdown-shooter";
import type { AutofillResult } from "@/lib/ordax/runtime-autofill/topdown-shooter";
import {
  PhysicsSystem,
  CollisionSystem,
  AISystem,
  InputSystem,
  SpawnerSystem,
  CombatSystem,
  GameStateSystem,
  ScoreSystem,
  TimerSystem,
  UISystem,
  JuiceSystem,
  AudioSystem,
} from "@/lib/ordax/systems";
import type { OrdaxEntity, OrdaxSpec } from "@/lib/ordax/types";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Play, Pause, RotateCcw, Eye, Gamepad2 } from "lucide-react";
import { HumanGamePlanView } from "./HumanGamePlanView";

export function TopDownShooterDemo() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [running, setRunning] = useState(false);
  const [gameState, setGameState] = useState<"START" | "PLAYING" | "PAUSED" | "GAME_OVER">("START");
  const [spec, setSpec] = useState<OrdaxSpec | null>(null);
  const [autofillResult, setAutofillResult] = useState<AutofillResult | null>(null);
  const systemsRef = useRef<any>(null);
  const entitiesRef = useRef<OrdaxEntity[]>([]);
  const rafRef = useRef<number>(0);

  // Initialize systems
  useEffect(() => {
    // Create minimal runtime
    const minimalRuntime = {
      gameType: 'topdown' as const,
      title: 'Top-Down Shooter Demo',
      description: 'Fases 4 + 5 + 6 Integration',
      systems: [],
      scene: {
        gravity: { x: 0, y: 0 },
        entities: []
      }
    };

    // Autofill
    const result = autofillTopDownShooter(minimalRuntime);
    setSpec(result.spec);
    setAutofillResult(result);
    entitiesRef.current = [...result.spec.scene.entities];

    // Create systems
    const systems = {
      physics: new PhysicsSystem(),
      collision: new CollisionSystem(),
      ai: new AISystem(),
      input: new InputSystem(),
      spawner: new SpawnerSystem(),
      combat: new CombatSystem(),
      gameState: new GameStateSystem(),
      score: new ScoreSystem(),
      timer: new TimerSystem(),
      ui: new UISystem(),
      juice: new JuiceSystem(),
      audio: new AudioSystem(),
    };

    // Setup collision handlers
    systems.collision.on('bullet', 'enemy', (bullet, enemy) => {
      systems.combat.handleCollisionDamage(bullet, enemy);
      systems.score.addScore(10);
      systems.juice.addFlashEffect(enemy);
      systems.audio.playHitSound();
    });

    systems.collision.on('enemy', 'player', (enemy, player) => {
      systems.combat.handleCollisionDamage(enemy, player);
      systems.juice.addKnockback(player, 50);
      systems.juice.addScreenShake(5, 0.15);
      systems.audio.playHitSound();
    });

    systemsRef.current = systems;

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  // Game loop
  useEffect(() => {
    if (!running || !systemsRef.current) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const systems = systemsRef.current;
    const entities = entitiesRef.current;
    let lastTime = performance.now();

    const loop = (currentTime: number) => {
      const dt = Math.min(0.05, (currentTime - lastTime) / 1000);
      lastTime = currentTime;

      // Update
      if (systems.gameState.current === 'PLAYING') {
        systems.input.update(dt, entities, currentTime / 1000);
        systems.physics.update(dt, entities);
        systems.ai.update(dt, entities);
        systems.spawner.update(dt, entities, currentTime / 1000);
        systems.collision.update(entities);
        systems.combat.update(dt, entities);
        systems.gameState.update(dt, entities);
        systems.timer.update(dt);
        systems.juice.update(dt, entities, systems.score, systems.gameState.current);

        // Check for shoot recoil
        const player = entities.find(e => e.type === 'player');
        const bullets = entities.filter(e => e.type === 'bullet' && e.props?._justCreated);
        if (bullets.length > 0 && player) {
          systems.juice.addShootRecoil(player);
          systems.audio.playShootSound();
          bullets.forEach(b => delete b.props._justCreated);
        }

        // Check for deaths
        const deadEntities = entities.filter(e => e.props?._justDied);
        deadEntities.forEach(e => {
          systems.juice.addDeathEffect(e);
          systems.audio.playDeathSound();
          delete e.props._justDied;
        });
      }

      // Render
      render(ctx, canvas, systems, entities);

      // Update React state
      setGameState(systems.gameState.current);

      rafRef.current = requestAnimationFrame(loop);
    };

    rafRef.current = requestAnimationFrame(loop);

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [running]);

  const render = (
    ctx: CanvasRenderingContext2D,
    canvas: HTMLCanvasElement,
    systems: any,
    entities: OrdaxEntity[]
  ) => {
    // Clear
    ctx.fillStyle = '#0a0a0a';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Render entities
    for (const entity of entities) {
      if (entity.type === 'ui' || entity.type === 'controls') continue;
      if (entity.type === 'spawner') continue;

      const color = String(entity.props?.color || '#fff');
      ctx.fillStyle = color;
      ctx.fillRect(
        entity.x - entity.w / 2,
        entity.y - entity.h / 2,
        entity.w,
        entity.h
      );
    }

    // Juice effects
    systems.juice.render(ctx, entities);

    // UI
    systems.ui.render(
      ctx,
      systems.gameState.current,
      entities,
      systems.score,
      systems.timer
    );

    // UI effects
    systems.juice.renderUIEffects(ctx, entities, systems.score);
  };

  const handleStart = () => {
    if (!systemsRef.current) return;
    systemsRef.current.gameState.start();
    setRunning(true);
  };

  const handlePause = () => {
    if (!systemsRef.current) return;
    if (systemsRef.current.gameState.current === 'PLAYING') {
      systemsRef.current.gameState.pause();
    } else if (systemsRef.current.gameState.current === 'PAUSED') {
      systemsRef.current.gameState.resume();
    }
  };

  const handleRestart = () => {
    if (!systemsRef.current) return;
    systemsRef.current.gameState.restart(entitiesRef.current);
    systemsRef.current.score.reset();
    systemsRef.current.timer.clear();
    systemsRef.current.juice.clear();
    setRunning(true);
  };

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center gap-2">
        <h2 className="text-2xl font-bold">Top-Down Shooter Demo</h2>
        <span className="text-sm text-muted-foreground">(Fases 4 + 5 + 6)</span>
      </div>

      <Tabs defaultValue="game" className="w-full">
        <TabsList className="grid w-full max-w-md grid-cols-2">
          <TabsTrigger value="game" className="flex items-center gap-2">
            <Gamepad2 className="w-4 h-4" />
            Jogar
          </TabsTrigger>
          <TabsTrigger value="plan" className="flex items-center gap-2">
            <Eye className="w-4 h-4" />
            Ver Plano
          </TabsTrigger>
        </TabsList>

        <TabsContent value="game" className="space-y-4 mt-6">
          <div className="flex gap-2">
            {gameState === 'START' && (
              <Button onClick={handleStart} size="sm">
                <Play className="w-4 h-4 mr-2" />
                Start
              </Button>
            )}
            {(gameState === 'PLAYING' || gameState === 'PAUSED') && (
              <Button onClick={handlePause} size="sm" variant="outline">
                <Pause className="w-4 h-4 mr-2" />
                {gameState === 'PLAYING' ? 'Pause' : 'Resume'}
              </Button>
            )}
            {gameState === 'GAME_OVER' && (
              <Button onClick={handleRestart} size="sm">
                <RotateCcw className="w-4 h-4 mr-2" />
                Restart
              </Button>
            )}
          </div>

          <canvas
            ref={canvasRef}
            width={800}
            height={600}
            className="border border-border rounded-lg bg-black"
          />

          <div className="text-sm text-muted-foreground text-center max-w-md">
            <p className="font-semibold mb-2">Controls:</p>
            <p>WASD - Move | SPACE - Shoot | R - Restart (when game over)</p>
          </div>

          <div className="text-xs text-muted-foreground text-center max-w-lg">
            <p>
              This demo integrates all systems from Phases 4, 5 & 6: Physics, AI, Spawner, Combat,
              GameState, Collision, Score, Timer, UI, Juice, Audio, and Human-Readable Layer.
            </p>
          </div>
        </TabsContent>

        <TabsContent value="plan" className="mt-6">
          {spec && (
            <HumanGamePlanView spec={spec} autofillResult={autofillResult || undefined} />
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
