# Ordax Runtime Core Architecture

## Arquitetura Central do Runtime da Ordax Engine

**Versão:** 1.0.0  
**Data:** 25 de Janeiro de 2026  
**Status:** CANÔNICO

---

## 1. Visão Geral

A Ordax Engine possui uma arquitetura em camadas fixas e imutáveis. Cada camada tem responsabilidades claras e regras de comunicação rígidas.

```
┌─────────────────────────────────────────┐
│           UI LAYER (Telas)              │
│  StartScreen │ HUD │ GameOverScreen     │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         EVENT LAYER (Eventos)           │
│  onStart │ onGameOver │ onPause         │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│      SYSTEMS LAYER (Lógica de Jogo)    │
│  Physics │ Collision │ AI │ Particles  │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│       LOOP LAYER (Game Loop)            │
│  update(deltaTime) │ render()           │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         FSM LAYER (Estados)             │
│  START │ PLAYING │ PAUSED │ GAME_OVER  │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│       INPUT LAYER (Entrada)             │
│  Keyboard │ Mouse │ Touch │ Gamepad    │
└─────────────────────────────────────────┘
```

---

## 2. Camadas Fixas da Engine

### Layer 1: INPUT LAYER (Base)
**Responsabilidade:** Capturar e normalizar entrada do usuário

**Módulos Obrigatórios:**
- `InputManager`: Gerenciamento centralizado de input
- `KeyboardHandler`: Captura de teclado
- `MouseHandler`: Captura de mouse
- `TouchHandler`: Captura de touch (mobile)

**Regras:**
- ✅ Pode ser chamado por: FSM Layer, Systems Layer
- ❌ Não pode chamar: Nenhuma outra camada (é a base)
- ✅ Deve expor: Estado atual de teclas/mouse/touch
- ❌ Não deve: Conter lógica de jogo

**Interface Mínima:**
```typescript
interface InputManager {
  keys: Map<string, boolean>
  mouse: { x: number, y: number, pressed: boolean }
  isKeyPressed(key: string): boolean
  getMousePosition(): { x: number, y: number }
}
```

---

### Layer 2: FSM LAYER (Controle de Estados)
**Responsabilidade:** Gerenciar estados do jogo e transições

**Módulos Obrigatórios:**
- `GameState`: Enum de estados
- `StateManager`: Gerenciador de transições

**Estados Obrigatórios:**
```typescript
enum GameState {
  START = 'START',       // Tela inicial
  PLAYING = 'PLAYING',   // Jogando
  PAUSED = 'PAUSED',     // Pausado
  GAME_OVER = 'GAME_OVER' // Fim de jogo
}
```

**Regras:**
- ✅ Pode ser chamado por: Loop Layer, Event Layer, UI Layer
- ✅ Pode chamar: Input Layer (para detectar input de transição)
- ✅ Deve expor: Estado atual, método de transição
- ❌ Não deve: Conter lógica de gameplay

**Interface Mínima:**
```typescript
interface StateManager {
  currentState: GameState
  transitionTo(newState: GameState): void
  canTransition(from: GameState, to: GameState): boolean
}
```

---

### Layer 3: LOOP LAYER (Game Loop)
**Responsabilidade:** Orquestrar update e render

**Módulos Obrigatórios:**
- `GameLoop`: Loop principal com requestAnimationFrame
- `TimeManager`: Cálculo de deltaTime

**Regras:**
- ✅ Pode ser chamado por: Engine initialization
- ✅ Pode chamar: FSM Layer, Systems Layer, UI Layer
- ✅ Deve expor: Métodos update() e render()
- ❌ Não deve: Conter lógica de gameplay específica

**Estrutura Obrigatória:**
```typescript
function gameLoop(timestamp: number): void {
  // 1. Calcular deltaTime
  const deltaTime = calculateDeltaTime(timestamp)
  
  // 2. Verificar estado atual
  const state = stateManager.currentState
  
  // 3. Update baseado no estado
  if (state === GameState.PLAYING) {
    update(deltaTime)
  }
  
  // 4. Render baseado no estado
  render(state)
  
  // 5. Continuar loop
  requestAnimationFrame(gameLoop)
}
```

---

### Layer 4: SYSTEMS LAYER (Lógica de Jogo)
**Responsabilidade:** Implementar mecânicas e sistemas do jogo

**Módulos Comuns:**
- `PhysicsSystem`: Movimento e física
- `CollisionSystem`: Detecção de colisões
- `AISystem`: Inteligência artificial
- `ParticleSystem`: Efeitos visuais
- `AudioSystem`: Som e música

**Regras:**
- ✅ Pode ser chamado por: Loop Layer
- ✅ Pode chamar: Input Layer, FSM Layer
- ✅ Deve expor: Métodos update(deltaTime)
- ✅ Deve usar: deltaTime para todas as atualizações

**Interface Mínima:**
```typescript
interface GameSystem {
  update(deltaTime: number): void
  reset(): void
}
```

---

### Layer 5: EVENT LAYER (Eventos)
**Responsabilidade:** Gerenciar eventos do jogo

**Módulos Obrigatórios:**
- `EventManager`: Sistema de pub/sub

**Eventos Comuns:**
- `onGameStart`: Jogo iniciado
- `onGameOver`: Jogo terminado
- `onPause`: Jogo pausado
- `onScoreChange`: Score alterado
- `onPlayerDeath`: Jogador morreu

**Regras:**
- ✅ Pode ser chamado por: Qualquer camada
- ✅ Pode chamar: Qualquer camada (via callbacks)
- ✅ Deve expor: on(), emit(), off()
- ❌ Não deve: Conter lógica de jogo

**Interface Mínima:**
```typescript
interface EventManager {
  on(event: string, callback: Function): void
  emit(event: string, data?: any): void
  off(event: string, callback: Function): void
}
```

---

### Layer 6: UI LAYER (Interface)
**Responsabilidade:** Renderizar interface do usuário

**Módulos Obrigatórios:**
- `StartScreen`: Tela inicial
- `HUD`: Interface durante gameplay
- `GameOverScreen`: Tela de fim de jogo
- `PauseMenu`: Menu de pausa (opcional mas recomendado)

**Regras:**
- ✅ Pode ser chamado por: Loop Layer (render)
- ✅ Pode chamar: FSM Layer (para transições), Input Layer (para botões)
- ✅ Deve expor: Métodos render(ctx)
- ❌ Não deve: Conter lógica de gameplay

**Interface Mínima:**
```typescript
interface UIComponent {
  render(ctx: CanvasRenderingContext2D): void
  handleClick?(x: number, y: number): void
}
```

---

## 3. Módulos Obrigatórios (Core)

### TimeManager
```typescript
class TimeManager {
  private lastTimestamp: number = 0
  
  calculateDeltaTime(timestamp: number): number {
    const delta = timestamp - this.lastTimestamp
    this.lastTimestamp = timestamp
    return delta / 1000 // Converter para segundos
  }
}
```

### ViewportManager
```typescript
class ViewportManager {
  canvas: HTMLCanvasElement
  
  handleResize(): void {
    this.canvas.width = window.innerWidth
    this.canvas.height = window.innerHeight
  }
  
  init(): void {
    window.addEventListener('resize', () => this.handleResize())
    this.handleResize()
  }
}
```

### SaveManager
```typescript
class SaveManager {
  private readonly STORAGE_KEY = 'ordax_game_save'
  
  saveHighScore(score: number): void {
    localStorage.setItem(this.STORAGE_KEY, JSON.stringify({ highScore: score }))
  }
  
  loadHighScore(): number {
    const data = localStorage.getItem(this.STORAGE_KEY)
    return data ? JSON.parse(data).highScore : 0
  }
}
```

---

## 4. Regras de Comunicação Entre Camadas

### ✅ Permitido
- Camadas superiores podem chamar camadas inferiores
- Event Layer pode comunicar entre qualquer camada (via eventos)
- Input Layer pode ser consultado por qualquer camada

### ❌ Proibido
- Camadas inferiores não podem chamar camadas superiores diretamente
- UI Layer não pode chamar Systems Layer diretamente
- Systems Layer não pode chamar UI Layer diretamente

### 🔄 Comunicação Indireta (via Events)
```typescript
// ✅ CORRETO: Systems → Events → UI
collisionSystem.on('playerDeath', () => {
  eventManager.emit('gameOver', { score: currentScore })
})

eventManager.on('gameOver', (data) => {
  stateManager.transitionTo(GameState.GAME_OVER)
})

// ❌ ERRADO: Systems → UI diretamente
collisionSystem.showGameOverScreen() // PROIBIDO!
```

---

## 5. Fluxo de Dados Canônico

### Inicialização
```
1. Criar Canvas
2. Inicializar ViewportManager
3. Inicializar InputManager
4. Inicializar SaveManager
5. Inicializar StateManager (estado = START)
6. Inicializar Systems
7. Iniciar GameLoop
```

### Durante o Jogo
```
Input → FSM → Loop → Systems → Events → UI
  ↓       ↓      ↓       ↓        ↓      ↓
User  → State → Δt → Gameplay → Notify → Render
```

### Transição de Estado
```
1. Input detecta ação (ex: clique em "Start")
2. FSM valida transição
3. FSM muda estado
4. Event é emitido (ex: 'gameStart')
5. Systems reagem ao evento
6. UI atualiza baseado no novo estado
```

---

## 6. Arquivos Protegidos vs Mutáveis

### 🔒 Protegidos (Não devem ser modificados pelo AI)
- `GameLoop.ts`: Estrutura do loop
- `TimeManager.ts`: Cálculo de deltaTime
- `InputManager.ts`: Captura de input
- `StateManager.ts`: Gerenciamento de FSM

### 🔓 Mutáveis (Podem ser modificados pelo AI)
- `game.ts`: Lógica específica do jogo
- `entities.ts`: Entidades do jogo
- `config.ts`: Configurações do jogo
- `assets.ts`: Recursos visuais/sonoros

### ⚙️ Gerados (Criados pelo AI para cada jogo)
- Sistemas específicos (ex: `EnemySpawner.ts`)
- Componentes de UI customizados
- Lógica de gameplay única

---

## 7. Padrões de Implementação

### Singleton para Managers
```typescript
class InputManager {
  private static instance: InputManager
  
  static getInstance(): InputManager {
    if (!this.instance) {
      this.instance = new InputManager()
    }
    return this.instance
  }
}
```

### Dependency Injection para Systems
```typescript
class PhysicsSystem {
  constructor(
    private inputManager: InputManager,
    private eventManager: EventManager
  ) {}
}
```

### Observer Pattern para Events
```typescript
class EventManager {
  private listeners: Map<string, Function[]> = new Map()
  
  on(event: string, callback: Function): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, [])
    }
    this.listeners.get(event)!.push(callback)
  }
}
```

---

## 8. Validação Arquitetural

O validador constitucional deve verificar:

1. ✅ Todas as camadas obrigatórias existem
2. ✅ Módulos core estão presentes
3. ✅ Fluxo de dados segue a arquitetura
4. ✅ Não há violações de comunicação entre camadas
5. ✅ deltaTime é usado em todos os updates

---

## 9. Extensibilidade

### Como Adicionar Novos Sistemas
```typescript
// 1. Implementar interface GameSystem
class NewSystem implements GameSystem {
  update(deltaTime: number): void {
    // Lógica do sistema
  }
  
  reset(): void {
    // Reset do sistema
  }
}

// 2. Registrar no game loop
const newSystem = new NewSystem()
systems.push(newSystem)
```

### Como Adicionar Novos Estados
```typescript
// 1. Estender enum GameState
enum GameState {
  // ... estados existentes
  CUTSCENE = 'CUTSCENE' // Novo estado
}

// 2. Adicionar lógica no loop
if (state === GameState.CUTSCENE) {
  updateCutscene(deltaTime)
}
```

---

## 10. Assinatura

```
ORDAX RUNTIME CORE ARCHITECTURE
Versão: 1.0.0
Data: 2026-01-25
Status: CANÔNICO E IMUTÁVEL
```

**Esta arquitetura é a fundação da Ordax Engine e não pode ser violada.**
