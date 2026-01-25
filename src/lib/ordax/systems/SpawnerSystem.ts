// Spawner System - Spawns enemies periodically
import type { OrdaxEntity } from "../types";

export class SpawnerSystem {
  private lastSpawnTimes: Map<string, number> = new Map();

  update(dt: number, entities: OrdaxEntity[], currentTime: number = Date.now() / 1000) {
    // Find all spawner entities
    const spawners = entities.filter((e) => e.type === "spawner" || e.props?.spawner);

    for (const spawner of spawners) {
      if (!spawner.props) continue;

      const spawnRate = spawner.props.spawnRate || 2.0;
      const maxEnemies = spawner.props.maxEnemies || 20;
      const spawnType = spawner.props.spawnType || "enemy";

      // Check if enough time has passed
      const lastSpawn = this.lastSpawnTimes.get(spawner.id) || 0;
      if (currentTime - lastSpawn < spawnRate) continue;

      // Check if we've reached max enemies
      const currentEnemies = entities.filter((e) => e.type === spawnType).length;
      if (currentEnemies >= maxEnemies) continue;

      // Spawn enemy
      this.spawnEnemy(spawner, entities, spawnType);
      this.lastSpawnTimes.set(spawner.id, currentTime);

      // Update wave counter
      if (spawner.props.enemiesSpawned !== undefined) {
        spawner.props.enemiesSpawned++;
      }
    }
  }

  private spawnEnemy(spawner: OrdaxEntity, entities: OrdaxEntity[], spawnType: string) {
    // Find enemy template
    const enemyTemplate = entities.find((e) => e.type === spawnType && e.id.includes("template"));
    if (!enemyTemplate) {
      // If no template, find any enemy to use as template
      const anyEnemy = entities.find((e) => e.type === spawnType);
      if (!anyEnemy) return;
    }

    const template = enemyTemplate || entities.find((e) => e.type === spawnType)!;

    // Random spawn position around spawner
    const spawnRadius = spawner.props?.spawnRadius || 50;
    const angle = Math.random() * Math.PI * 2;
    const distance = Math.random() * spawnRadius;
    const x = spawner.x + Math.cos(angle) * distance;
    const y = spawner.y + Math.sin(angle) * distance;

    // Create new enemy
    const enemy: OrdaxEntity = {
      id: `${spawnType}_${Date.now()}_${Math.random()}`,
      type: spawnType,
      x,
      y,
      w: template.w,
      h: template.h,
      props: {
        ...template.props,
        x,
        y,
        vx: 0,
        vy: 0,
      },
    };

    entities.push(enemy);
  }

  // Reset spawner timers
  reset() {
    this.lastSpawnTimes.clear();
  }

  // Force spawn
  forceSpawn(spawnerId: string, entities: OrdaxEntity[]) {
    const spawner = entities.find((e) => e.id === spawnerId);
    if (!spawner) return;

    const spawnType = spawner.props?.spawnType || "enemy";
    this.spawnEnemy(spawner, entities, spawnType);
  }
}
