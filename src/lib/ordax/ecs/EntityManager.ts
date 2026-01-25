// Entity Manager - Manages entity lifecycle

export class EntityManager {
  private nextId: number = 0;
  private entities: Set<string> = new Set();
  private entityNames: Map<string, string> = new Map(); // id -> name

  // Create new entity
  createEntity(name?: string): string {
    const id = `entity_${this.nextId++}`;
    this.entities.add(id);
    if (name) {
      this.entityNames.set(id, name);
    }
    return id;
  }

  // Destroy entity
  destroyEntity(entityId: string): void {
    this.entities.delete(entityId);
    this.entityNames.delete(entityId);
  }

  // Check if entity exists
  hasEntity(entityId: string): boolean {
    return this.entities.has(entityId);
  }

  // Get all entities
  getAllEntities(): string[] {
    return Array.from(this.entities);
  }

  // Get entity count
  getEntityCount(): number {
    return this.entities.size;
  }

  // Set entity name
  setEntityName(entityId: string, name: string): void {
    if (this.entities.has(entityId)) {
      this.entityNames.set(entityId, name);
    }
  }

  // Get entity name
  getEntityName(entityId: string): string | null {
    return this.entityNames.get(entityId) ?? null;
  }

  // Find entity by name
  findEntityByName(name: string): string | null {
    for (const [id, entityName] of this.entityNames) {
      if (entityName === name) {
        return id;
      }
    }
    return null;
  }

  // Clear all entities
  clear(): void {
    this.entities.clear();
    this.entityNames.clear();
    this.nextId = 0;
  }
}
