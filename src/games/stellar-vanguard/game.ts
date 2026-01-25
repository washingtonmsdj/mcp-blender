import { WORLD, KEYS } from "./constants";
import { BIOMES } from "./biomes";
import { Pool } from "./pool";
import { KeyboardInput } from "./input";
import { aabbCircle, circleCircle, clamp, rand } from "./math";
import { UPGRADES, costFor } from "./upgrades";
import type {
  BulletState,
  EnemyKind,
  EnemyState,
  GameInput,
  GamePhase,
  GameState,
  Particle,
  PickupState,
  PlayerState,
  UpgradeId,
} from "./types";

type HudSnapshot = {
  phase: GamePhase;
  biomeName: string;
  score: number;
  highScore: number;
  hp: number;
  shield: number;
  shieldMax: number;
  dashCd: number;
  specialCd: number;
  bombCount: number;
  energy: number;
  upgrades: { id: UpgradeId; name: string; level: number; cost: number; maxLevel: number }[];
  wave: number;
  bossActive: boolean;
  bossHp?: number;
  bossHpMax?: number;
};

export class StellarVanguardGame {
  private input = new KeyboardInput();
  private detachInput: (() => void) | null = null;

  private state: GameState;
  private player: PlayerState;

  private bullets = new Pool<BulletState>((id) => ({
    id,
    owner: "player",
    x: 0,
    y: 0,
    vx: 0,
    vy: 0,
    r: 3,
    dmg: 1,
    guided: false,
    alive: false,
  }));
  private enemies = new Pool<EnemyState>((id) => ({
    id,
    kind: "light",
    x: 0,
    y: 0,
    w: 24,
    h: 24,
    vx: 0,
    vy: 0,
    hp: 1,
    alive: false,
    phase: 0,
    t: 0,
  }));
  private pickups = new Pool<PickupState>((id) => ({
    id,
    kind: "energy",
    x: 0,
    y: 0,
    vx: 0,
    vy: 0,
    r: 6,
    value: 1,
    alive: false,
  }));
  private particles = new Pool<Particle>((id) => ({
    id,
    x: 0,
    y: 0,
    vx: 0,
    vy: 0,
    life: 0,
    maxLife: 0,
    size: 2,
    color: "hsl(0,0%,100%)",
    alive: false,
  }));

  private spawnT = 0;
  private enemyShotT = 0;
  private uiFlashT = 0;

  constructor() {
    this.state = {
      phase: "start",
      biome: "nebula",
      biomeTime: 0,
      score: 0,
      highScore: this.loadHighScore(),
      wave: 1,
      bossActive: false,
      bossDefeated: false,
    };

    this.player = this.createPlayer();
  }

  mount() {
    this.detachInput = this.input.attach();
  }

  unmount() {
    this.detachInput?.();
    this.detachInput = null;
  }

  getBiome() {
    return BIOMES[this.state.biome];
  }

  getAll() {
    return {
      player: this.player,
      enemies: this.enemies.all(),
      bullets: this.bullets.all(),
      pickups: this.pickups.all(),
      particles: this.particles.all(),
      state: this.state,
      uiFlashT: this.uiFlashT,
    };
  }

  getHud(): HudSnapshot {
    const biomeName = this.getBiome().name;
    const upgrades = UPGRADES.map((u) => {
      const level = this.player.upgrades[u.id] ?? 0;
      const cost = level >= u.maxLevel ? 0 : costFor(u.id, level, u.baseCost);
      return { id: u.id, name: u.name, level, cost, maxLevel: u.maxLevel };
    });
    const boss = this.enemies.all().find((e) => e.alive && e.kind === "boss");
    return {
      phase: this.state.phase,
      biomeName,
      score: this.state.score,
      highScore: this.state.highScore,
      hp: this.player.hp,
      shield: this.player.shield,
      shieldMax: this.player.shieldMax,
      dashCd: this.player.dashCd,
      specialCd: this.player.specialCd,
      bombCount: this.player.bombCount,
      energy: this.player.energy,
      upgrades,
      wave: this.state.wave,
      bossActive: this.state.bossActive,
      bossHp: boss?.hp,
      bossHpMax: boss ? this.bossMaxHp() : undefined,
    };
  }

  update(dt: number) {
    const input = this.input.getState();
    const startPressed = this.input.consumePress(["Enter"]);
    const restartPressed = this.input.consumePress(["r", "R", "Enter"]);

    if (this.state.phase === "start") {
      if (startPressed) {
        this.start();
      }
      return;
    }

    if (this.state.phase === "gameover") {
      if (restartPressed) {
        this.reset();
        this.start();
      }
      return;
    }

    // playing
    this.state.biomeTime += dt;
    this.uiFlashT = Math.max(0, this.uiFlashT - dt);

    this.player.iFrames = Math.max(0, this.player.iFrames - dt);
    this.player.dashCd = Math.max(0, this.player.dashCd - dt);
    this.player.specialCd = Math.max(0, this.player.specialCd - dt);
    this.player.fireCd = Math.max(0, this.player.fireCd - dt);
    if (this.player.dashTime > 0) this.player.dashTime = Math.max(0, this.player.dashTime - dt);

    // shield regen
    if ((this.player.upgrades.regen ?? 0) > 0 && this.player.shieldMax > 0) {
      const regen = 2 + (this.player.upgrades.regen ?? 0) * 2;
      this.player.shield = Math.min(this.player.shieldMax, this.player.shield + regen * dt);
    }

    this.handleMovement(input, dt);
    this.handleCombat(input, dt);
    this.handleSpawning(dt);
    this.updateEnemies(dt);
    this.updateBullets(dt);
    this.updatePickups(dt);
    this.updateParticles(dt);
    this.handleCollisions();
    this.handleUpgradeHotbar();
  }

  private createPlayer(): PlayerState {
    const u: Record<UpgradeId, number> = {
      double_shot: 0,
      spread: 0,
      guided: 0,
      shield: 0,
      regen: 0,
      fire_rate: 0,
      special_cd: 0,
      bomb_plus: 0,
    };

    return {
      x: WORLD.w / 2,
      y: WORLD.h * 0.86,
      vx: 0,
      vy: 0,
      hp: 100,
      shield: 0,
      shieldMax: 0,
      iFrames: 0,
      dashCd: 0,
      dashTime: 0,
      specialCd: 0,
      bombCount: 2,
      energy: 0,
      fireCd: 0,
      fireRate: 9,
      bulletSpeed: 620,
      upgrades: u,
    };
  }

  private start() {
    this.state.phase = "playing";
  }

  private reset() {
    this.state = {
      ...this.state,
      phase: "start",
      biome: "nebula",
      biomeTime: 0,
      score: 0,
      wave: 1,
      bossActive: false,
      bossDefeated: false,
    };
    this.player = this.createPlayer();
    this.spawnT = 0;
    this.enemyShotT = 0;
    this.uiFlashT = 0;
    this.bullets.clear();
    this.enemies.clear();
    this.pickups.clear();
    this.particles.clear();
  }

  private handleMovement(input: GameInput, dt: number) {
    const speedBase = 280;
    const speed = speedBase;
    let vx = 0;
    let vy = 0;
    if (input.left) vx -= 1;
    if (input.right) vx += 1;
    if (input.up) vy -= 1;
    if (input.down) vy += 1;
    const len = Math.hypot(vx, vy) || 1;
    vx /= len;
    vy /= len;

    // dash: burst + invencibilidade curta
    const dashPressed = this.input.consumePress(KEYS.dash);
    if (dashPressed && this.player.dashCd <= 0) {
      this.player.dashCd = 0.9;
      this.player.dashTime = 0.18;
      this.player.iFrames = Math.max(this.player.iFrames, 0.25);
      this.emitBurst(this.player.x, this.player.y + 10, 28, this.getBiome().theme.primary);
    }
    const dashMul = this.player.dashTime > 0 ? 2.4 : 1;
    this.player.x += vx * speed * dashMul * dt;
    this.player.y += vy * speed * dashMul * dt;
    this.player.x = clamp(this.player.x, 16, WORLD.w - 16);
    this.player.y = clamp(this.player.y, 20, WORLD.h - 20);
  }

  private handleCombat(input: GameInput, dt: number) {
    // shooting (hold)
    const fireRateBonus = (this.player.upgrades.fire_rate ?? 0) * 2.2;
    const fireRate = this.player.fireRate + fireRateBonus;
    const interval = fireRate > 0 ? 1 / fireRate : 0.12;
    if (input.shoot && this.player.fireCd <= 0) {
      this.player.fireCd = interval;
      this.spawnPlayerShot("primary");
    }

    // special (press)
    const specialPressed = this.input.consumePress(KEYS.special);
    if (specialPressed && this.player.specialCd <= 0) {
      const lvl = this.player.upgrades.special_cd ?? 0;
      const cd = Math.max(2.4, 4.2 - lvl * 0.6);
      this.player.specialCd = cd;
      this.spawnPlayerShot("special");
      this.emitBurst(this.player.x, this.player.y - 20, 34, this.getBiome().theme.accent);
    }

    // bomb (press)
    const bombPressed = this.input.consumePress(KEYS.bomb);
    if (bombPressed && this.player.bombCount > 0) {
      this.player.bombCount -= 1;
      this.uiFlashT = 0.12;
      // clear enemy bullets + damage enemies
      for (const b of this.bullets.all()) {
        if (b.alive && b.owner === "enemy") b.alive = false;
      }
      for (const e of this.enemies.all()) {
        if (!e.alive) continue;
        e.hp -= e.kind === "boss" ? 10 : 3;
        if (e.hp <= 0) {
          e.alive = false;
          this.onEnemyKilled(e);
        }
      }
      this.emitBurst(WORLD.w / 2, WORLD.h / 2, 120, this.getBiome().theme.gold);
    }
  }

  private spawnPlayerShot(kind: "primary" | "special") {
    const t = this.getBiome().theme;
    const guided = (this.player.upgrades.guided ?? 0) > 0;
    const double = (this.player.upgrades.double_shot ?? 0) > 0;
    const spreadLvl = this.player.upgrades.spread ?? 0;
    const bulletSpeed = this.player.bulletSpeed + (kind === "special" ? 120 : 0);
    const dmg = kind === "special" ? 3 : 1;

    const spawn = (dx: number, dy: number, vx: number, vy: number) => {
      this.bullets.spawn((b) => {
        b.owner = "player";
        b.x = this.player.x + dx;
        b.y = this.player.y + dy;
        b.vx = vx;
        b.vy = vy;
        b.r = kind === "special" ? 4 : 3;
        b.dmg = dmg;
        b.guided = guided;
      });
      this.particles.spawn((p) => {
        p.x = this.player.x;
        p.y = this.player.y - 16;
        p.vx = rand(-20, 20);
        p.vy = rand(-160, -60);
        p.maxLife = p.life = 0.18;
        p.size = 2;
        p.color = kind === "special" ? t.accent : t.primary;
      });
    };

    if (spreadLvl > 0) {
      const spread = spreadLvl === 1 ? 0.34 : 0.46;
      spawn(0, -16, -120, -bulletSpeed * (1 - spread));
      spawn(0, -16, 0, -bulletSpeed);
      spawn(0, -16, 120, -bulletSpeed * (1 - spread));
      if (double) {
        spawn(-8, -16, 0, -bulletSpeed);
        spawn(8, -16, 0, -bulletSpeed);
      }
      return;
    }

    if (double) {
      spawn(-7, -16, 0, -bulletSpeed);
      spawn(7, -16, 0, -bulletSpeed);
      return;
    }
    spawn(0, -16, 0, -bulletSpeed);
  }

  private handleSpawning(dt: number) {
    // wave scaling via score
    this.state.wave = 1 + Math.floor(this.state.score / 240);

    const bossGateScore = 1200;
    if (!this.state.bossActive && !this.state.bossDefeated && this.state.score >= bossGateScore) {
      this.spawnBoss();
      this.state.bossActive = true;
      return;
    }

    if (this.state.bossActive) return;

    this.spawnT += dt;
    const baseRate = 1.35;
    const rate = baseRate + this.state.wave * 0.22;
    const interval = 1 / rate;
    if (this.spawnT < interval) return;
    this.spawnT = 0;

    const roll = Math.random();
    const kind: EnemyKind = roll < 0.62 ? "light" : roll < 0.88 ? "medium" : "heavy";
    const x = rand(40, WORLD.w - 40);
    const y = -30;
    const baseVy = kind === "light" ? 120 : kind === "medium" ? 95 : 70;
    const vy = baseVy + this.state.wave * 8;
    const w = kind === "heavy" ? 44 : kind === "medium" ? 34 : 26;
    const h = w;
    const hp = kind === "light" ? 1 : kind === "medium" ? 3 : 6;
    const vx = kind === "light" ? rand(-50, 50) : kind === "medium" ? rand(-35, 35) : rand(-22, 22);

    this.enemies.spawn((e) => {
      e.kind = kind;
      e.x = x;
      e.y = y;
      e.w = w;
      e.h = h;
      e.vx = vx;
      e.vy = vy;
      e.hp = hp;
      e.t = 0;
      e.phase = 0;
    });
  }

  private spawnBoss() {
    const hp = this.bossMaxHp();
    this.enemies.spawn((e) => {
      e.kind = "boss";
      e.x = WORLD.w / 2;
      e.y = -60;
      e.w = 140;
      e.h = 84;
      e.vx = 0;
      e.vy = 45;
      e.hp = hp;
      e.phase = 0;
      e.t = 0;
    });
  }

  private bossMaxHp() {
    return 90;
  }

  private updateEnemies(dt: number) {
    this.enemyShotT += dt;
    const shootInterval = Math.max(0.5, 1.35 - this.state.wave * 0.05);

    const enemies = this.enemies.all();
    for (const e of enemies) {
      if (!e.alive) continue;
      e.t += dt;

      if (e.kind === "boss") {
        // enter then patrol
        if (e.y < 120) {
          e.y += e.vy * dt;
        } else {
          e.y = 120 + Math.sin(e.t * 0.9) * 10;
          e.x = WORLD.w / 2 + Math.sin(e.t * 0.8) * 240;
        }

        // phases based on hp
        const hpPct = e.hp / this.bossMaxHp();
        e.phase = hpPct > 0.66 ? 0 : hpPct > 0.33 ? 1 : 2;

        // boss shooting
        if (this.enemyShotT >= shootInterval * 0.8) {
          this.enemyShotT = 0;
          this.spawnBossPattern(e);
        }
        continue;
      }

      // drift + bounce
      e.x = clamp(e.x + e.vx * dt, 20, WORLD.w - 20);
      e.y += e.vy * dt;
      if (e.x <= 20 || e.x >= WORLD.w - 20) e.vx *= -1;

      // enemy shooting (simple)
      if (this.enemyShotT >= shootInterval) {
        // some enemies shoot
        if (e.kind !== "light" || Math.random() < 0.45) {
          this.spawnEnemyShot(e);
        }
      }

      // despawn offscreen
      if (e.y > WORLD.h + 80) e.alive = false;
    }

    if (this.enemyShotT >= shootInterval) this.enemyShotT = 0;
  }

  private spawnEnemyShot(e: EnemyState) {
    const dy = 220 + this.state.wave * 10;
    const spread = e.kind === "medium" ? 2 : e.kind === "heavy" ? 3 : 1;
    for (let i = 0; i < spread; i++) {
      const ang = spread === 1 ? Math.PI / 2 : Math.PI / 2 + (i - (spread - 1) / 2) * 0.18;
      const vx = Math.cos(ang) * dy;
      const vy = Math.sin(ang) * dy;
      this.bullets.spawn((b) => {
        b.owner = "enemy";
        b.x = e.x;
        b.y = e.y + e.h * 0.45;
        b.vx = vx;
        b.vy = vy;
        b.r = 3.2;
        b.dmg = e.kind === "heavy" ? 12 : 8;
        b.guided = false;
      });
    }
  }

  private spawnBossPattern(boss: EnemyState) {
    const phase = boss.phase ?? 0;
    const speed = 260;
    if (phase === 0) {
      // cone
      for (let i = -2; i <= 2; i++) {
        const ang = Math.PI / 2 + i * 0.16;
        this.spawnBossBullet(boss, Math.cos(ang) * speed, Math.sin(ang) * speed, 10);
      }
      return;
    }
    if (phase === 1) {
      // ring burst
      const n = 14;
      for (let i = 0; i < n; i++) {
        const ang = (i / n) * Math.PI * 2;
        this.spawnBossBullet(boss, Math.cos(ang) * (speed * 0.72), Math.sin(ang) * (speed * 0.72), 10);
      }
      return;
    }
    // phase 2: aimed + side shots
    const dx = this.player.x - boss.x;
    const dy = this.player.y - boss.y;
    const len = Math.hypot(dx, dy) || 1;
    const ux = dx / len;
    const uy = dy / len;
    this.spawnBossBullet(boss, ux * (speed * 0.95), uy * (speed * 0.95), 12);
    this.spawnBossBullet(boss, -120, 240, 10);
    this.spawnBossBullet(boss, 120, 240, 10);
  }

  private spawnBossBullet(boss: EnemyState, vx: number, vy: number, dmg: number) {
    this.bullets.spawn((b) => {
      b.owner = "enemy";
      b.x = boss.x;
      b.y = boss.y + boss.h * 0.5;
      b.vx = vx;
      b.vy = vy;
      b.r = 4;
      b.dmg = dmg;
      b.guided = false;
    });
  }

  private updateBullets(dt: number) {
    const enemies = this.enemies.all().filter((e) => e.alive);
    for (const b of this.bullets.all()) {
      if (!b.alive) continue;

      // simple guidance: nudge toward nearest enemy
      if (b.owner === "player" && b.guided) {
        const target = nearestEnemy(enemies, b.x, b.y);
        if (target) {
          const dx = target.x - b.x;
          const dy = target.y - b.y;
          const len = Math.hypot(dx, dy) || 1;
          const ux = dx / len;
          const uy = dy / len;
          b.vx = b.vx * 0.92 + ux * 120 * 0.08;
          b.vy = b.vy * 0.92 + uy * 120 * 0.08;
        }
      }

      b.x += b.vx * dt;
      b.y += b.vy * dt;
      if (b.y < -120 || b.y > WORLD.h + 120 || b.x < -120 || b.x > WORLD.w + 120) {
        b.alive = false;
      }
    }
  }

  private updatePickups(dt: number) {
    for (const p of this.pickups.all()) {
      if (!p.alive) continue;
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      p.vy += 18 * dt;
      if (p.y > WORLD.h + 80) p.alive = false;
    }
  }

  private updateParticles(dt: number) {
    for (const p of this.particles.all()) {
      if (!p.alive) continue;
      p.life -= dt;
      if (p.life <= 0) {
        p.alive = false;
        continue;
      }
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      p.vx *= 0.98;
      p.vy *= 0.98;
    }
  }

  private handleCollisions() {
    // bullets -> enemies
    for (const b of this.bullets.all()) {
      if (!b.alive || b.owner !== "player") continue;
      for (const e of this.enemies.all()) {
        if (!e.alive) continue;
        if (aabbCircle(e.x, e.y, e.w, e.h, b.x, b.y, b.r)) {
          b.alive = false;
          e.hp -= b.dmg;
          this.emitHit(b.x, b.y);
          if (e.hp <= 0) {
            e.alive = false;
            this.onEnemyKilled(e);
          }
          break;
        }
      }
    }

    // enemy bullets -> player
    for (const b of this.bullets.all()) {
      if (!b.alive || b.owner !== "enemy") continue;
      if (this.player.iFrames > 0) continue;
      if (circleCircle(this.player.x, this.player.y, 12, b.x, b.y, b.r)) {
        b.alive = false;
        this.applyDamage(b.dmg);
        this.emitHit(this.player.x, this.player.y);
      }
    }

    // enemies -> player
    for (const e of this.enemies.all()) {
      if (!e.alive || e.kind === "boss") continue;
      if (this.player.iFrames > 0) continue;
      // treat player as circle
      if (aabbCircle(e.x, e.y, e.w, e.h, this.player.x, this.player.y, 12)) {
        e.alive = false;
        this.applyDamage(e.kind === "heavy" ? 18 : e.kind === "medium" ? 14 : 10);
        this.emitBurst(e.x, e.y, 24, this.getBiome().theme.accent);
      }
    }

    // pickups -> player
    for (const p of this.pickups.all()) {
      if (!p.alive) continue;
      if (circleCircle(this.player.x, this.player.y, 14, p.x, p.y, p.r)) {
        p.alive = false;
        this.player.energy += p.value;
        this.state.score += 2;
        this.emitBurst(p.x, p.y, 12, this.getBiome().theme.gold);
      }
    }

    // boss defeated
    if (this.state.bossActive) {
      const boss = this.enemies.all().find((e) => e.alive && e.kind === "boss");
      if (!boss) {
        this.state.bossActive = false;
        this.state.bossDefeated = true;
        this.state.score += 500;
        this.emitBurst(WORLD.w / 2, 120, 160, this.getBiome().theme.primary);
      }
    }
  }

  private onEnemyKilled(e: EnemyState) {
    const t = this.getBiome().theme;
    const base = e.kind === "boss" ? 200 : e.kind === "heavy" ? 40 : e.kind === "medium" ? 22 : 14;
    this.state.score += base;

    // energy drop
    const drop = e.kind === "heavy" ? 4 : e.kind === "medium" ? 2 : 1;
    this.pickups.spawn((p) => {
      p.kind = "energy";
      p.x = e.x;
      p.y = e.y;
      p.vx = rand(-40, 40);
      p.vy = rand(30, 70);
      p.r = 6;
      p.value = drop;
    });

    this.emitBurst(e.x, e.y, e.kind === "heavy" ? 46 : 30, t.accent);
  }

  private emitHit(x: number, y: number) {
    const t = this.getBiome().theme;
    this.particles.spawn((p) => {
      p.x = x;
      p.y = y;
      p.vx = rand(-40, 40);
      p.vy = rand(-40, 40);
      p.maxLife = p.life = 0.22;
      p.size = 2.5;
      p.color = t.primary;
    });
  }

  private emitBurst(x: number, y: number, count: number, color: string) {
    for (let i = 0; i < count; i++) {
      this.particles.spawn((p) => {
        p.x = x;
        p.y = y;
        p.vx = rand(-220, 220);
        p.vy = rand(-220, 220);
        p.maxLife = p.life = rand(0.25, 0.75);
        p.size = rand(1.5, 3.6);
        p.color = color;
      });
    }
  }

  private applyDamage(amount: number) {
    // iFrames
    this.player.iFrames = 0.35;

    // shield first
    if (this.player.shield > 0) {
      const absorbed = Math.min(this.player.shield, amount);
      this.player.shield = Math.max(0, this.player.shield - absorbed);
      amount -= absorbed;
      if (amount <= 0) return;
    }
    this.player.hp = Math.max(0, this.player.hp - amount);
    if (this.player.hp <= 0) {
      this.onGameOver();
    }
  }

  private onGameOver() {
    this.state.phase = "gameover";
    if (this.state.score > this.state.highScore) {
      this.state.highScore = this.state.score;
      this.saveHighScore(this.state.highScore);
    }
  }

  private handleUpgradeHotbar() {
    // Compra rápida 1..8
    const digits = ["1","2","3","4","5","6","7","8"] as const;
    for (let i = 0; i < digits.length; i++) {
      if (this.input.consumePress([digits[i]])) {
        const up = UPGRADES[i];
        if (!up) return;
        this.tryBuyUpgrade(up.id);
      }
    }
  }

  private tryBuyUpgrade(id: UpgradeId) {
    const def = UPGRADES.find((u) => u.id === id);
    if (!def) return;
    const current = this.player.upgrades[id] ?? 0;
    if (current >= def.maxLevel) return;
    const cost = costFor(id, current, def.baseCost);
    if (this.player.energy < cost) return;
    this.player.energy -= cost;
    this.player.upgrades[id] = current + 1;
    this.uiFlashT = 0.18;

    // apply effects
    if (id === "shield") {
      this.player.shieldMax = 20 + (this.player.upgrades.shield ?? 0) * 20;
      this.player.shield = Math.max(this.player.shield, this.player.shieldMax);
    }
    if (id === "bomb_plus") {
      // cap bombs for MVP
      const extra = this.player.upgrades.bomb_plus ?? 0;
      this.player.bombCount = Math.min(5, 2 + extra);
    }
  }

  private loadHighScore(): number {
    try {
      const raw = localStorage.getItem("stellar_vanguard_highscore");
      const n = raw ? Number(raw) : 0;
      return Number.isFinite(n) ? n : 0;
    } catch {
      return 0;
    }
  }

  private saveHighScore(v: number) {
    try {
      localStorage.setItem("stellar_vanguard_highscore", String(v));
    } catch {
      // ignore
    }
  }
}

function nearestEnemy(enemies: EnemyState[], x: number, y: number): EnemyState | null {
  let best: EnemyState | null = null;
  let bestD = Infinity;
  for (const e of enemies) {
    if (!e.alive) continue;
    const dx = e.x - x;
    const dy = e.y - y;
    const d = dx * dx + dy * dy;
    if (d < bestD) {
      bestD = d;
      best = e;
    }
  }
  return best;
}
