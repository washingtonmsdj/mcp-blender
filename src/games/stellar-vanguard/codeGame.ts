import { defineGame } from "@/games/_template";

/**
 * Code-first module (fonte de verdade). Por enquanto, o setup registra um “snapshot” mínimo
 * para projetar um runtimeSpec Ordax derivado.
 */
export const stellarVanguardCodeGame = defineGame({
  meta: {
    id: "stellar-vanguard",
    title: "Stellar Vanguard",
    description: "Shmup espacial completo (code-first). runtimeSpec é derivado do código.",
    gameType: "shooter",
  },
  setup: ({ collector }) => {
    if (!collector) return;

    collector.setGravity({ x: 0, y: 0 });
    collector.setVisual({
      theme: {
        background: "hsl(220, 45%, 6%)",
        primary: "hsl(190, 95%, 55%)",
        accent: "hsl(300, 90%, 60%)",
      },
      background: {
        layers: [
          { type: "solid", parallax: 0 },
          { type: "starfield", parallax: 0.08, density: 0.9, speedY: 20 },
          { type: "nebula", parallax: 0.18, density: 0.6, speedY: 30 },
          { type: "gradient", parallax: 0.25 },
          { type: "starfield", parallax: 0.5, density: 0.4, speedY: 70 },
        ],
      },
    });

    // Systems “projetados” (mapeiam para o runtime JSON engine atual)
    collector.useSystem("PhysicsSystem");
    collector.useSystem("CollisionSystem");
    collector.useSystem("ParticleSystem");
    collector.useSystem("ScoreSystem");
    collector.useSystem("TimerSystem");
    collector.useSystem("AISystem");
    collector.useSystem("UISystem");
    collector.useSystem("AudioSystem");

    collector.addEntity({
      id: "player",
      type: "player",
      x: 400,
      y: 480,
      w: 28,
      h: 28,
      props: {
        health: 100,
        fireRate: 9,
        bulletSpeed: 520,
        // hints (não usados pelo engine JSON ainda)
        dash: true,
        bomb: true,
      },
    });
    collector.addEntity({
      id: "spawner_main",
      type: "spawner",
      x: 0,
      y: 0,
      w: 1,
      h: 1,
      props: { rate: 1.0, variants: ["scout", "tank", "sniper"] },
    });
    collector.addEntity({
      id: "ui",
      type: "ui",
      x: 0,
      y: 0,
      w: 800,
      h: 600,
      props: { showScore: true, showHealthBar: true, showShieldBar: true },
    });
  },
});
