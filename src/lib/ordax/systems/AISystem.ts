// AI System
export type AIBehavior = "idle" | "patrol" | "chase" | "flee" | "wander";

export type AIAgent = {
  id: string;
  behavior: AIBehavior;
  target: string | null;
  speed: number;
  detectionRange: number;
  patrolPoints?: { x: number; y: number }[];
  currentPatrolIndex?: number;
};

export class AISystem {
  private agents: Map<string, AIAgent> = new Map();

  register(entityId: string, behavior: AIBehavior, speed: number = 100) {
    this.agents.set(entityId, {
      id: entityId,
      behavior,
      target: null,
      speed,
      detectionRange: 200,
    });
  }

  setBehavior(entityId: string, behavior: AIBehavior) {
    const agent = this.agents.get(entityId);
    if (agent) agent.behavior = behavior;
  }

  setPatrolPoints(entityId: string, points: { x: number; y: number }[]) {
    const agent = this.agents.get(entityId);
    if (agent) {
      agent.patrolPoints = points;
      agent.currentPatrolIndex = 0;
    }
  }

  update(dt: number, entities: any[]) {
    // Process registered agents (advanced mode)
    for (const agent of this.agents.values()) {
      const entity = entities.find((e) => e.id === agent.id);
      if (!entity) continue;

      switch (agent.behavior) {
        case "chase":
          this.updateChase(agent, entity, entities, dt);
          break;
        case "flee":
          this.updateFlee(agent, entity, entities, dt);
          break;
        case "patrol":
          this.updatePatrol(agent, entity, dt);
          break;
        case "wander":
          this.updateWander(agent, entity, dt);
          break;
      }
    }

    // Process entities with props directly (simple mode - for autofilled entities)
    for (const entity of entities) {
      // Skip if already processed via agent
      if (this.agents.has(entity.id)) continue;

      // Skip if no props or no AI
      if (!entity.props || !entity.props.ai) continue;

      // Read behavior from props
      const behavior = entity.props.ai;
      const speed = entity.props.speed || 100;
      const target = entity.props.target || "player";

      // Execute behavior
      switch (behavior) {
        case "chase":
          this.updateChaseSimple(entity, entities, speed, dt);
          break;
        case "flee":
          this.updateFleeSimple(entity, entities, speed, dt);
          break;
        case "wander":
          this.updateWanderSimple(entity, speed, dt);
          break;
      }
    }
  }

  private updateChase(agent: AIAgent, entity: any, entities: any[], dt: number) {
    const target = entities.find((e) => e.type === "player" || e.id === "player");
    if (!target) return;

    const dx = target.x - entity.x;
    const dy = target.y - entity.y;
    const distance = Math.hypot(dx, dy);

    if (distance < agent.detectionRange) {
      entity.x += (dx / distance) * agent.speed * dt;
      entity.y += (dy / distance) * agent.speed * dt;
    }
  }

  private updateFlee(agent: AIAgent, entity: any, entities: any[], dt: number) {
    const target = entities.find((e) => e.type === "player" || e.id === "player");
    if (!target) return;

    const dx = entity.x - target.x;
    const dy = entity.y - target.y;
    const distance = Math.hypot(dx, dy);

    if (distance < agent.detectionRange) {
      entity.x += (dx / distance) * agent.speed * dt;
      entity.y += (dy / distance) * agent.speed * dt;
    }
  }

  private updatePatrol(agent: AIAgent, entity: any, dt: number) {
    if (!agent.patrolPoints || agent.patrolPoints.length === 0) return;

    const target = agent.patrolPoints[agent.currentPatrolIndex || 0];
    const dx = target.x - entity.x;
    const dy = target.y - entity.y;
    const distance = Math.hypot(dx, dy);

    if (distance < 10) {
      agent.currentPatrolIndex = ((agent.currentPatrolIndex || 0) + 1) % agent.patrolPoints.length;
    } else {
      entity.x += (dx / distance) * agent.speed * dt;
      entity.y += (dy / distance) * agent.speed * dt;
    }
  }

  private updateWander(agent: AIAgent, entity: any, dt: number) {
    if (!entity.wanderAngle) {
      entity.wanderAngle = Math.random() * Math.PI * 2;
      entity.wanderTimer = 0;
    }

    entity.wanderTimer += dt;
    if (entity.wanderTimer > 2) {
      entity.wanderAngle = Math.random() * Math.PI * 2;
      entity.wanderTimer = 0;
    }

    entity.x += Math.cos(entity.wanderAngle) * agent.speed * dt;
    entity.y += Math.sin(entity.wanderAngle) * agent.speed * dt;
  }

  // Simple mode methods (work with props directly)
  private updateChaseSimple(entity: any, entities: any[], speed: number, dt: number) {
    const target = entities.find((e) => e.type === "player" || e.id === "player");
    if (!target) return;

    const dx = target.x - entity.x;
    const dy = target.y - entity.y;
    const distance = Math.hypot(dx, dy);

    if (distance > 0) {
      // Update velocity in props
      if (entity.props) {
        entity.props.vx = (dx / distance) * speed;
        entity.props.vy = (dy / distance) * speed;
      }
    }
  }

  private updateFleeSimple(entity: any, entities: any[], speed: number, dt: number) {
    const target = entities.find((e) => e.type === "player" || e.id === "player");
    if (!target) return;

    const dx = entity.x - target.x;
    const dy = entity.y - target.y;
    const distance = Math.hypot(dx, dy);

    if (distance > 0) {
      // Update velocity in props
      if (entity.props) {
        entity.props.vx = (dx / distance) * speed;
        entity.props.vy = (dy / distance) * speed;
      }
    }
  }

  private updateWanderSimple(entity: any, speed: number, dt: number) {
    if (!entity.props) return;

    if (!entity.props.wanderAngle) {
      entity.props.wanderAngle = Math.random() * Math.PI * 2;
      entity.props.wanderTimer = 0;
    }

    entity.props.wanderTimer += dt;
    if (entity.props.wanderTimer > 2) {
      entity.props.wanderAngle = Math.random() * Math.PI * 2;
      entity.props.wanderTimer = 0;
    }

    entity.props.vx = Math.cos(entity.props.wanderAngle) * speed;
    entity.props.vy = Math.sin(entity.props.wanderAngle) * speed;
  }
}
