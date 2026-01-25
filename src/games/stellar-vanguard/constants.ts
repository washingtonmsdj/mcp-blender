export const WORLD = { w: 800, h: 600 } as const;

export const KEYS = {
  up: ["ArrowUp", "w", "W"],
  down: ["ArrowDown", "s", "S"],
  left: ["ArrowLeft", "a", "A"],
  right: ["ArrowRight", "d", "D"],
  shoot: [" "],
  dash: ["Shift"],
  special: ["e", "E"],
  bomb: ["q", "Q"],
} as const;
