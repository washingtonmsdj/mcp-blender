# 📊 DIAGRAMA: Profile Validator - Top-Down Shooter

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                    ORDAX RUNTIME VALIDATOR                      │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
        ┌────────────────────────────────────────┐
        │   validateRuntimeAgainstProfile()      │
        │                                        │
        │   Input:  OrdaxSpec + RuntimeProfile   │
        │   Output: ProfileValidationResult      │
        └────────────────────────────────────────┘
                                 │
                ┌────────────────┼────────────────┐
                ▼                ▼                ▼
        ┌───────────┐    ┌───────────┐    ┌───────────┐
        │  Systems  │    │ Entities  │    │    UI     │
        │ Validator │    │ Validator │    │ Validator │
        └───────────┘    └───────────┘    └───────────┘
                ▼                ▼                ▼
        ┌───────────┐    ┌───────────┐    ┌───────────┐
        │ Controls  │    │  Signals  │    │ Lifecycle │
        │ Validator │    │ Validator │    │ Validator │
        └───────────┘    └───────────┘    └───────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │ ProfileValidationResult│
                    │                        │
                    │ - isValid: boolean     │
                    │ - violations: []       │
                    │ - missingElements: {}  │
                    │ - summary: {}          │
                    └────────────────────────┘
```

---

## 🎯 Perfil Canônico: Top-Down Shooter Survival

```
┌─────────────────────────────────────────────────────────────────┐
│              TOPDOWN_SHOOTER_PROFILE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📦 SISTEMAS (7)                                                │
│  ├─ PhysicsSystem      ⚡ Movimento                            │
│  ├─ CollisionSystem    💥 Colisões                             │
│  ├─ AISystem           🤖 Comportamento                        │
│  ├─ SpawnerSystem      🌊 Ondas                                │
│  ├─ ScoreSystem        🏆 Pontuação                            │
│  ├─ TimerSystem        ⏱️  Tempo                               │
│  └─ UISystem           🖥️  Interface                           │
│                                                                 │
│  🎮 ENTIDADES (4)                                               │
│  ├─ player                                                      │
│  │  ├─ Transform  (x, y, rotation)         [CRITICAL]          │
│  │  ├─ Velocity   (vx, vy, speed)          [CRITICAL]          │
│  │  ├─ Health     (health, hp)             [CRITICAL]          │
│  │  ├─ Weapon     (fireRate, damage)       [CRITICAL]          │
│  │  └─ Collider   (w, h, radius)           [CRITICAL]          │
│  │                                                              │
│  ├─ enemy                                                       │
│  │  ├─ Transform                            [CRITICAL]          │
│  │  ├─ Velocity                             [CRITICAL]          │
│  │  ├─ Health                               [CRITICAL]          │
│  │  ├─ AI         (behavior, target)       [CRITICAL]          │
│  │  └─ Collider                             [CRITICAL]          │
│  │                                                              │
│  ├─ bullet                                                      │
│  │  ├─ Transform                            [CRITICAL]          │
│  │  ├─ Velocity                             [CRITICAL]          │
│  │  ├─ Collider                             [CRITICAL]          │
│  │  └─ Lifetime   (ttl)                     [optional]          │
│  │                                                              │
│  └─ spawner                                                     │
│     ├─ Transform                            [CRITICAL]          │
│     └─ Spawner    (spawnRate, maxEnemies)  [CRITICAL]          │
│                                                                 │
│  🖥️  UI (3)                                                     │
│  ├─ StartScreen   (title, startButton, instructions)           │
│  ├─ HUD           (health, score, timer, wave)                 │
│  └─ GameOverScreen (finalScore, survivalTime, restartButton)   │
│                                                                 │
│  🎮 CONTROLES (2)                                               │
│  ├─ Movement      (W, A, S, D)                                 │
│  └─ Action        (SPACE, MOUSE_LEFT)                          │
│                                                                 │
│  📡 SINAIS (4)                                                  │
│  ├─ player_health [REQUIRED]                                   │
│  ├─ score         [REQUIRED]                                   │
│  ├─ timer         [REQUIRED]                                   │
│  └─ wave          [optional]                                   │
│                                                                 │
│  🔄 LIFECYCLE                                                   │
│  ├─ Start:   Jogador clica 'Start'                            │
│  ├─ Lose:    player.health <= 0                               │
│  └─ Restart: Jogador clica 'Restart'                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔍 Fluxo de Validação

```
┌─────────────┐
│ OrdaxSpec   │
│ (runtime)   │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│ 1. VALIDAR SISTEMAS                     │
│                                         │
│ Required: [PhysicsSystem, ...]          │
│ Actual:   [PhysicsSystem]               │
│                                         │
│ ❌ Missing: CollisionSystem, AISystem   │
│    → CRITICAL violation                 │
└─────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│ 2. VALIDAR ENTIDADES                    │
│                                         │
│ Required: [player, enemy, bullet, ...]  │
│ Actual:   [player]                      │
│                                         │
│ ❌ Missing: enemy, bullet, spawner      │
│    → CRITICAL violation                 │
└─────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│ 3. VALIDAR COMPONENTES                  │
│                                         │
│ Entity: player                          │
│ Required: [Transform, Velocity, ...]    │
│ Actual:   [Transform]                   │
│                                         │
│ ❌ Missing: Velocity, Health, Weapon    │
│    → CRITICAL violation                 │
└─────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│ 4. VALIDAR PROPS                        │
│                                         │
│ Entity: player                          │
│ Required: {health, speed, fireRate}     │
│ Actual:   {}                            │
│                                         │
│ ❌ Missing: health, speed, fireRate     │
│    → SEVERE violation                   │
└─────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│ 5. VALIDAR UI                           │
│                                         │
│ Required: StartScreen, HUD, GameOver    │
│ Actual:   (none)                        │
│                                         │
│ ❌ Missing: StartScreen, HUD, GameOver  │
│    → CRITICAL violation                 │
└─────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│ 6. VALIDAR CONTROLES                    │
│                                         │
│ Required: [W,A,S,D], [SPACE]            │
│ Actual:   (none)                        │
│                                         │
│ ❌ Missing: movement, action            │
│    → CRITICAL violation                 │
└─────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│ 7. VALIDAR SINAIS                       │
│                                         │
│ Required: player_health, score, timer   │
│ Actual:   (none)                        │
│                                         │
│ ❌ Missing: player_health, score, timer │
│    → SEVERE violation                   │
└─────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│ ProfileValidationResult                 │
│                                         │
│ isValid: false                          │
│ violations: [                           │
│   {id: "SYS_COLLISIONSYSTEM", ...},     │
│   {id: "ENT_ENEMY", ...},               │
│   {id: "COMP_PLAYER_HEALTH", ...},      │
│   ...                                   │
│ ]                                       │
│ summary: {                              │
│   critical: 12,                         │
│   severe: 5,                            │
│   minor: 0                              │
│ }                                       │
│ missingElements: {                      │
│   systems: ["CollisionSystem", ...],    │
│   entities: ["enemy", ...],             │
│   components: {                         │
│     player: ["Health", "Weapon", ...]   │
│   },                                    │
│   ...                                   │
│ }                                       │
└─────────────────────────────────────────┘
```

---

## 🚦 Níveis de Violação

```
┌─────────────────────────────────────────────────────────────────┐
│                      VIOLATION LEVELS                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  🔴 CRITICAL                                                    │
│  ├─ Sistemas faltantes                                         │
│  ├─ Entidades faltantes                                        │
│  ├─ Componentes críticos faltantes                            │
│  ├─ UI faltante                                                │
│  └─ Controles faltantes                                        │
│                                                                 │
│  Action: ❌ BLOQUEAR COMPILAÇÃO                                │
│  Reason: Jogo não funciona sem esses elementos                 │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  🟠 SEVERE                                                      │
│  ├─ Props obrigatórias faltantes                              │
│  └─ Sinais obrigatórios faltantes                             │
│                                                                 │
│  Action: ⚠️  AVISAR FORTEMENTE                                 │
│  Reason: Funcionalidade comprometida                           │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  🟡 MINOR                                                       │
│  ├─ Componentes opcionais faltantes                           │
│  └─ Sinais opcionais faltantes                                │
│                                                                 │
│  Action: ℹ️  AVISAR LEVEMENTE                                  │
│  Reason: Nice-to-have                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Integração com Protocolo de Compilação

```
┌─────────────────────────────────────────────────────────────────┐
│                   COMPILER PROTOCOL FLOW                        │
└─────────────────────────────────────────────────────────────────┘

User Input
    │
    ▼
┌─────────────────┐
│ 1. PARSE        │  Parse natural language → GamePlan
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. PLAN         │  Generate structured plan
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 3. CODE         │  Generate TypeScript code
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. EXTRACT      │  Extract RuntimeSpec from code                │
└────────┬────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. VALIDATE     │  🆕 validateRuntimeAgainstProfile()           │
│                 │                                               │
│  Input:  runtimeSpec + TOPDOWN_SHOOTER_PROFILE                 │
│  Output: ProfileValidationResult                               │
│                                                                 │
│  if (!result.isValid) {                                        │
│    return {                                                    │
│      phase: "validation",                                      │
│      status: "error",                                          │
│      violations: result.violations,                            │
│      missingElements: result.missingElements                   │
│    }                                                           │
│  }                                                             │
└────────┬────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│ 6. COMPILE      │  Compile to executable
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 7. RUN          │  Execute game
└─────────────────┘
```

---

## 📈 Exemplo de Uso

### ❌ Runtime Incompleto

```typescript
const incompleteRuntime: OrdaxSpec = {
  systems: ["PhysicsSystem"],  // Faltam 6 sistemas
  scene: {
    entities: [
      {
        type: "player",
        props: {}  // Faltam componentes
      }
    ]
  }
};

const result = validateRuntimeAgainstProfile(
  incompleteRuntime,
  TOPDOWN_SHOOTER_PROFILE
);

// result.isValid = false
// result.summary.critical = 12
// result.missingElements.systems = [
//   "CollisionSystem", "AISystem", "SpawnerSystem", ...
// ]
```

### ✅ Runtime Completo

```typescript
const completeRuntime: OrdaxSpec = {
  systems: [
    "PhysicsSystem", "CollisionSystem", "AISystem",
    "SpawnerSystem", "ScoreSystem", "TimerSystem", "UISystem"
  ],
  scene: {
    entities: [
      {
        type: "player",
        props: {
          x: 400, y: 300,
          health: 100, speed: 200, fireRate: 0.2,
          vx: 0, vy: 0, w: 32, h: 32
        }
      },
      {
        type: "enemy",
        props: {
          health: 50, speed: 100, damage: 10,
          ai: "chase", target: "player"
        }
      },
      {
        type: "bullet",
        props: { speed: 400, damage: 25 }
      },
      {
        type: "spawner",
        props: { spawnRate: 2.0, spawner: true }
      }
    ]
  }
};

const result = validateRuntimeAgainstProfile(
  completeRuntime,
  TOPDOWN_SHOOTER_PROFILE
);

// result.isValid = true ✅
// result.summary.critical = 0
```

---

## 🎯 Próximos Passos

```
FASE 2.1: Integração com Protocolo
├─ Adicionar validação no game-ai-chat-stream
├─ Retornar violações na fase de validação
└─ IA usar violações para corrigir código

FASE 2.2: Geração Assistida
├─ IA detecta violações CRITICAL
├─ IA gera código para corrigir automaticamente
└─ Loop até runtime estar válido

FASE 2.3: Mais Gêneros
├─ platformer.ts profile
├─ puzzle.ts profile
└─ racing.ts profile
```

---

**Status:** ✅ **IMPLEMENTADO E PRONTO PARA USO**
