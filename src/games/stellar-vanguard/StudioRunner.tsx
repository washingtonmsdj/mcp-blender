import { useEffect, useMemo, useRef, useState } from "react";
import type { GamePhase } from "./types";
import { StellarVanguardGame } from "./game";
import { Renderer } from "./renderer";

/**
 * Runner embutido para o Studio (sem layout de página, só canvas + overlay leve).
 * Mantém o jogo code-first rodando dentro do PreviewPanel.
 */
export function StellarVanguardStudioRunner() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const rafRef = useRef<number>(0);
  const lastTRef = useRef<number>(0);
  const gameRef = useRef<StellarVanguardGame | null>(null);
  const rendererRef = useRef<Renderer | null>(null);

  type HudState = {
    phase: GamePhase;
    biomeName: string;
    score: number;
    hp: number;
    wave: number;
    bossActive: boolean;
  };

  const [hud, setHud] = useState<HudState>(() => ({
    phase: "start",
    biomeName: "Nebulosa Colorida",
    score: 0,
    hp: 100,
    wave: 1,
    bossActive: false,
  }));

  const help = useMemo(
    () => "WASD/Setas • SPACE tiro • SHIFT dash • E especial • Q bomba • Enter iniciar • R reiniciar • 1-8 upgrades",
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
    renderer.initStars(420);
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

      renderer.beginWorld(w, h);
      renderer.drawParticles(snapshot.particles);
      for (const p of snapshot.pickups) if (p.alive) renderer.drawPickup(p.x, p.y, p.r, biome.theme);
      for (const e of snapshot.enemies) if (e.alive) renderer.drawEnemy(e.x, e.y, e.w, e.h, biome.theme, e.kind);
      for (const b of snapshot.bullets) if (b.alive) renderer.drawBullet(b.x, b.y, b.r, biome.theme, b.owner);
      renderer.drawShip(snapshot.player.x, snapshot.player.y, biome.theme, snapshot.player.dashTime > 0);
      renderer.endWorld();

      if (t % 2 < 1) {
        const h0 = game.getHud();
        setHud({
          phase: h0.phase,
          biomeName: h0.biomeName,
          score: h0.score,
          hp: h0.hp,
          wave: h0.wave,
          bossActive: h0.bossActive,
        });
      }

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

  return (
    <div className="relative h-full w-full">
      <canvas ref={canvasRef} className="h-full w-full" />

      <div className="pointer-events-none absolute left-3 top-3 right-3 flex items-start justify-between gap-3">
        <div className="pointer-events-auto rounded-md bg-card/70 backdrop-blur px-3 py-2 text-xs text-card-foreground shadow">
          <div className="font-medium">{hud.biomeName} • Wave {hud.wave}</div>
          <div className="mt-1 text-muted-foreground">{help}</div>
        </div>
        <div className="pointer-events-auto rounded-md bg-card/70 backdrop-blur px-3 py-2 text-xs text-card-foreground shadow">
          <div className="flex items-center justify-between gap-3">
            <span className="text-muted-foreground">Score</span>
            <span className="font-mono">{hud.score}</span>
          </div>
          <div className="flex items-center justify-between gap-3">
            <span className="text-muted-foreground">HP</span>
            <span className="font-mono">{hud.hp}</span>
          </div>
        </div>
      </div>

      {(hud.phase === "start" || hud.phase === "gameover") && (
        <div className="pointer-events-none absolute inset-0 grid place-items-center">
          <div className="rounded-lg bg-card/80 backdrop-blur px-5 py-4 text-center shadow">
            <div className="text-base font-semibold text-foreground">
              {hud.phase === "start" ? "Pressione Enter" : "Game Over"}
            </div>
            <div className="mt-1 text-sm text-muted-foreground">
              {hud.phase === "start" ? "para iniciar" : "Pressione R (ou Enter) para reiniciar"}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
