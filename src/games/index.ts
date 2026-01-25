import type { GameDefinition } from "./types";
import { buildSpaceOperaParallaxShmupSpec } from "./space-opera-parallax-shmup";

export const GAMES: GameDefinition[] = [
  {
    id: "stellar-vanguard",
    title: "Stellar Vanguard",
    tagline: "Shmup espacial completo (standalone) + demo Ordax",
    description:
      "Runner standalone (Canvas 2D) com dash, bomba, especial, upgrades (8) e boss. Também pode ser carregado no Studio como demo Ordax.",
    buildSpec: buildSpaceOperaParallaxShmupSpec,
    play: { kind: "standalone", route: "/games/play/stellar-vanguard" },
    docPath: "games/01-space-opera-parallax-shmup.md",
  },
  {
    id: "space-opera-parallax-shmup",
    title: "Space Opera Parallax Shmup",
    tagline: "Shmup vertical com parallax profundo (MVP 1 bioma)",
    description:
      "Sobreviva o máximo possível em uma nebulosa vibrante. Inimigos escalam por wave, powerups aparecem, HUD e restart rápido inclusos.",
    buildSpec: buildSpaceOperaParallaxShmupSpec,
    docPath: "games/01-space-opera-parallax-shmup.md",
  },
];

export function getGameById(id: string | null | undefined): GameDefinition | undefined {
  if (!id) return undefined;
  return GAMES.find((g) => g.id === id);
}
