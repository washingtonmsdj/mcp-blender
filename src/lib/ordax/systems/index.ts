// Ordax Engine Systems - Complete Suite

export { PhysicsSystem } from "./PhysicsSystem";
export type { PhysicsComponent, Vector2 } from "./PhysicsSystem";

export { CollisionSystem } from "./CollisionSystem";
export type { CollisionCallback } from "./CollisionSystem";

export { ParticleSystem } from "./ParticleSystem";
export type { Particle, ParticleEmitter } from "./ParticleSystem";

export { AnimationSystem } from "./AnimationSystem";
export type { Animation, AnimationFrame, AnimatedEntity } from "./AnimationSystem";

export { AudioSystem } from "./AudioSystem";
export type { Sound, Music } from "./AudioSystem";

export { CameraSystem } from "./CameraSystem";
export type { Camera } from "./CameraSystem";

export { AISystem } from "./AISystem";
export type { AIBehavior, AIAgent } from "./AISystem";

export { TimerSystem } from "./TimerSystem";
export type { Timer } from "./TimerSystem";

export { UISystem } from "./UISystem";
export type { UIElement } from "./UISystem";

export { ScoreSystem } from "./ScoreSystem";
export type { ScoreEvent } from "./ScoreSystem";

export { DialogueSystem } from "./DialogueSystem";
export type { Dialogue, DialogueLine } from "./DialogueSystem";

export { InventorySystem } from "./InventorySystem";
export type { Item, InventorySlot } from "./InventorySystem";

export { SaveSystem } from "./SaveSystem";
export type { SaveData } from "./SaveSystem";

// System Registry
export const ORDAX_SYSTEMS = [
  "InputSystem",
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

export type OrdaxSystemName = typeof ORDAX_SYSTEMS[number];
