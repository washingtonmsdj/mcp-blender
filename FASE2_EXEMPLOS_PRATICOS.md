# 🎮 EXEMPLOS PRÁTICOS: Runtimes Válidos vs Inválidos

## ❌ EXEMPLO 1: Runtime Mínimo (INVÁLIDO)

```typescript
const minimalRuntime: OrdaxSpec = {
  gameType: "topdown",
  title: "My First Shooter",
  description: "A simple shooter",
  systems: [],
  scene: {
    gravity: { x: 0, y: 0 },
    entities: []
  }
};

// Validação
const result = validateRuntimeAgainstProfile(minimalRuntime, TOPDOWN_SHOOTER_PROFILE);

// Resultado:
// isValid: false
// summary.critical: 11
// 
// Violações:
// - SYS_PHYSICSSYSTEM: Sistema obrigatório ausente
// - SYS_COLLISIONSYSTEM: Sistema obrigatório ausente
// - SYS_AISYSTEM: Sistema obrigatório ausente
// - SYS_SPAWNERSYSTEM: Sistema obrigatório ausente
// - SYS_SCORESYSTEM: Sistema obrigatório ausente
// - SYS_TIMERSYSTEM: Sistema obrigatório ausente
// - SYS_UISYSTEM: Sistema obrigatório ausente
// - ENT_PLAYER: Entidade obrigatória ausente
// - ENT_ENEMY: Entidade obrigatória ausente
// - ENT_BULLET: Entidade obrigatória ausente
// - ENT_SPAWNER: Entidade obrigatória ausente
```

---

## ⚠️ EXEMPLO 2: Runtime com Sistemas mas sem Entidades (INVÁLIDO)

```typescript
const systemsOnlyRuntime: OrdaxSpec = {
  gameType: "topdown",
  title: "Systems Only",
  description: "Has systems but no entities",
  systems: [
    "PhysicsSystem",
    "CollisionSystem",
    "AISystem",
    "SpawnerSystem",
    "ScoreSystem",
    "TimerSystem",
    "UISystem"
  ],
  scene: {
    gravity: { x: 0, y: 0 },
    entities: [] // ❌ Vazio!
  }
};

// Validação
const result = validateRuntimeAgainstProfile(systemsOnlyRuntime, TOPDOWN_SHOOTER_PROFILE);

// Resultado:
// isValid: false
// summary.critical: 4
// 
// Violações:
// - ENT_PLAYER: Entidade obrigatória ausente
// - ENT_ENEMY: Entidade obrigatória ausente
// - ENT_BULLET: Entidade obrigatória ausente
// - ENT_SPAWNER: Entidade obrigatória ausente
```

---

## ⚠️ EXEMPLO 3: Runtime com Player Incompleto (INVÁLIDO)

```typescript
const incompletePlayerRuntime: OrdaxSpec = {
  gameType: "topdown",
  title: "Incomplete Player",
  description: "Player missing critical components",
  systems: [
    "PhysicsSystem",
    "CollisionSystem",
    "AISystem",
    "SpawnerSystem",
    "ScoreSystem",
    "TimerSystem",
    "UISystem"
  ],
  scene: {
    gravity: { x: 0, y: 0 },
    entities: [
      {
        id: "player1",
        type: "player",
        x: 400,
        y: 300,
        w: 32,
        h: 32,
        props: {
          // ❌ Faltam: health, speed, fireRate, vx, vy
          x: 400,
          y: 300
        }
      }
    ]
  }
};

// Validação
const result = validateRuntimeAgainstProfile(incompletePlayerRuntime, TOPDOWN_SHOOTER_PROFILE);

// Resultado:
// isValid: false
// summary.critical: 7 (componentes faltantes) + 3 (entidades faltantes)
// summary.severe: 3 (props faltantes)
// 
// Violações Críticas:
// - COMP_PLAYER_VELOCITY: Componente crítico ausente (vx, vy, speed)
// - COMP_PLAYER_HEALTH: Componente crítico ausente (health, hp)
// - COMP_PLAYER_WEAPON: Componente crítico ausente (fireRate, damage)
// - ENT_ENEMY: Entidade obrigatória ausente
// - ENT_BULLET: Entidade obrigatória ausente
// - ENT_SPAWNER: Entidade obrigatória ausente
// 
// Violações Graves:
// - PROP_PLAYER_HEALTH: Propriedade obrigatória ausente
// - PROP_PLAYER_SPEED: Propriedade obrigatória ausente
```

---

## ✅ EXEMPLO 4: Runtime Completo e Válido

```typescript
const completeRuntime: OrdaxSpec = {
  gameType: "topdown",
  title: "Stellar Vanguard",
  description: "Survive waves of enemies in space",
  
  // ✅ Todos os sistemas obrigatórios
  systems: [
    "PhysicsSystem",
    "CollisionSystem",
    "AISystem",
    "SpawnerSystem",
    "ScoreSystem",
    "TimerSystem",
    "UISystem"
  ],
  
  visual: {
    theme: {
      background: "hsl(220, 20%, 10%)",
      primary: "hsl(200, 80%, 60%)",
      accent: "hsl(30, 90%, 60%)"
    },
    background: {
      layers: [
        { type: "starfield", parallax: 0.5, density: 100 }
      ]
    }
  },
  
  audio: {
    sounds: {
      shoot: "laser.mp3",
      collision: "explosion.mp3",
      score: "coin.mp3"
    }
  },
  
  scene: {
    gravity: { x: 0, y: 0 },
    entities: [
      // ✅ PLAYER completo
      {
        id: "player1",
        type: "player",
        x: 400,
        y: 300,
        w: 32,
        h: 32,
        sprite: {
          url: "player.png",
          frameWidth: 32,
          frameHeight: 32
        },
        props: {
          // Transform
          x: 400,
          y: 300,
          rotation: 0,
          
          // Velocity
          vx: 0,
          vy: 0,
          speed: 200,
          
          // Health
          health: 100,
          maxHealth: 100,
          
          // Weapon
          fireRate: 0.2,
          damage: 25,
          lastFired: 0,
          
          // Collider
          w: 32,
          h: 32,
          collider: "circle",
          radius: 16
        }
      },
      
      // ✅ ENEMY completo
      {
        id: "enemy_template",
        type: "enemy",
        x: 200,
        y: 100,
        w: 24,
        h: 24,
        sprite: {
          url: "enemy.png",
          frameWidth: 24,
          frameHeight: 24
        },
        props: {
          // Transform
          x: 200,
          y: 100,
          rotation: 0,
          
          // Velocity
          vx: 0,
          vy: 0,
          speed: 100,
          
          // Health
          health: 50,
          maxHealth: 50,
          
          // AI
          ai: "chase",
          behavior: "aggressive",
          target: "player",
          detectionRadius: 300,
          
          // Damage
          damage: 10,
          
          // Collider
          w: 24,
          h: 24,
          collider: "circle",
          radius: 12
        }
      },
      
      // ✅ BULLET completo
      {
        id: "bullet_template",
        type: "bullet",
        x: 0,
        y: 0,
        w: 4,
        h: 4,
        sprite: {
          url: "bullet.png",
          frameWidth: 4,
          frameHeight: 4
        },
        props: {
          // Transform
          x: 0,
          y: 0,
          rotation: 0,
          
          // Velocity
          vx: 0,
          vy: 0,
          speed: 400,
          
          // Damage
          damage: 25,
          
          // Lifetime
          lifetime: 2.0,
          ttl: 2.0,
          
          // Collider
          w: 4,
          h: 4,
          collider: "circle",
          radius: 2
        }
      },
      
      // ✅ SPAWNER completo
      {
        id: "spawner1",
        type: "spawner",
        x: 400,
        y: 50,
        w: 1,
        h: 1,
        props: {
          // Transform
          x: 400,
          y: 50,
          
          // Spawner
          spawner: true,
          spawnRate: 2.0,
          maxEnemies: 20,
          currentWave: 1,
          enemiesSpawned: 0,
          
          // Spawn area
          spawnRadius: 50,
          spawnType: "enemy"
        }
      }
    ]
  }
};

// Validação
const result = validateRuntimeAgainstProfile(completeRuntime, TOPDOWN_SHOOTER_PROFILE);

// Resultado:
// isValid: true ✅
// summary.critical: 0
// summary.severe: 0
// summary.minor: 0
// 
// ✅ Runtime válido para gênero 'topdown-shooter-survival'
```

---

## 🎯 EXEMPLO 5: Runtime Quase Completo (Falta UI)

```typescript
const almostCompleteRuntime: OrdaxSpec = {
  gameType: "topdown",
  title: "Almost There",
  description: "Has systems and entities, but missing UI",
  
  systems: [
    "PhysicsSystem",
    "CollisionSystem",
    "AISystem",
    "SpawnerSystem",
    "ScoreSystem",
    "TimerSystem",
    "UISystem"
  ],
  
  scene: {
    gravity: { x: 0, y: 0 },
    entities: [
      // Player completo
      {
        id: "player1",
        type: "player",
        x: 400,
        y: 300,
        w: 32,
        h: 32,
        props: {
          x: 400, y: 300, rotation: 0,
          vx: 0, vy: 0, speed: 200,
          health: 100, maxHealth: 100,
          fireRate: 0.2, damage: 25,
          w: 32, h: 32, radius: 16
        }
      },
      // Enemy completo
      {
        id: "enemy1",
        type: "enemy",
        x: 200,
        y: 100,
        w: 24,
        h: 24,
        props: {
          x: 200, y: 100, rotation: 0,
          vx: 0, vy: 0, speed: 100,
          health: 50, maxHealth: 50,
          ai: "chase", target: "player",
          damage: 10,
          w: 24, h: 24, radius: 12
        }
      },
      // Bullet completo
      {
        id: "bullet1",
        type: "bullet",
        x: 0,
        y: 0,
        w: 4,
        h: 4,
        props: {
          speed: 400, damage: 25,
          lifetime: 2.0, ttl: 2.0
        }
      },
      // Spawner completo
      {
        id: "spawner1",
        type: "spawner",
        x: 400,
        y: 50,
        w: 1,
        h: 1,
        props: {
          spawner: true,
          spawnRate: 2.0,
          maxEnemies: 20
        }
      }
    ]
  }
  
  // ❌ Falta: UI (StartScreen, HUD, GameOverScreen)
  // ❌ Falta: Controles (WASD, SPACE)
  // ❌ Falta: Sinais (player_health, score, timer)
};

// Validação
const result = validateRuntimeAgainstProfile(almostCompleteRuntime, TOPDOWN_SHOOTER_PROFILE);

// Resultado:
// isValid: false
// summary.critical: 5 (UI + Controles)
// summary.severe: 3 (Sinais)
// 
// Violações Críticas:
// - UI_START_SCREEN: StartScreen obrigatória ausente
// - UI_HUD: HUD obrigatória ausente
// - UI_GAME_OVER: GameOverScreen obrigatória ausente
// - CTRL_MOVEMENT: Controles de movimento ausentes
// - CTRL_ACTION: Controles de ação ausentes
// 
// Violações Graves:
// - SIG_PLAYER_HEALTH: Sinal obrigatório ausente
// - SIG_SCORE: Sinal obrigatório ausente
// - SIG_TIMER: Sinal obrigatório ausente
```

---

## 🔧 EXEMPLO 6: Corrigindo Violações Passo a Passo

### Passo 1: Runtime Inicial (Vazio)

```typescript
let runtime: OrdaxSpec = {
  gameType: "topdown",
  title: "Building Step by Step",
  description: "Adding elements incrementally",
  systems: [],
  scene: {
    gravity: { x: 0, y: 0 },
    entities: []
  }
};

let result = validateRuntimeAgainstProfile(runtime, TOPDOWN_SHOOTER_PROFILE);
console.log(`Critical: ${result.summary.critical}`); // 11
```

### Passo 2: Adicionar Sistemas

```typescript
runtime.systems = [
  "PhysicsSystem",
  "CollisionSystem",
  "AISystem",
  "SpawnerSystem",
  "ScoreSystem",
  "TimerSystem",
  "UISystem"
];

result = validateRuntimeAgainstProfile(runtime, TOPDOWN_SHOOTER_PROFILE);
console.log(`Critical: ${result.summary.critical}`); // 4 (só entidades faltando)
```

### Passo 3: Adicionar Player

```typescript
runtime.scene.entities.push({
  id: "player1",
  type: "player",
  x: 400,
  y: 300,
  w: 32,
  h: 32,
  props: {
    x: 400, y: 300, rotation: 0,
    vx: 0, vy: 0, speed: 200,
    health: 100, maxHealth: 100,
    fireRate: 0.2, damage: 25,
    w: 32, h: 32, radius: 16
  }
});

result = validateRuntimeAgainstProfile(runtime, TOPDOWN_SHOOTER_PROFILE);
console.log(`Critical: ${result.summary.critical}`); // 3 (enemy, bullet, spawner)
```

### Passo 4: Adicionar Enemy

```typescript
runtime.scene.entities.push({
  id: "enemy1",
  type: "enemy",
  x: 200,
  y: 100,
  w: 24,
  h: 24,
  props: {
    x: 200, y: 100, rotation: 0,
    vx: 0, vy: 0, speed: 100,
    health: 50, maxHealth: 50,
    ai: "chase", target: "player",
    damage: 10,
    w: 24, h: 24, radius: 12
  }
});

result = validateRuntimeAgainstProfile(runtime, TOPDOWN_SHOOTER_PROFILE);
console.log(`Critical: ${result.summary.critical}`); // 2 (bullet, spawner)
```

### Passo 5: Adicionar Bullet

```typescript
runtime.scene.entities.push({
  id: "bullet1",
  type: "bullet",
  x: 0,
  y: 0,
  w: 4,
  h: 4,
  props: {
    speed: 400,
    damage: 25,
    lifetime: 2.0
  }
});

result = validateRuntimeAgainstProfile(runtime, TOPDOWN_SHOOTER_PROFILE);
console.log(`Critical: ${result.summary.critical}`); // 1 (spawner)
```

### Passo 6: Adicionar Spawner

```typescript
runtime.scene.entities.push({
  id: "spawner1",
  type: "spawner",
  x: 400,
  y: 50,
  w: 1,
  h: 1,
  props: {
    spawner: true,
    spawnRate: 2.0,
    maxEnemies: 20
  }
});

result = validateRuntimeAgainstProfile(runtime, TOPDOWN_SHOOTER_PROFILE);
console.log(`Critical: ${result.summary.critical}`); // 0 ✅

// Agora só faltam UI, Controles e Sinais (não críticos para sistemas/entidades)
console.log(`Valid: ${result.isValid}`); // true (se ignorar UI/Controles)
```

---

## 📊 Resumo de Violações por Categoria

| Categoria | Exemplo | Nível | Impacto |
|-----------|---------|-------|---------|
| **Sistemas** | Falta `CollisionSystem` | CRITICAL | Jogo não funciona |
| **Entidades** | Falta `enemy` | CRITICAL | Gênero não existe |
| **Componentes** | Player sem `Health` | CRITICAL | Entidade não funciona |
| **Props** | Player sem `speed` | SEVERE | Funcionalidade comprometida |
| **UI** | Falta `HUD` | CRITICAL | Jogo não é jogável |
| **Controles** | Falta `WASD` | CRITICAL | Jogador não consegue jogar |
| **Sinais** | Falta `player_health` | SEVERE | Feedback comprometido |

---

## 🎯 Dicas para Criar Runtime Válido

### 1. Comece pelos Sistemas
```typescript
systems: [
  "PhysicsSystem",
  "CollisionSystem",
  "AISystem",
  "SpawnerSystem",
  "ScoreSystem",
  "TimerSystem",
  "UISystem"
]
```

### 2. Adicione Entidades Obrigatórias
- `player` (com todos os componentes)
- `enemy` (com AI)
- `bullet` (com velocidade)
- `spawner` (com taxa de spawn)

### 3. Garanta Componentes Críticos
- **Transform**: `x`, `y`, `rotation`
- **Velocity**: `vx`, `vy`, `speed`
- **Health**: `health`, `maxHealth`
- **Weapon**: `fireRate`, `damage`
- **Collider**: `w`, `h`, `radius`
- **AI**: `ai`, `behavior`, `target`

### 4. Adicione Props Obrigatórias
- Player: `health`, `speed`, `fireRate`
- Enemy: `health`, `speed`, `damage`
- Bullet: `speed`, `damage`
- Spawner: `spawnRate`

### 5. Valide Continuamente
```typescript
const result = validateRuntimeAgainstProfile(runtime, TOPDOWN_SHOOTER_PROFILE);
if (!result.isValid) {
  console.log(generateMissingElementsReport(result));
}
```

---

**Status:** ✅ Exemplos prontos para referência

Use estes exemplos como guia para criar runtimes válidos ou para entender por que um runtime está inválido.
