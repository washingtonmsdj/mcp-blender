# 🚀 Roadmap de Implementação: Ordax 100%

## 📋 VISÃO GERAL

**Objetivo**: Alcançar 100% de paridade com GameForge Engine
**Esforço Total**: 45 horas
**Status Atual**: 70% (84/120 pontos)
**Meta**: 100% (120/120 pontos)

---

## 🔴 FASE 1: INTEGRAÇÃO DE SISTEMAS (8h)

### ✅ TASK 1.1: Integrar AnimationSystem (3h)

**Problema**: AnimationSystem existe mas não é usado no canvas

**Solução**:
1. Adicionar suporte a spritesheets no OrdaxSpec
2. Carregar imagens no canvas
3. Renderizar frames animados
4. Integrar no game loop

**Arquivos**:
- `src/lib/ordax/types.ts` (adicionar sprite props)
- `src/components/ordax/OrdaxCanvas.tsx` (renderizar sprites)
- `src/lib/ordax/systems/AnimationSystem.ts` (melhorias)

**Código**:
```typescript
// 1. Atualizar OrdaxEntity
type OrdaxEntity = {
  // ... existing
  sprite?: {
    url: string;
    frameWidth: number;
    frameHeight: number;
    animations: {
      [key: string]: {
        frames: number[];
        duration: number;
        loop: boolean;
      }
    }
  }
}

// 2. No canvas, carregar sprites
const sprites = new Map<string, HTMLImageElement>();

// 3. Renderizar sprite ao invés de retângulo
if (entity.sprite) {
  const frame = animationSystem.getCurrentFrame(entity.id);
  ctx.drawImage(sprite, frame.x, frame.y, frame.w, frame.h, x, y, w, h);
}
```

**Resultado**: Personagens animados ao invés de retângulos

---

### ✅ TASK 1.2: Integrar AudioSystem (2h)

**Problema**: AudioSystem existe mas não é usado

**Solução**:
1. Adicionar sons ao OrdaxSpec
2. Carregar áudio no canvas
3. Tocar sons em eventos
4. Música de fundo

**Arquivos**:
- `src/lib/ordax/types.ts` (adicionar audio props)
- `src/components/ordax/OrdaxCanvas.tsx` (tocar sons)

**Código**:
```typescript
// 1. Atualizar OrdaxSpec
type OrdaxSpec = {
  // ... existing
  audio?: {
    music?: string;
    sounds?: {
      collision: string;
      score: string;
      gameOver: string;
    }
  }
}

// 2. No canvas, carregar áudio
useEffect(() => {
  if (spec.audio?.music) {
    audioSystem.loadMusic("bgm", spec.audio.music);
    audioSystem.playMusic("bgm");
  }
  if (spec.audio?.sounds) {
    Object.entries(spec.audio.sounds).forEach(([key, url]) => {
      audioSystem.loadSound(key, url);
    });
  }
}, [spec]);

// 3. Tocar sons em eventos
collision.on("player", "enemy", () => {
  audioSystem.playSound("collision");
});
```

**Resultado**: Jogos com som e música

---

### ✅ TASK 1.3: Melhorar CameraSystem (3h)

**Problema**: Camera só tem shake, não segue player

**Solução**:
1. Ativar follow no canvas
2. Aplicar transform no contexto
3. Adicionar zoom e bounds

**Arquivos**:
- `src/components/ordax/OrdaxCanvas.tsx` (usar camera transform)

**Código**:
```typescript
// 1. Setup camera follow
useEffect(() => {
  if (hasCameraSystem && initialPlayer) {
    cameraSystem.follow("player", 5);
    cameraSystem.setBounds(0, 0, WORLD.w, WORLD.h);
  }
}, [hasCameraSystem, initialPlayer]);

// 2. Aplicar transform antes de renderizar
if (hasCameraSystem) {
  cameraSystem.apply(ctx);
}

// Renderizar mundo
drawEntities();
drawParticles();

if (hasCameraSystem) {
  cameraSystem.restore(ctx);
}

// Renderizar HUD (sem transform)
drawHUD();
```

**Resultado**: Camera segue player suavemente

---

## 🟡 FASE 2: PHYSICS SYSTEM COMPLETO (12h)

### ✅ TASK 2.1: Criar PhysicsSystem Completo (12h)

**Problema**: Física é básica (apenas movimento direto)

**Solução**: Implementar sistema de física completo

**Arquivo**: `src/lib/ordax/systems/PhysicsSystem.ts` (NOVO)

**Código**:
```typescript
export type PhysicsComponent = {
  vx: number;
  vy: number;
  ax: number;
  ay: number;
  mass: number;
  friction: number;
  restitution: number;
  forces: Vector2[];
};

export class PhysicsSystem {
  private components: Map<string, PhysicsComponent> = new Map();
  
  register(entityId: string, mass: number = 1) {
    this.components.set(entityId, {
      vx: 0, vy: 0,
      ax: 0, ay: 0,
      mass,
      friction: 0.1,
      restitution: 0.5,
      forces: [],
    });
  }
  
  applyForce(entityId: string, fx: number, fy: number) {
    const comp = this.components.get(entityId);
    if (comp) comp.forces.push({ x: fx, y: fy });
  }
  
  applyImpulse(entityId: string, ix: number, iy: number) {
    const comp = this.components.get(entityId);
    if (!comp) return;
    comp.vx += ix / comp.mass;
    comp.vy += iy / comp.mass;
  }
  
  update(dt: number, entities: any[], gravity: Vector2) {
    for (const [id, comp] of this.components) {
      const entity = entities.find(e => e.id === id);
      if (!entity) continue;
      
      // Sum forces
      let fx = 0, fy = 0;
      comp.forces.forEach(f => { fx += f.x; fy += f.y; });
      comp.forces = [];
      
      // Add gravity
      fx += gravity.x * comp.mass;
      fy += gravity.y * comp.mass;
      
      // Calculate acceleration (F = ma)
      comp.ax = fx / comp.mass;
      comp.ay = fy / comp.mass;
      
      // Update velocity
      comp.vx += comp.ax * dt;
      comp.vy += comp.ay * dt;
      
      // Apply friction
      comp.vx *= (1 - comp.friction);
      comp.vy *= (1 - comp.friction);
      
      // Update position
      entity.x += comp.vx * dt;
      entity.y += comp.vy * dt;
    }
  }
}
```

**Resultado**: Física realista com forças, massa, atrito

---

## 🟡 FASE 3: ECS PURO (20h)

### ✅ TASK 3.1: Component Manager (8h)

**Arquivo**: `src/lib/ordax/ecs/ComponentManager.ts` (NOVO)

**Código**:
```typescript
export interface Component {
  type: string;
}

export interface Position extends Component {
  type: "Position";
  x: number;
  y: number;
}

export interface Velocity extends Component {
  type: "Velocity";
  vx: number;
  vy: number;
}

export interface Sprite extends Component {
  type: "Sprite";
  url: string;
  frameWidth: number;
  frameHeight: number;
}

export interface Health extends Component {
  type: "Health";
  current: number;
  max: number;
}

export class ComponentManager {
  private components: Map<string, Map<string, Component>> = new Map();
  
  addComponent(entityId: string, component: Component) {
    if (!this.components.has(entityId)) {
      this.components.set(entityId, new Map());
    }
    this.components.get(entityId)!.set(component.type, component);
  }
  
  removeComponent(entityId: string, componentType: string) {
    this.components.get(entityId)?.delete(componentType);
  }
  
  getComponent<T extends Component>(entityId: string, type: string): T | null {
    return (this.components.get(entityId)?.get(type) as T) ?? null;
  }
  
  hasComponent(entityId: string, type: string): boolean {
    return this.components.get(entityId)?.has(type) ?? false;
  }
  
  getEntitiesWithComponents(...types: string[]): string[] {
    const result: string[] = [];
    for (const [entityId, components] of this.components) {
      if (types.every(type => components.has(type))) {
        result.push(entityId);
      }
    }
    return result;
  }
}
```

---

### ✅ TASK 3.2: Entity Manager (6h)

**Arquivo**: `src/lib/ordax/ecs/EntityManager.ts` (NOVO)

**Código**:
```typescript
export class EntityManager {
  private nextId = 0;
  private entities: Set<string> = new Set();
  
  createEntity(): string {
    const id = `entity_${this.nextId++}`;
    this.entities.add(id);
    return id;
  }
  
  destroyEntity(entityId: string) {
    this.entities.delete(entityId);
  }
  
  hasEntity(entityId: string): boolean {
    return this.entities.has(entityId);
  }
  
  getAllEntities(): string[] {
    return Array.from(this.entities);
  }
}
```

---

### ✅ TASK 3.3: Migrar para ECS (6h)

**Arquivos**:
- `src/lib/ordax/ecs/World.ts` (NOVO)
- `src/components/ordax/OrdaxCanvas.tsx` (atualizar)

**Código**:
```typescript
// World.ts
export class World {
  entityManager = new EntityManager();
  componentManager = new ComponentManager();
  
  createEntity(): string {
    return this.entityManager.createEntity();
  }
  
  addComponent(entityId: string, component: Component) {
    this.componentManager.addComponent(entityId, component);
  }
  
  getComponent<T extends Component>(entityId: string, type: string): T | null {
    return this.componentManager.getComponent<T>(entityId, type);
  }
  
  query(...componentTypes: string[]): string[] {
    return this.componentManager.getEntitiesWithComponents(...componentTypes);
  }
}
```

---

## 🟢 FASE 4: PROFILING (5h)

### ✅ TASK 4.1: Performance Monitor (3h)

**Arquivo**: `src/lib/ordax/PerformanceMonitor.ts` (NOVO)

**Código**:
```typescript
export class PerformanceMonitor {
  private frameTimes: number[] = [];
  private systemTimes: Map<string, number[]> = new Map();
  
  startFrame() {
    this.frameStart = performance.now();
  }
  
  endFrame() {
    const frameTime = performance.now() - this.frameStart;
    this.frameTimes.push(frameTime);
    if (this.frameTimes.length > 60) this.frameTimes.shift();
  }
  
  startSystem(name: string) {
    this.systemStart = performance.now();
  }
  
  endSystem(name: string) {
    const time = performance.now() - this.systemStart;
    if (!this.systemTimes.has(name)) {
      this.systemTimes.set(name, []);
    }
    const times = this.systemTimes.get(name)!;
    times.push(time);
    if (times.length > 60) times.shift();
  }
  
  getReport() {
    const avgFrameTime = this.frameTimes.reduce((a, b) => a + b, 0) / this.frameTimes.length;
    const fps = 1000 / avgFrameTime;
    
    const systems: Record<string, number> = {};
    for (const [name, times] of this.systemTimes) {
      systems[name] = times.reduce((a, b) => a + b, 0) / times.length;
    }
    
    return { fps, avgFrameTime, systems };
  }
}
```

---

### ✅ TASK 4.2: Debug Panel Melhorado (2h)

**Arquivo**: `src/components/ordax/StudioPreviewPanel.tsx`

**Adicionar**:
- FPS graph (últimos 60 frames)
- System timing breakdown
- Memory usage
- Entity count

---

## 📊 CRONOGRAMA

| Fase | Tarefas | Horas | Semana |
|------|---------|-------|--------|
| **Fase 1** | Integração de Sistemas | 8h | Semana 1 |
| **Fase 2** | Physics System | 12h | Semana 2 |
| **Fase 3** | ECS Puro | 20h | Semana 3-4 |
| **Fase 4** | Profiling | 5h | Semana 4 |
| **TOTAL** | | **45h** | **4 semanas** |

---

## 🎯 RESULTADO FINAL

Após completar todas as fases:

✅ **Ordax 120/120 pontos** (100%)
✅ **ECS puro** implementado
✅ **Física completa** (forças, atrito, massa)
✅ **Animações** integradas
✅ **Áudio** integrado
✅ **Camera** completa
✅ **Profiling** automático

**Ordax = GameForge** 🎉

---

**Desenvolvido por**: Kiro AI  
**Data**: 2026-01-24  
**Status**: Roadmap Completo ✅
