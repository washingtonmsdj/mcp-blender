// Juice System - Visual feedback and game feel
import type { OrdaxEntity } from "../types";

// Helper function for lerp
function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

// Visual effect types
type VisualEffect = {
  id: string;
  type: "flash" | "particle" | "shake" | "fade";
  entityId?: string;
  x: number;
  y: number;
  duration: number;
  elapsed: number;
  data: any;
};

export class JuiceSystem {
  private effects: VisualEffect[] = [];
  private screenShake = { x: 0, y: 0, intensity: 0, duration: 0 };
  private previousHealth: Map<string, number> = new Map();
  private previousScore: number = 0;
  private scoreAnimationTime: number = 0;
  private gameOverFade: number = 0;

  update(dt: number, entities: OrdaxEntity[], scoreSystem?: any, gameState?: string) {
    // Update visual effects
    this.updateEffects(dt);

    // Update screen shake
    this.updateScreenShake(dt);

    // Player acceleration (lerp velocity)
    this.updatePlayerAcceleration(dt, entities);

    // Clamp player to bounds
    this.clampPlayerToBounds(entities);

    // Track health changes for blink effect
    this.trackHealthChanges(entities);

    // Track score changes for animation
    if (scoreSystem) {
      this.trackScoreChanges(scoreSystem);
    }

    // Game over fade
    if (gameState === "GAME_OVER") {
      this.gameOverFade = Math.min(1, this.gameOverFade + dt * 2);
    } else {
      this.gameOverFade = 0;
    }
  }

  private updateEffects(dt: number) {
    // Update all effects
    for (let i = this.effects.length - 1; i >= 0; i--) {
      const effect = this.effects[i];
      effect.elapsed += dt;

      if (effect.elapsed >= effect.duration) {
        this.effects.splice(i, 1);
      }
    }
  }

  private updateScreenShake(dt: number) {
    if (this.screenShake.duration > 0) {
      this.screenShake.duration -= dt;
      
      if (this.screenShake.duration <= 0) {
        this.screenShake.x = 0;
        this.screenShake.y = 0;
        this.screenShake.intensity = 0;
      } else {
        // Random shake
        const intensity = this.screenShake.intensity * (this.screenShake.duration / 0.2);
        this.screenShake.x = (Math.random() - 0.5) * intensity;
        this.screenShake.y = (Math.random() - 0.5) * intensity;
      }
    }
  }

  private updatePlayerAcceleration(dt: number, entities: OrdaxEntity[]) {
    const player = entities.find((e) => e.type === "player");
    if (!player || !player.props) return;

    // Smooth acceleration (lerp)
    const lerpFactor = 0.15; // Lower = smoother, higher = snappier
    
    if (!player.props._targetVx) player.props._targetVx = player.props.vx || 0;
    if (!player.props._targetVy) player.props._targetVy = player.props.vy || 0;
    if (!player.props._currentVx) player.props._currentVx = 0;
    if (!player.props._currentVy) player.props._currentVy = 0;

    // Store target velocity
    player.props._targetVx = player.props.vx || 0;
    player.props._targetVy = player.props.vy || 0;

    // Lerp current velocity toward target
    player.props._currentVx = lerp(
      Number(player.props._currentVx), 
      Number(player.props._targetVx), 
      lerpFactor
    );
    player.props._currentVy = lerp(
      Number(player.props._currentVy), 
      Number(player.props._targetVy), 
      lerpFactor
    );

    // Apply smoothed velocity
    player.props.vx = player.props._currentVx;
    player.props.vy = player.props._currentVy;
  }

  private clampPlayerToBounds(entities: OrdaxEntity[]) {
    const player = entities.find((e) => e.type === "player");
    if (!player) return;

    const bounds = { width: 800, height: 600, padding: 20 };

    // Smooth clamp with slight bounce
    if (player.x < bounds.padding) {
      player.x = bounds.padding;
      if (player.props) player.props.vx = Math.abs(Number(player.props.vx) || 0) * 0.5;
    }
    if (player.x > bounds.width - bounds.padding) {
      player.x = bounds.width - bounds.padding;
      if (player.props) player.props.vx = -Math.abs(Number(player.props.vx) || 0) * 0.5;
    }
    if (player.y < bounds.padding) {
      player.y = bounds.padding;
      if (player.props) player.props.vy = Math.abs(Number(player.props.vy) || 0) * 0.5;
    }
    if (player.y > bounds.height - bounds.padding) {
      player.y = bounds.height - bounds.padding;
      if (player.props) player.props.vy = -Math.abs(Number(player.props.vy) || 0) * 0.5;
    }
  }

  private trackHealthChanges(entities: OrdaxEntity[]) {
    for (const entity of entities) {
      if (!entity.props || entity.props.health === undefined) continue;

      const currentHealth = Number(entity.props.health);
      const previousHealth = this.previousHealth.get(entity.id);

      if (previousHealth !== undefined && currentHealth < previousHealth) {
        // Health decreased - add flash effect
        this.addFlashEffect(entity);

        // Add knockback for player
        if (entity.type === "player") {
          this.addKnockback(entity, 50);
          this.addScreenShake(5, 0.15);
        }
      }

      this.previousHealth.set(entity.id, currentHealth);
    }
  }

  private trackScoreChanges(scoreSystem: any) {
    const currentScore = scoreSystem.getScore();
    
    if (currentScore > this.previousScore) {
      this.scoreAnimationTime = 0.5; // Animate for 0.5 seconds
    }

    if (this.scoreAnimationTime > 0) {
      this.scoreAnimationTime -= 0.016; // Assuming 60 FPS
    }

    this.previousScore = currentScore;
  }

  // Add flash effect to entity
  addFlashEffect(entity: OrdaxEntity) {
    this.effects.push({
      id: `flash_${Date.now()}_${Math.random()}`,
      type: "flash",
      entityId: entity.id,
      x: entity.x,
      y: entity.y,
      duration: 0.1,
      elapsed: 0,
      data: { color: "#fff" },
    });
  }

  // Add particle effect
  addParticleEffect(x: number, y: number, color: string, count: number = 8) {
    for (let i = 0; i < count; i++) {
      const angle = (Math.PI * 2 * i) / count;
      const speed = 50 + Math.random() * 50;
      
      this.effects.push({
        id: `particle_${Date.now()}_${i}`,
        type: "particle",
        x,
        y,
        duration: 0.5,
        elapsed: 0,
        data: {
          vx: Math.cos(angle) * speed,
          vy: Math.sin(angle) * speed,
          color,
          size: 2 + Math.random() * 2,
        },
      });
    }
  }

  // Add knockback to entity
  addKnockback(entity: OrdaxEntity, force: number) {
    if (!entity.props) return;

    // Apply knockback in opposite direction of velocity
    const vx = Number(entity.props.vx) || 0;
    const vy = Number(entity.props.vy) || 0;
    const length = Math.hypot(vx, vy);

    if (length > 0) {
      entity.props.vx = (Number(entity.props.vx) || 0) - (vx / length) * force;
      entity.props.vy = (Number(entity.props.vy) || 0) - (vy / length) * force;
    }
  }

  // Add screen shake
  addScreenShake(intensity: number, duration: number) {
    this.screenShake.intensity = intensity;
    this.screenShake.duration = duration;
  }

  // Add recoil to player when shooting
  addShootRecoil(player: OrdaxEntity) {
    if (!player.props) return;

    // Small recoil downward (opposite of bullet direction)
    player.props.vy = (Number(player.props.vy) || 0) + 20;
    
    // Tiny screen shake
    this.addScreenShake(2, 0.05);
  }

  // Add death effect
  addDeathEffect(entity: OrdaxEntity) {
    const color = String(entity.props?.color || "#f00");
    this.addParticleEffect(entity.x, entity.y, color, 12);
    
    if (entity.type === "enemy") {
      this.addScreenShake(3, 0.1);
    } else if (entity.type === "player") {
      this.addScreenShake(10, 0.3);
    }
  }

  // Render effects
  render(ctx: CanvasRenderingContext2D, entities: OrdaxEntity[]) {
    // Apply screen shake
    ctx.save();
    ctx.translate(this.screenShake.x, this.screenShake.y);

    // Render flash effects
    for (const effect of this.effects) {
      if (effect.type === "flash" && effect.entityId) {
        const entity = entities.find((e) => e.id === effect.entityId);
        if (entity) {
          const alpha = 1 - effect.elapsed / effect.duration;
          ctx.fillStyle = `rgba(255, 255, 255, ${alpha * 0.7})`;
          ctx.fillRect(
            entity.x - entity.w / 2 - 2,
            entity.y - entity.h / 2 - 2,
            entity.w + 4,
            entity.h + 4
          );
        }
      }

      if (effect.type === "particle") {
        const alpha = 1 - effect.elapsed / effect.duration;
        const x = effect.x + effect.data.vx * effect.elapsed;
        const y = effect.y + effect.data.vy * effect.elapsed;
        
        ctx.fillStyle = effect.data.color;
        ctx.globalAlpha = alpha;
        ctx.fillRect(x - effect.data.size / 2, y - effect.data.size / 2, effect.data.size, effect.data.size);
        ctx.globalAlpha = 1;
      }
    }

    ctx.restore();
  }

  // Render UI effects
  renderUIEffects(ctx: CanvasRenderingContext2D, entities: OrdaxEntity[], scoreSystem?: any) {
    const player = entities.find((e) => e.type === "player");
    if (!player || !player.props) return;

    const padding = 10;
    const barWidth = 200;
    const barHeight = 20;

    // Health blink effect
    const health = Number(player.props.health) || 0;
    const previousHealth = this.previousHealth.get(player.id) || health;
    
    if (health < previousHealth) {
      const blinkTime = 0.2;
      const timeSinceHit = Date.now() / 1000 - (Number(player.props._lastHitTime) || 0);
      
      if (timeSinceHit < blinkTime) {
        const alpha = Math.sin(timeSinceHit * 30) * 0.5 + 0.5;
        ctx.fillStyle = `rgba(255, 0, 0, ${alpha * 0.3})`;
        ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);
      }
    }

    // Score animation
    if (this.scoreAnimationTime > 0 && scoreSystem) {
      const scale = 1 + (this.scoreAnimationTime / 0.5) * 0.2;
      const alpha = this.scoreAnimationTime / 0.5;
      
      ctx.save();
      ctx.translate(padding, padding + barHeight + 40);
      ctx.scale(scale, scale);
      ctx.fillStyle = `rgba(255, 215, 0, ${alpha})`;
      ctx.font = "bold 16px monospace";
      ctx.textAlign = "left";
      ctx.fillText(`+10`, 100, 0);
      ctx.restore();
    }

    // Game over fade
    if (this.gameOverFade > 0) {
      ctx.fillStyle = `rgba(0, 0, 0, ${this.gameOverFade * 0.8})`;
      ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);
    }
  }

  // Get screen shake offset
  getScreenShake(): { x: number; y: number } {
    return { x: this.screenShake.x, y: this.screenShake.y };
  }

  // Check if entity should flash
  shouldFlash(entityId: string): boolean {
    return this.effects.some((e) => e.type === "flash" && e.entityId === entityId);
  }

  // Clear all effects
  clear() {
    this.effects = [];
    this.screenShake = { x: 0, y: 0, intensity: 0, duration: 0 };
    this.previousHealth.clear();
    this.previousScore = 0;
    this.scoreAnimationTime = 0;
    this.gameOverFade = 0;
  }
}
