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

// NEW: Top-Down Shooter Systems
export { InputSystem } from "./InputSystem";
export type { InputState } from "./InputSystem";

export { SpawnerSystem } from "./SpawnerSystem";

export { CombatSystem } from "./CombatSystem";
export type { DamageEvent } from "./CombatSystem";

export { GameStateSystem } from "./GameStateSystem";
export type { GameState, GameStateEvent } from "./GameStateSystem";

// NEW: Juice & Feel Systems (Fase 5)
export { JuiceSystem } from "./JuiceSystem";

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
  "CombatSystem",
  "GameStateSystem",
  "ScoreSystem",
  "UISystem",
  "TimerSystem",
  "DialogueSystem",
  "InventorySystem",
  "SaveSystem",
  "JuiceSystem",
] as const;

export type OrdaxSystemName = typeof ORDAX_SYSTEMS[number];
