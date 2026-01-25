// World - Main ECS container

import { EntityManager } from "./EntityManager";
import { ComponentManager } from "./ComponentManager";
import type { Component } from "./Component";

export class World {
  public entityManager: EntityManager;
  public componentManager: ComponentManager;

  constructor() {
    this.entityManager = new EntityManager();
    this.componentManager = new ComponentManager();
  }

  // Entity operations
  createEntity(name?: string): string {
    return this.entityManager.createEntity(name);
  }

  destroyEntity(entityId: string): void {
    this.componentManager.removeAllComponents(entityId);
    this.entityManager.destroyEntity(entityId);
  }

  hasEntity(entityId: string): boolean {
    return this.entityManager.hasEntity(entityId);
  }

  getAllEntities(): string[] {
    return this.entityManager.getAllEntities();
  }

  // Component operations
  addComponent(entityId: string, component: Component): void {
    if (!this.hasEntity(entityId)) {
      throw new Error(`Entity ${entityId} does not exist`);
    }
    this.componentManager.addComponent(entityId, component);
  }

  removeComponent(entityId: string, componentType: string): void {
    this.componentManager.removeComponent(entityId, componentType);
  }

  getComponent<T extends Component>(entityId: string, componentType: string): T | null {
    return this.componentManager.getComponent<T>(entityId, componentType);
  }

  hasComponent(entityId: string, componentType: string): boolean {
    return this.componentManager.hasComponent(entityId, componentType);
  }

  getAllComponents(entityId: string): Component[] {
    return this.componentManager.getAllComponents(entityId);
  }

  // Query operations
  query(...componentTypes: string[]): string[] {
    return this.componentManager.getEntitiesWithComponents(...componentTypes);
  }

  queryAny(...componentTypes: string[]): string[] {
    return this.componentManager.getEntitiesWithAnyComponent(...componentTypes);
  }

  // Utility
  clear(): void {
    this.componentManager.clear();
    this.entityManager.clear();
  }

  getStats() {
    return {
      entities: this.entityManager.getEntityCount(),
      components: this.componentManager.getComponentCount(),
    };
  }
}
