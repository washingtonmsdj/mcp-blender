// ECS System - Export all

export { World } from "./World";
export { EntityManager } from "./EntityManager";
export { ComponentManager } from "./ComponentManager";

export type {
  Component,
  Position,
  Velocity,
  Size,
  Health,
  Sprite,
  Physics,
  Collider,
  Tag,
  AI,
  Score,
} from "./Component";

export {
  createPosition,
  createVelocity,
  createSize,
  createHealth,
  createSprite,
  createPhysics,
  createCollider,
  createTag,
  createAI,
  createScore,
} from "./Component";
