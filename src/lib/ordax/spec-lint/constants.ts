export const ORDAX_ALLOWED_SYSTEMS = [
  "PhysicsSystem",
  "CollisionSystem",
  "ParticleSystem",
  "AnimationSystem",
  "AudioSystem",
  "CameraSystem",
  "AISystem",
  "SpawnerSystem",
  "ScoreSystem",
  "UISystem",
  "TimerSystem",
  "DialogueSystem",
  "InventorySystem",
  "SaveSystem",
] as const;

export type OrdaxAllowedSystem = (typeof ORDAX_ALLOWED_SYSTEMS)[number];

export const WORLD_BOUNDS = { w: 800, h: 600 } as const;

export const COMMON_SYSTEM_ALIASES: Record<string, OrdaxAllowedSystem> = {
  movementsystem: "PhysicsSystem",
  inputsystem: "UISystem",
  rendersystem: "UISystem",
  hudsystem: "UISystem",
  scoringsystem: "ScoreSystem",
  spawningsystem: "SpawnerSystem",
  enemysystem: "AISystem",
};
