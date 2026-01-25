import { WORLD } from "./constants";
import type { ParallaxLayer, Particle, Theme } from "./types";

type Star = { x: number; y: number; s: number; lane: number };

export class Renderer {
  private stars: Star[] = [];
  private scroll = 0;

  constructor(private ctx: CanvasRenderingContext2D) {}

  resizeToFit() {
    const canvas = this.ctx.canvas;
    const rect = canvas.getBoundingClientRect();
    const dpr = Math.max(1, Math.floor(window.devicePixelRatio || 1));
    const w = Math.max(1, Math.floor(rect.width));
    const h = Math.max(1, Math.floor(rect.height));
    if (canvas.width !== w * dpr || canvas.height !== h * dpr) {
      canvas.width = w * dpr;
      canvas.height = h * dpr;
    }
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return { w, h };
  }

  initStars(count = 420) {
    this.stars = [];
    for (let i = 0; i < count; i++) {
      this.stars.push({
        x: Math.random() * WORLD.w,
        y: Math.random() * WORLD.h,
        s: 0.8 + Math.random() * 2.2,
        lane: Math.random() < 0.2 ? 2 : Math.random() < 0.55 ? 1 : 0,
      });
    }
  }

  drawBackground(fullW: number, fullH: number, theme: Theme, layers: ParallaxLayer[], dt: number) {
    const ctx = this.ctx;
    // base
    ctx.fillStyle = theme.bg;
    ctx.fillRect(0, 0, fullW, fullH);

    // world frame
    const scale = Math.min(fullW / WORLD.w, fullH / WORLD.h);
    const ox = (fullW - WORLD.w * scale) / 2;
    const oy = (fullH - WORLD.h * scale) / 2;

    // subtle vignette/letterbox
    ctx.fillStyle = "rgba(0,0,0,0.25)";
    ctx.fillRect(0, 0, fullW, Math.max(0, oy));
    ctx.fillRect(0, oy + WORLD.h * scale, fullW, Math.max(0, fullH - (oy + WORLD.h * scale)));
    ctx.fillRect(0, oy, Math.max(0, ox), WORLD.h * scale);
    ctx.fillRect(ox + WORLD.w * scale, oy, Math.max(0, fullW - (ox + WORLD.w * scale)), WORLD.h * scale);

    this.scroll += dt;
    const t = this.scroll;

    for (const layer of layers) {
      if (layer.kind === "stars") {
        const speed = layer.speed;
        const alpha = layer.alpha;
        ctx.save();
        ctx.globalAlpha = alpha;
        ctx.fillStyle = "rgba(255,255,255,0.9)";
        for (const st of this.stars) {
          const localSpeed = speed * (st.lane === 2 ? 1.8 : st.lane === 1 ? 1.2 : 0.9);
          st.y += localSpeed * dt;
          if (st.y > WORLD.h) st.y = 0;
          const x = ox + st.x * scale;
          const y = oy + st.y * scale;
          if (x < -10 || x > fullW + 10 || y < -10 || y > fullH + 10) continue;
          ctx.fillRect(x, y, st.s, st.s);
        }
        ctx.restore();
      }

      if (layer.kind === "nebula") {
        ctx.save();
        ctx.globalAlpha = layer.alpha;
        const g = ctx.createLinearGradient(0, 0, fullW, fullH);
        g.addColorStop(0, theme.accent);
        g.addColorStop(0.45, theme.primary);
        g.addColorStop(1, theme.accent);
        ctx.fillStyle = g;
        const bandY = fullH * 0.32 + Math.sin(t * 0.7) * 18;
        ctx.fillRect(0, bandY, fullW, fullH * 0.36);
        ctx.restore();
      }

      if (layer.kind === "planet") {
        ctx.save();
        ctx.globalAlpha = layer.alpha;
        const px = fullW * 0.76 + Math.sin(t * 0.16) * 10;
        const py = fullH * 0.22 + Math.cos(t * 0.12) * 8;
        const r = Math.min(fullW, fullH) * 0.18;
        const rg = ctx.createRadialGradient(px - r * 0.25, py - r * 0.25, r * 0.2, px, py, r);
        rg.addColorStop(0, theme.primary);
        rg.addColorStop(1, "rgba(0,0,0,0)");
        ctx.fillStyle = rg;
        ctx.beginPath();
        ctx.arc(px, py, r, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }

      if (layer.kind === "debris") {
        ctx.save();
        ctx.globalAlpha = layer.alpha;
        ctx.strokeStyle = "rgba(255,255,255,0.16)";
        ctx.lineWidth = 1;
        const speed = layer.speed;
        for (let i = 0; i < 16; i++) {
          const x = (fullW * ((i * 83) % 997) / 997) + Math.sin(t * 0.9 + i) * 8;
          const y = (fullH * (((i * 173) % 997) / 997) + (t * speed * 0.7) % fullH);
          const len = 16 + (i % 5) * 7;
          ctx.beginPath();
          ctx.moveTo(x, y);
          ctx.lineTo(x + len, y - len * 0.6);
          ctx.stroke();
        }
        ctx.restore();
      }

      if (layer.kind === "fog") {
        ctx.save();
        ctx.globalAlpha = layer.alpha;
        ctx.fillStyle = "rgba(255,255,255,0.06)";
        const y = fullH * 0.62 + Math.sin(t * 0.4) * 12;
        ctx.fillRect(0, y, fullW, fullH * 0.12);
        ctx.restore();
      }
    }
  }

  beginWorld(fullW: number, fullH: number) {
    const ctx = this.ctx;
    const scale = Math.min(fullW / WORLD.w, fullH / WORLD.h);
    const ox = (fullW - WORLD.w * scale) / 2;
    const oy = (fullH - WORLD.h * scale) / 2;
    ctx.save();
    ctx.beginPath();
    ctx.rect(ox, oy, WORLD.w * scale, WORLD.h * scale);
    ctx.clip();
    ctx.translate(ox, oy);
    ctx.scale(scale, scale);
    return { scale, ox, oy };
  }

  endWorld() {
    this.ctx.restore();
  }

  drawShip(x: number, y: number, theme: Theme, isDashing: boolean) {
    const ctx = this.ctx;
    ctx.save();
    ctx.translate(x, y);
    if (isDashing) {
      ctx.globalAlpha = 0.75;
      ctx.shadowColor = theme.primary;
      ctx.shadowBlur = 18;
    }
    ctx.fillStyle = theme.primary;
    ctx.beginPath();
    ctx.moveTo(0, -14);
    ctx.lineTo(10, 12);
    ctx.lineTo(0, 7);
    ctx.lineTo(-10, 12);
    ctx.closePath();
    ctx.fill();
    ctx.fillStyle = theme.accent;
    ctx.fillRect(-2, 2, 4, 8);
    ctx.restore();
  }

  drawBullet(x: number, y: number, r: number, theme: Theme, owner: "player" | "enemy") {
    const ctx = this.ctx;
    ctx.save();
    ctx.fillStyle = owner === "player" ? theme.primary : theme.danger;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  drawEnemy(x: number, y: number, w: number, h: number, theme: Theme, kind: string) {
    const ctx = this.ctx;
    ctx.save();
    ctx.translate(x, y);
    ctx.fillStyle = kind === "boss" ? theme.accent : "rgba(255,255,255,0.12)";
    ctx.strokeStyle = kind === "boss" ? theme.primary : "rgba(255,255,255,0.25)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.roundRect(-w / 2, -h / 2, w, h, 6);
    ctx.fill();
    ctx.stroke();
    ctx.restore();
  }

  drawPickup(x: number, y: number, r: number, theme: Theme) {
    const ctx = this.ctx;
    ctx.save();
    ctx.fillStyle = theme.gold;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  drawParticles(particles: Particle[]) {
    const ctx = this.ctx;
    for (const p of particles) {
      if (!p.alive) continue;
      const a = Math.max(0, Math.min(1, p.life / p.maxLife));
      ctx.save();
      ctx.globalAlpha = a;
      ctx.fillStyle = p.color;
      ctx.fillRect(p.x, p.y, p.size, p.size);
      ctx.restore();
    }
  }
}
