// Component Manager - Manages all components for all entities

import type { Component } from "./Component";

export class ComponentManager {
  // Map<EntityId, Map<ComponentType, Component>>
  private components: Map<string, Map<string, Component>> = new Map();

  // Add component to entity
  addComponent(entityId: string, component: Component): void {
    if (!this.components.has(entityId)) {
      this.components.set(entityId, new Map());
    }
    this.components.get(entityId)!.set(component.type, component);
  }

  // Remove component from entity
  removeComponent(entityId: string, componentType: string): void {
    const entityComponents = this.components.get(entityId);
    if (entityComponents) {
      entityComponents.delete(componentType);
      if (entityComponents.size === 0) {
        this.components.delete(entityId);
      }
    }
  }

  // Get component from entity
  getComponent<T extends Component>(entityId: string, componentType: string): T | null {
    const entityComponents = this.components.get(entityId);
    if (!entityComponents) return null;
    return (entityComponents.get(componentType) as T) ?? null;
  }

  // Check if entity has component
  hasComponent(entityId: string, componentType: string): boolean {
    const entityComponents = this.components.get(entityId);
    return entityComponents?.has(componentType) ?? false;
  }

  // Get all components for entity
  getAllComponents(entityId: string): Component[] {
    const entityComponents = this.components.get(entityId);
    return entityComponents ? Array.from(entityComponents.values()) : [];
  }

  // Get entities with specific components
  getEntitiesWithComponents(...componentTypes: string[]): string[] {
    const result: string[] = [];
    for (const [entityId, entityComponents] of this.components) {
      if (componentTypes.every((type) => entityComponents.has(type))) {
        result.push(entityId);
      }
    }
    return result;
  }

  // Get entities with any of the components
  getEntitiesWithAnyComponent(...componentTypes: string[]): string[] {
    const result: string[] = [];
    for (const [entityId, entityComponents] of this.components) {
      if (componentTypes.some((type) => entityComponents.has(type))) {
        result.push(entityId);
      }
    }
    return result;
  }

  // Remove all components from entity
  removeAllComponents(entityId: string): void {
    this.components.delete(entityId);
  }

  // Get all entities
  getAllEntities(): string[] {
    return Array.from(this.components.keys());
  }

  // Clear all components
  clear(): void {
    this.components.clear();
  }

  // Get component count
  getComponentCount(): number {
    let count = 0;
    for (const entityComponents of this.components.values()) {
      count += entityComponents.size;
    }
    return count;
  }

  // Debug: Get all components by type
  getComponentsByType(componentType: string): Array<{ entityId: string; component: Component }> {
    const result: Array<{ entityId: string; component: Component }> = [];
    for (const [entityId, entityComponents] of this.components) {
      const component = entityComponents.get(componentType);
      if (component) {
        result.push({ entityId, component });
      }
    }
    return result;
  }
}
