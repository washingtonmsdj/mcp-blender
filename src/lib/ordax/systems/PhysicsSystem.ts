// Physics System - Complete implementation with forces, friction, mass
export type Vector2 = {
  x: number;
  y: number;
};

export type PhysicsComponent = {
  vx: number;
  vy: number;
  ax: number;
  ay: number;
  mass: number;
  friction: number;
  restitution: number;
  forces: Vector2[];
  grounded: boolean;
  maxVelocity?: Vector2;
};

export class PhysicsSystem {
  private components: Map<string, PhysicsComponent> = new Map();

  // Register entity with physics
  register(
    entityId: string,
    mass: number = 1,
    friction: number = 0.1,
    restitution: number = 0.5
  ) {
    this.components.set(entityId, {
      vx: 0,
      vy: 0,
      ax: 0,
      ay: 0,
      mass,
      friction,
      restitution,
      forces: [],
      grounded: false,
    });
  }

  // Unregister entity
  unregister(entityId: string) {
    this.components.delete(entityId);
  }

  // Apply force (F = ma)
  applyForce(entityId: string, fx: number, fy: number) {
    const comp = this.components.get(entityId);
    if (comp) {
      comp.forces.push({ x: fx, y: fy });
    }
  }

  // Apply impulse (instant velocity change)
  applyImpulse(entityId: string, ix: number, iy: number) {
    const comp = this.components.get(entityId);
    if (!comp) return;
    comp.vx += ix / comp.mass;
    comp.vy += iy / comp.mass;
  }

  // Set velocity
  setVelocity(entityId: string, vx: number, vy: number) {
    const comp = this.components.get(entityId);
    if (comp) {
      comp.vx = vx;
      comp.vy = vy;
    }
  }

  // Get velocity
  getVelocity(entityId: string): Vector2 | null {
    const comp = this.components.get(entityId);
    return comp ? { x: comp.vx, y: comp.vy } : null;
  }

  // Set max velocity
  setMaxVelocity(entityId: string, maxVx: number, maxVy: number) {
    const comp = this.components.get(entityId);
    if (comp) {
      comp.maxVelocity = { x: maxVx, y: maxVy };
    }
  }

  // Set grounded state
  setGrounded(entityId: string, grounded: boolean) {
    const comp = this.components.get(entityId);
    if (comp) {
      comp.grounded = grounded;
    }
  }

  // Check if grounded
  isGrounded(entityId: string): boolean {
    return this.components.get(entityId)?.grounded ?? false;
  }

  // Update physics
  update(dt: number, entities: any[], gravity: Vector2) {
    for (const [id, comp] of this.components) {
      const entity = entities.find((e) => e.id === id);
      if (!entity) continue;

      // Sum all forces
      let fx = 0;
      let fy = 0;
      comp.forces.forEach((f) => {
        fx += f.x;
        fy += f.y;
      });
      comp.forces = [];

      // Add gravity force (F = mg)
      fx += gravity.x * comp.mass;
      fy += gravity.y * comp.mass;

      // Calculate acceleration (F = ma -> a = F/m)
      comp.ax = fx / comp.mass;
      comp.ay = fy / comp.mass;

      // Update velocity
      comp.vx += comp.ax * dt;
      comp.vy += comp.ay * dt;

      // Apply friction
      if (comp.grounded) {
        comp.vx *= 1 - comp.friction;
      } else {
        // Air resistance (less friction)
        comp.vx *= 1 - comp.friction * 0.1;
        comp.vy *= 1 - comp.friction * 0.1;
      }

      // Clamp to max velocity
      if (comp.maxVelocity) {
        comp.vx = Math.max(
          -comp.maxVelocity.x,
          Math.min(comp.maxVelocity.x, comp.vx)
        );
        comp.vy = Math.max(
          -comp.maxVelocity.y,
          Math.min(comp.maxVelocity.y, comp.vy)
        );
      }

      // Update position
      entity.x += comp.vx * dt;
      entity.y += comp.vy * dt;
    }
  }

  // Get component
  getComponent(entityId: string): PhysicsComponent | null {
    return this.components.get(entityId) ?? null;
  }

  // Clear all
  clear() {
    this.components.clear();
  }
}
