// ECS Components - Pure data structures

export interface Component {
  type: string;
}

// Position Component
export interface Position extends Component {
  type: "Position";
  x: number;
  y: number;
}

// Velocity Component
export interface Velocity extends Component {
  type: "Velocity";
  vx: number;
  vy: number;
}

// Size Component
export interface Size extends Component {
  type: "Size";
  w: number;
  h: number;
}

// Health Component
export interface Health extends Component {
  type: "Health";
  current: number;
  max: number;
}

// Sprite Component
export interface Sprite extends Component {
  type: "Sprite";
  url: string;
  frameWidth: number;
  frameHeight: number;
  currentAnimation?: string;
}

// Physics Component
export interface Physics extends Component {
  type: "Physics";
  mass: number;
  friction: number;
  restitution: number;
  grounded: boolean;
}

// Collider Component
export interface Collider extends Component {
  type: "Collider";
  layer: string;
  isTrigger: boolean;
}

// Tag Component
export interface Tag extends Component {
  type: "Tag";
  value: string;
}

// AI Component
export interface AI extends Component {
  type: "AI";
  behavior: "idle" | "patrol" | "chase" | "flee" | "wander";
  speed: number;
  detectionRange: number;
}

// Score Component
export interface Score extends Component {
  type: "Score";
  value: number;
  multiplier: number;
}

// Helper functions
export function createPosition(x: number, y: number): Position {
  return { type: "Position", x, y };
}

export function createVelocity(vx: number, vy: number): Velocity {
  return { type: "Velocity", vx, vy };
}

export function createSize(w: number, h: number): Size {
  return { type: "Size", w, h };
}

export function createHealth(current: number, max: number): Health {
  return { type: "Health", current, max };
}

export function createSprite(
  url: string,
  frameWidth: number,
  frameHeight: number
): Sprite {
  return { type: "Sprite", url, frameWidth, frameHeight };
}

export function createPhysics(
  mass: number = 1,
  friction: number = 0.1,
  restitution: number = 0.5
): Physics {
  return { type: "Physics", mass, friction, restitution, grounded: false };
}

export function createCollider(layer: string = "default", isTrigger: boolean = false): Collider {
  return { type: "Collider", layer, isTrigger };
}

export function createTag(value: string): Tag {
  return { type: "Tag", value };
}

export function createAI(
  behavior: AI["behavior"],
  speed: number = 100,
  detectionRange: number = 200
): AI {
  return { type: "AI", behavior, speed, detectionRange };
}

export function createScore(value: number = 0, multiplier: number = 1): Score {
  return { type: "Score", value, multiplier };
}
