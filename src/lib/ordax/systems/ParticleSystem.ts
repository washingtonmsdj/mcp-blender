// Particle System
export type Particle = {
  x: number;
  y: number;
  vx: number;
  vy: number;
  life: number;
  maxLife: number;
  size: number;
  color: string;
  alpha: number;
};

export type ParticleEmitter = {
  x: number;
  y: number;
  rate: number; // particles per second
  timer: number;
  config: {
    life: number;
    speed: number;
    size: number;
    color: string;
    spread: number; // angle spread in radians
    direction: number; // base direction in radians
  };
};

export class ParticleSystem {
  private particles: Particle[] = [];
  private emitters: Map<string, ParticleEmitter> = new Map();

  // Create emitter
  createEmitter(id: string, x: number, y: number, config: ParticleEmitter["config"]): ParticleEmitter {
    const emitter: ParticleEmitter = {
      x,
      y,
      rate: 10,
      timer: 0,
      config,
    };
    
    this.emitters.set(id, emitter);
    return emitter;
  }

  // Emit particles
  emit(x: number, y: number, count: number, config: ParticleEmitter["config"]) {
    for (let i = 0; i < count; i++) {
      const angle = config.direction + (Math.random() - 0.5) * config.spread;
      const speed = config.speed * (0.8 + Math.random() * 0.4);

      this.particles.push({
        x,
        y,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        life: config.life,
        maxLife: config.life,
        size: config.size * (0.8 + Math.random() * 0.4),
        color: config.color,
        alpha: 1,
      });
    }
  }

  // Update particles
  update(dt: number) {
    // Update emitters
    for (const emitter of this.emitters.values()) {
      emitter.timer += dt;
      const interval = 1 / emitter.rate;

      while (emitter.timer >= interval) {
        emitter.timer -= interval;
        this.emit(emitter.x, emitter.y, 1, emitter.config);
      }
    }

    // Update particles
    this.particles = this.particles.filter((p) => {
      p.life -= dt;
      if (p.life <= 0) return false;

      p.x += p.vx * dt;
      p.y += p.vy * dt;
      p.vy += 100 * dt; // gravity
      p.alpha = p.life / p.maxLife;

      return true;
    });
  }

  // Render particles
  render(ctx: CanvasRenderingContext2D) {
    for (const p of this.particles) {
      ctx.save();
      ctx.globalAlpha = p.alpha;
      ctx.fillStyle = p.color;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }
  }

  // Get particle count
  getCount(): number {
    return this.particles.length;
  }

  // Clear all particles
  clear() {
    this.particles = [];
  }

  // Remove emitter
  removeEmitter(id: string) {
    this.emitters.delete(id);
  }
}
