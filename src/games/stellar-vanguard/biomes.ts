import type { BiomeId, ParallaxLayer, Theme } from "./types";

export const BIOMES: Record<BiomeId, { theme: Theme; layers: ParallaxLayer[]; name: string }> = {
  nebula: {
    name: "Nebulosa Colorida",
    theme: {
      bg: "hsl(240, 60%, 6%)",
      primary: "hsl(190, 100%, 55%)",
      accent: "hsl(295, 85%, 62%)",
      gold: "hsl(45, 95%, 55%)",
      danger: "hsl(0, 84%, 60%)",
      text: "hsl(0, 0%, 98%)",
    },
    layers: [
      { kind: "stars", speed: 28, alpha: 0.85, scale: 1 },
      { kind: "stars", speed: 52, alpha: 0.55, scale: 1 },
      { kind: "nebula", speed: 18, alpha: 0.28, scale: 1 },
      { kind: "planet", speed: 10, alpha: 0.30, scale: 1 },
      { kind: "debris", speed: 92, alpha: 0.22, scale: 1 },
    ],
  },
  asteroid: {
    name: "Cinturão de Asteroides",
    theme: {
      bg: "hsl(220, 38%, 6%)",
      primary: "hsl(38, 92%, 55%)",
      accent: "hsl(200, 90%, 55%)",
      gold: "hsl(45, 95%, 55%)",
      danger: "hsl(0, 84%, 60%)",
      text: "hsl(0, 0%, 98%)",
    },
    layers: [
      { kind: "stars", speed: 32, alpha: 0.8 },
      { kind: "fog", speed: 14, alpha: 0.18 },
      { kind: "debris", speed: 110, alpha: 0.26 },
      { kind: "planet", speed: 10, alpha: 0.24 },
      { kind: "fog", speed: 22, alpha: 0.12 },
    ],
  },
  tech: {
    name: "Território Tecnológico",
    theme: {
      bg: "hsl(230, 55%, 6%)",
      primary: "hsl(170, 90%, 52%)",
      accent: "hsl(320, 90%, 62%)",
      gold: "hsl(45, 95%, 55%)",
      danger: "hsl(0, 84%, 60%)",
      text: "hsl(0, 0%, 98%)",
    },
    layers: [
      { kind: "stars", speed: 36, alpha: 0.78 },
      { kind: "fog", speed: 18, alpha: 0.14 },
      { kind: "nebula", speed: 22, alpha: 0.22 },
      { kind: "planet", speed: 12, alpha: 0.22 },
      { kind: "debris", speed: 96, alpha: 0.18 },
    ],
  },
};
