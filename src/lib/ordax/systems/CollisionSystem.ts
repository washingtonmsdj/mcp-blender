// Collision Detection System
import type { OrdaxEntity } from "../types";

export type CollisionCallback = (a: OrdaxEntity, b: OrdaxEntity) => void;

export class CollisionSystem {
  private callbacks: Map<string, CollisionCallback[]> = new Map();

  // Register collision callback
  on(typeA: string, typeB: string, callback: CollisionCallback) {
    const key = this.getKey(typeA, typeB);
    if (!this.callbacks.has(key)) {
      this.callbacks.set(key, []);
    }
    this.callbacks.get(key)!.push(callback);
  }

  // Check collisions between entities
  update(entities: OrdaxEntity[]) {
    for (let i = 0; i < entities.length; i++) {
      for (let j = i + 1; j < entities.length; j++) {
        const a = entities[i];
        const b = entities[j];

        if (this.checkCollision(a, b)) {
          this.handleCollision(a, b);
        }
      }
    }
  }

  // AABB collision detection
  private checkCollision(a: OrdaxEntity, b: OrdaxEntity): boolean {
    return (
      a.x - a.w / 2 < b.x + b.w / 2 &&
      a.x + a.w / 2 > b.x - b.w / 2 &&
      a.y - a.h / 2 < b.y + b.h / 2 &&
      a.y + a.h / 2 > b.y - b.h / 2
    );
  }

  private handleCollision(a: OrdaxEntity, b: OrdaxEntity) {
    const key = this.getKey(a.type, b.type);
    const callbacks = this.callbacks.get(key);
    
    if (callbacks) {
      callbacks.forEach((cb) => cb(a, b));
    }

    // Also check reverse
    const reverseKey = this.getKey(b.type, a.type);
    const reverseCallbacks = this.callbacks.get(reverseKey);
    
    if (reverseCallbacks) {
      reverseCallbacks.forEach((cb) => cb(b, a));
    }
  }

  private getKey(typeA: string, typeB: string): string {
    return `${typeA}:${typeB}`;
  }

  // Get collision info
  getCollisionInfo(a: OrdaxEntity, b: OrdaxEntity) {
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const distance = Math.hypot(dx, dy);
    
    return {
      distance,
      angle: Math.atan2(dy, dx),
      overlap: {
        x: (a.w + b.w) / 2 - Math.abs(dx),
        y: (a.h + b.h) / 2 - Math.abs(dy),
      },
    };
  }
}
