// Combat System - Handles damage and death
import type { OrdaxEntity } from "../types";

export type DamageEvent = {
  attacker: OrdaxEntity;
  target: OrdaxEntity;
  damage: number;
  timestamp: number;
};

export class CombatSystem {
  private damageEvents: DamageEvent[] = [];
  private entitiesToRemove: Set<string> = new Set();

  update(dt: number, entities: OrdaxEntity[]) {
    // Process damage events
    this.processDamageEvents(entities);

    // Check for dead entities
    this.checkDeaths(entities);

    // Remove dead entities
    this.removeDeadEntities(entities);
  }

  // Apply damage to an entity
  applyDamage(attacker: OrdaxEntity, target: OrdaxEntity, damage: number) {
    if (!target.props) return;

    // Reduce health
    const currentHealth = target.props.health || 0;
    target.props.health = Math.max(0, currentHealth - damage);

    // Mark time of hit for juice effects
    target.props._lastHitTime = Date.now() / 1000;

    // Record event
    this.damageEvents.push({
      attacker,
      target,
      damage,
      timestamp: Date.now(),
    });
  }

  // Handle collision damage
  handleCollisionDamage(entityA: OrdaxEntity, entityB: OrdaxEntity) {
    // Bullet hits enemy
    if (entityA.type === "bullet" && entityB.type === "enemy") {
      const damage = entityA.props?.damage || 25;
      this.applyDamage(entityA, entityB, damage);
      this.markForRemoval(entityA.id); // Remove bullet
    }

    // Enemy hits player
    if (entityA.type === "enemy" && entityB.type === "player") {
      const damage = entityA.props?.contactDamage || entityA.props?.damage || 10;
      this.applyDamage(entityA, entityB, damage);
    }

    // Player hits enemy (melee)
    if (entityA.type === "player" && entityB.type === "enemy") {
      const damage = entityA.props?.meleeDamage || 0;
      if (damage > 0) {
        this.applyDamage(entityA, entityB, damage);
      }
    }
  }

  private processDamageEvents(entities: OrdaxEntity[]) {
    // Keep only recent events (last 5 seconds)
    const now = Date.now();
    this.damageEvents = this.damageEvents.filter((e) => now - e.timestamp < 5000);
  }

  private checkDeaths(entities: OrdaxEntity[]) {
    for (const entity of entities) {
      if (!entity.props) continue;

      const health = entity.props.health;
      if (health !== undefined && health <= 0) {
        // Mark for death effect before removal
        entity.props._justDied = true;
        
        this.markForRemoval(entity.id);

        // Award score if enemy died
        if (entity.type === "enemy" && entity.props.scoreValue) {
          // Score will be handled by ScoreSystem
        }
      }
    }
  }

  private removeDeadEntities(entities: OrdaxEntity[]) {
    // Remove entities marked for removal
    for (let i = entities.length - 1; i >= 0; i--) {
      if (this.entitiesToRemove.has(entities[i].id)) {
        entities.splice(i, 1);
      }
    }

    // Clear removal set
    this.entitiesToRemove.clear();
  }

  // Mark entity for removal
  markForRemoval(entityId: string) {
    this.entitiesToRemove.add(entityId);
  }

  // Get damage events
  getDamageEvents(): DamageEvent[] {
    return [...this.damageEvents];
  }

  // Check if entity is marked for removal
  isMarkedForRemoval(entityId: string): boolean {
    return this.entitiesToRemove.has(entityId);
  }

  // Clear all
  clear() {
    this.damageEvents = [];
    this.entitiesToRemove.clear();
  }
}
