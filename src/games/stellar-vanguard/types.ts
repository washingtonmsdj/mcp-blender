export type Vec2 = { x: number; y: number };

export type BiomeId = "nebula" | "asteroid" | "tech";

export type UpgradeId =
  | "double_shot"
  | "spread"
  | "guided"
  | "shield"
  | "regen"
  | "fire_rate"
  | "special_cd"
  | "bomb_plus";

export type GameInput = {
  up: boolean;
  down: boolean;
  left: boolean;
  right: boolean;
  shoot: boolean;
  dash: boolean;
  special: boolean;
  bomb: boolean;
};

export type Theme = {
  bg: string;
  primary: string;
  accent: string;
  gold: string;
  danger: string;
  text: string;
};

export type ParallaxLayer = {
  kind: "stars" | "nebula" | "planet" | "debris" | "fog";
  speed: number;
  alpha: number;
  scale?: number;
};

export type PlayerState = {
  x: number;
  y: number;
  vx: number;
  vy: number;
  hp: number;
  shield: number;
  shieldMax: number;
  iFrames: number;
  dashCd: number;
  dashTime: number;
  specialCd: number;
  bombCount: number;
  energy: number;
  fireCd: number;
  fireRate: number;
  bulletSpeed: number;
  upgrades: Record<UpgradeId, number>;
};

export type EnemyKind = "light" | "medium" | "heavy" | "boss";

export type EnemyState = {
  id: number;
  kind: EnemyKind;
  x: number;
  y: number;
  w: number;
  h: number;
  vx: number;
  vy: number;
  hp: number;
  alive: boolean;
  phase?: number;
  t: number;
};

export type BulletOwner = "player" | "enemy";

export type BulletState = {
  id: number;
  owner: BulletOwner;
  x: number;
  y: number;
  vx: number;
  vy: number;
  r: number;
  dmg: number;
  alive: boolean;
  guided?: boolean;
};

export type PickupKind = "energy";

export type PickupState = {
  id: number;
  kind: PickupKind;
  x: number;
  y: number;
  vx: number;
  vy: number;
  r: number;
  value: number;
  alive: boolean;
};

export type Particle = {
  id: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
  life: number;
  maxLife: number;
  size: number;
  color: string;
  alive: boolean;
};

export type GamePhase = "start" | "playing" | "gameover";

export type GameState = {
  phase: GamePhase;
  biome: BiomeId;
  biomeTime: number;
  score: number;
  highScore: number;
  wave: number;
  bossActive: boolean;
  bossDefeated: boolean;
};
