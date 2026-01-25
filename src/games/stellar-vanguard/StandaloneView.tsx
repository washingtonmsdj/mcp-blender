import { useEffect, useMemo, useRef, useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import type { GamePhase } from "./types";
import { StellarVanguardGame } from "./game";
import { Renderer } from "./renderer";
import { WORLD } from "./constants";

export function StellarVanguardStandaloneView() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const rafRef = useRef<number>(0);
  const lastTRef = useRef<number>(0);
  const gameRef = useRef<StellarVanguardGame | null>(null);
  const rendererRef = useRef<Renderer | null>(null);

  type HudState = {
    phase: GamePhase;
    biomeName: string;
    score: number;
    highScore: number;
    hp: number;
    shield: number;
    shieldMax: number;
    dashCd: number;
    specialCd: number;
    bombCount: number;
    energy: number;
    upgrades: any[];
    wave: number;
    bossActive: boolean;
    bossHp?: number;
    bossHpMax?: number;
  };

  const [hud, setHud] = useState<HudState>(() => ({
    phase: "start",
    biomeName: "Nebulosa Colorida",
    score: 0,
    highScore: 0,
    hp: 100,
    shield: 0,
    shieldMax: 0,
    dashCd: 0,
    specialCd: 0,
    bombCount: 2,
    energy: 0,
    upgrades: [] as any[],
    wave: 1,
    bossActive: false,
    bossHp: undefined,
    bossHpMax: undefined,
  }));

  const help = useMemo(
    () =>
      "WASD/Setas mover • SPACE tiro • SHIFT dash • E especial • Q bomba • Enter iniciar • R reiniciar • 1-8 comprar upgrades",
    [],
  );

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const game = new StellarVanguardGame();
    game.mount();
    gameRef.current = game;
    const renderer = new Renderer(ctx);
    renderer.initStars(520);
    rendererRef.current = renderer;

    lastTRef.current = performance.now();
    const loop = (t: number) => {
      const dt = Math.min(0.05, (t - lastTRef.current) / 1000);
      lastTRef.current = t;

      const { w, h } = renderer.resizeToFit();
      const biome = game.getBiome();
      renderer.drawBackground(w, h, biome.theme, biome.layers, dt);

      game.update(dt);
      const snapshot = game.getAll();

      const world = renderer.beginWorld(w, h);
      // flash for bomb
      if (snapshot.uiFlashT > 0) {
        ctx.save();
        ctx.globalAlpha = Math.min(0.8, snapshot.uiFlashT * 8);
        ctx.fillStyle = biome.theme.gold;
        ctx.fillRect(0, 0, WORLD.w, WORLD.h);
        ctx.restore();
      }

      // particles (behind)
      renderer.drawParticles(snapshot.particles);

      // pickups
      for (const p of snapshot.pickups) {
        if (!p.alive) continue;
        renderer.drawPickup(p.x, p.y, p.r, biome.theme);
      }

      // enemies
      for (const e of snapshot.enemies) {
        if (!e.alive) continue;
        renderer.drawEnemy(e.x, e.y, e.w, e.h, biome.theme, e.kind);
      }

      // bullets
      for (const b of snapshot.bullets) {
        if (!b.alive) continue;
        renderer.drawBullet(b.x, b.y, b.r, biome.theme, b.owner);
      }

      // player
      renderer.drawShip(snapshot.player.x, snapshot.player.y, biome.theme, snapshot.player.dashTime > 0);

      renderer.endWorld();

      // HUD state (React overlay)
      if (t % 2 < 1) setHud(game.getHud());

      rafRef.current = requestAnimationFrame(loop);
    };

    rafRef.current = requestAnimationFrame(loop);
    return () => {
      cancelAnimationFrame(rafRef.current);
      game.unmount();
      gameRef.current = null;
      rendererRef.current = null;
    };
  }, []);

  const healthPct = Math.max(0, Math.min(1, hud.hp / 100));
  const shieldPct = hud.shieldMax > 0 ? Math.max(0, Math.min(1, hud.shield / hud.shieldMax)) : 0;

  return (
    <div className="min-h-screen w-full bg-background">
      <header className="mx-auto max-w-6xl px-6 py-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-foreground">Stellar Vanguard</h1>
            <p className="mt-1 text-sm text-muted-foreground">Shmup espacial standalone (Canvas 2D) — treino robusto.</p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="secondary">Standalone</Badge>
          </div>
        </div>
        <Separator className="mt-4" />
      </header>

      <main className="mx-auto grid max-w-6xl grid-cols-1 gap-4 px-6 pb-10 lg:grid-cols-[1fr_320px]">
        <Card className="relative overflow-hidden">
          <div className="aspect-[4/3] w-full bg-muted">
            <canvas ref={canvasRef} className="h-full w-full" />
          </div>

          {/* Overlay HUD */}
          <div className="pointer-events-none absolute left-3 top-3 right-3 flex flex-wrap items-start justify-between gap-3">
            <div className="pointer-events-auto rounded-md bg-card/70 backdrop-blur px-3 py-2 text-sm text-card-foreground shadow">
              <div className="flex items-center gap-2">
                <span className="font-medium">{hud.biomeName}</span>
                <span className="text-muted-foreground">• Wave {hud.wave}</span>
              </div>
              <div className="mt-1 text-xs text-muted-foreground">{help}</div>
            </div>

            <div className="pointer-events-auto rounded-md bg-card/70 backdrop-blur px-3 py-2 text-sm text-card-foreground shadow">
              <div className="flex items-center justify-between gap-3">
                <span>Score</span>
                <span className="font-mono">{hud.score}</span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-muted-foreground">High</span>
                <span className="font-mono text-muted-foreground">{hud.highScore}</span>
              </div>
              <div className="mt-2">
                <div className="text-xs text-muted-foreground">HP</div>
                <div className="h-2 w-40 overflow-hidden rounded bg-muted">
                  <div className="h-full bg-primary" style={{ width: `${healthPct * 100}%` }} />
                </div>
              </div>
              {hud.shieldMax > 0 ? (
                <div className="mt-2">
                  <div className="text-xs text-muted-foreground">Shield</div>
                  <div className="h-2 w-40 overflow-hidden rounded bg-muted">
                    <div className="h-full bg-accent" style={{ width: `${shieldPct * 100}%` }} />
                  </div>
                </div>
              ) : null}
              {hud.bossActive && typeof hud.bossHp === "number" && typeof hud.bossHpMax === "number" ? (
                <div className="mt-2">
                  <div className="text-xs text-muted-foreground">Boss</div>
                  <div className="h-2 w-40 overflow-hidden rounded bg-muted">
                    <div
                      className="h-full bg-destructive"
                      style={{ width: `${Math.max(0, Math.min(1, hud.bossHp / hud.bossHpMax)) * 100}%` }}
                    />
                  </div>
                </div>
              ) : null}
              <div className="mt-2 flex items-center justify-between gap-3 text-xs">
                <span className="text-muted-foreground">Energia</span>
                <span className="font-mono">{hud.energy}</span>
              </div>
              <div className="flex items-center justify-between gap-3 text-xs">
                <span className="text-muted-foreground">Bombas</span>
                <span className="font-mono">{hud.bombCount}</span>
              </div>
              <div className="flex items-center justify-between gap-3 text-xs">
                <span className="text-muted-foreground">Dash CD</span>
                <span className="font-mono">{hud.dashCd.toFixed(1)}s</span>
              </div>
              <div className="flex items-center justify-between gap-3 text-xs">
                <span className="text-muted-foreground">Especial CD</span>
                <span className="font-mono">{hud.specialCd.toFixed(1)}s</span>
              </div>
            </div>
          </div>

          {/* Start/GameOver label */}
          {(hud.phase === "start" || hud.phase === "gameover") && (
            <div className="pointer-events-none absolute inset-0 grid place-items-center">
              <div className="rounded-lg bg-card/80 backdrop-blur px-5 py-4 text-center shadow animate-enter">
                <div className="text-lg font-semibold text-foreground">
                  {hud.phase === "start" ? "Pressione Enter" : "Game Over"}
                </div>
                <div className="mt-1 text-sm text-muted-foreground">
                  {hud.phase === "start" ? "para iniciar" : "Pressione R (ou Enter) para reiniciar"}
                </div>
              </div>
            </div>
          )}
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium text-foreground">Upgrades (1–8)</div>
              <div className="text-xs text-muted-foreground">Gaste energia sem pausar</div>
            </div>
            <Badge variant="outline">8 tipos</Badge>
          </div>
          <Separator className="my-3" />
          <div className="space-y-2">
            {hud.upgrades?.map((u: any, idx: number) => (
              <div key={u.id} className="flex items-center justify-between gap-3 rounded-md border border-border/60 px-3 py-2">
                <div className="min-w-0">
                  <div className="text-sm text-foreground truncate">
                    <span className="font-mono text-muted-foreground mr-2">{idx + 1}</span>
                    {u.name}
                  </div>
                  <div className="text-xs text-muted-foreground">Lv {u.level}/{u.maxLevel}</div>
                </div>
                <div className="text-xs font-mono text-muted-foreground">{u.cost === 0 ? "MAX" : `${u.cost}`}</div>
              </div>
            ))}
          </div>

          <Separator className="my-3" />
          <div className="text-xs text-muted-foreground">
            Dica: acumule energia destruindo inimigos e use 1–8 para comprar.
          </div>

          <div className="mt-4">
            <Button asChild variant="outline" className="w-full">
              <a href="/games">Voltar</a>
            </Button>
          </div>
        </Card>
      </main>
    </div>
  );
}
