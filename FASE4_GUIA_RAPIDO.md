# 🚀 FASE 4 - GUIA RÁPIDO DE USO

## TL;DR

Agora você pode criar um jogo top-down shooter funcional com **3 linhas de código**:

```typescript
import { autofillTopDownShooter } from '@/lib/ordax/runtime-autofill';

const minimalRuntime = { gameType: 'topdown', title: 'My Game', systems: [], scene: { entities: [] } };
const { spec } = autofillTopDownShooter(minimalRuntime);
// spec agora tem um jogo completo e jogável!
```

---

## 📦 SISTEMAS DISPONÍVEIS

### Novos (Fase 4):
- **InputSystem** - Controles WASD + SPACE
- **SpawnerSystem** - Spawna enemies automaticamente
- **CombatSystem** - Dano e morte
- **GameStateSystem** - START → PLAYING → GAME_OVER

### Corrigidos (Fase 4):
- **PhysicsSystem** - Agora funciona com props direto
- **AISystem** - Agora funciona com props direto
- **UISystem** - Renderiza telas automaticamente

### Já funcionavam:
- **CollisionSystem** - Detecção de colisões
- **ScoreSystem** - Pontuação
- **TimerSystem** - Tempo

---

## 🎮 EXEMPLO COMPLETO

```typescript
import { autofillTopDownShooter } from '@/lib/ordax/runtime-autofill';
import {
  PhysicsSystem, CollisionSystem, AISystem, InputSystem,
  SpawnerSystem, CombatSystem, GameStateSystem,
  ScoreSystem, TimerSystem, UISystem
} from '@/lib/ordax/systems';

// 1. Autofill
const { spec } = autofillTopDownShooter({
  gameType: 'topdown',
  title: 'My Game',
  systems: [],
  scene: { entities: [] }
});

// 2. Criar sistemas
const systems = {
  physics: new PhysicsSystem(),
  collision: new CollisionSystem(),
  ai: new AISystem(),
  input: new InputSystem(),
  spawner: new SpawnerSystem(),
  combat: new CombatSystem(),
  gameState: new GameStateSystem(),
  score: new ScoreSystem(),
  timer: new TimerSystem(),
  ui: new UISystem(),
};

// 3. Setup colisões
systems.collision.on('bullet', 'enemy', (bullet, enemy) => {
  systems.combat.handleCollisionDamage(bullet, enemy);
  systems.score.addScore(10);
});

systems.collision.on('enemy', 'player', (enemy, player) => {
  systems.combat.handleCollisionDamage(enemy, player);
});

// 4. Game loop
function update(dt: number) {
  if (systems.gameState.current !== 'PLAYING') return;
  
  systems.input.update(dt, spec.scene.entities);
  systems.physics.update(dt, spec.scene.entities);
  systems.ai.update(dt, spec.scene.entities);
  systems.spawner.update(dt, spec.scene.entities, Date.now() / 1000);
  systems.collision.update(spec.scene.entities);
  systems.combat.update(dt, spec.scene.entities);
  systems.gameState.update(dt, spec.scene.entities);
  systems.timer.update(dt);
}

function render(ctx: CanvasRenderingContext2D) {
  // Clear
  ctx.fillStyle = '#000';
  ctx.fillRect(0, 0, 800, 600);
  
  // Entities
  for (const entity of spec.scene.entities) {
    if (entity.type === 'ui' || entity.type === 'controls') continue;
    
    ctx.fillStyle = entity.props?.color || '#fff';
    ctx.fillRect(entity.x - entity.w/2, entity.y - entity.h/2, entity.w, entity.h);
  }
  
  // UI
  systems.ui.render(ctx, systems.gameState.current, spec.scene.entities, systems.score, systems.timer);
}

// 5. Start
systems.gameState.start();

// 6. Run
setInterval(() => {
  update(1/60);
  render(canvas.getContext('2d')!);
}, 1000/60);
```

---

## 🔑 CONCEITOS-CHAVE

### 1. Dual Mode Systems

Sistemas agora funcionam em **dois modos**:

**Advanced Mode** (registro manual):
```typescript
const physics = new PhysicsSystem();
physics.register('player1', 1, 0.1, 0.5);
physics.applyForce('player1', 100, 0);
```

**Simple Mode** (props direto):
```typescript
// Autofill já injeta props
entity.props.vx = 100;
entity.props.vy = 0;

// Sistema lê automaticamente
physics.update(dt, entities);
```

### 2. Props-Based Configuration

Tudo é configurado via `props`:

```typescript
// Player
{
  type: 'player',
  props: {
    health: 100,
    speed: 200,
    fireRate: 0.25,
    vx: 0,
    vy: 0
  }
}

// Enemy
{
  type: 'enemy',
  props: {
    health: 50,
    speed: 100,
    ai: 'chase',
    damage: 10
  }
}

// Spawner
{
  type: 'spawner',
  props: {
    spawnRate: 2.0,
    maxEnemies: 20
  }
}
```

### 3. Auto-Rendering UI

UISystem renderiza automaticamente baseado em game state:

```typescript
ui.render(ctx, gameState.current, entities, score, timer);

// Renderiza:
// - START: StartScreen com título e instruções
// - PLAYING: HUD com health, score, timer
// - GAME_OVER: GameOverScreen com score final
```

---

## 📋 CHECKLIST DE INTEGRAÇÃO

Para integrar com seu jogo:

- [ ] Importar `autofillTopDownShooter`
- [ ] Criar runtime mínimo
- [ ] Chamar autofill
- [ ] Criar instâncias dos sistemas
- [ ] Setup collision handlers
- [ ] Implementar game loop (update + render)
- [ ] Chamar `gameState.start()`

---

## 🐛 TROUBLESHOOTING

### Player não se move
```typescript
// Verifique se InputSystem está sendo chamado
input.update(dt, entities);

// Verifique se PhysicsSystem está sendo chamado
physics.update(dt, entities);
```

### Enemies não spawnam
```typescript
// Verifique se SpawnerSystem está sendo chamado com currentTime
spawner.update(dt, entities, Date.now() / 1000);

// Verifique se há spawner entity
const spawner = entities.find(e => e.type === 'spawner');
console.log(spawner?.props);
```

### Colisões não funcionam
```typescript
// Verifique se collision handlers estão registrados
collision.on('bullet', 'enemy', (bullet, enemy) => {
  console.log('Collision!', bullet, enemy);
});

// Verifique se CollisionSystem está sendo chamado
collision.update(entities);
```

### Game over não dispara
```typescript
// Verifique se GameStateSystem está sendo chamado
gameState.update(dt, entities);

// Verifique health do player
const player = entities.find(e => e.type === 'player');
console.log('Player health:', player?.props?.health);
```

---

## 📚 REFERÊNCIAS

- **Fase 2:** Runtime Profile + Validator → `LEIA_PRIMEIRO_FASE2.md`
- **Fase 3:** Autofill + Defaults → `FASE3_RUNTIME_AUTOFILL.md`
- **Fase 4:** System Implementation → `FASE4_IMPLEMENTACAO_COMPLETA.md`
- **Testes:** Integration tests → `src/lib/ordax/systems/integration.test.ts`

---

## ✅ RESULTADO ESPERADO

Após seguir este guia, você terá:

- ✅ Player controlável (WASD)
- ✅ Shooting funcional (SPACE)
- ✅ Enemies spawnando
- ✅ Enemies perseguindo player
- ✅ Colisões detectadas
- ✅ Dano aplicado
- ✅ Game over quando player morre
- ✅ Restart funcional
- ✅ UI completa (StartScreen, HUD, GameOverScreen)

**Tudo isso com ~50 linhas de código!**
