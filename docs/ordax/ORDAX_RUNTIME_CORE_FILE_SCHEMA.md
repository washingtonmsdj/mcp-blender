# Ordax Runtime Core File Schema

## Estrutura Fixa de Arquivos da Engine Runtime

**Versão:** 1.0.0  
**Data:** 25 de Janeiro de 2026  
**Status:** CANÔNICO

---

## 1. Estrutura de Diretórios Obrigatória

```
src/games/[game-name]/
├── core/                    # 🔒 PROTEGIDO - Arquivos da engine
│   ├── GameLoop.ts         # Loop principal
│   ├── TimeManager.ts      # Gerenciamento de tempo
│   ├── InputManager.ts     # Gerenciamento de input
│   ├── StateManager.ts     # Máquina de estados
│   ├── SaveManager.ts      # Persistência
│   ├── ViewportManager.ts  # Gerenciamento de viewport
│   └── EventManager.ts     # Sistema de eventos
│
├── systems/                 # ⚙️ GERADO - Sistemas do jogo
│   ├── PhysicsSystem.ts    # Sistema de física
│   ├── CollisionSystem.ts  # Sistema de colisão
│   ├── RenderSystem.ts     # Sistema de renderização
│   └── [CustomSystem].ts   # Sistemas customizados
│
├── ui/                      # 🔓 MUTÁVEL - Interface do usuário
│   ├── StartScreen.ts      # Tela inicial (OBRIGATÓRIO)
│   ├── HUD.ts              # Interface durante jogo (OBRIGATÓRIO)
│   ├── GameOverScreen.ts   # Tela de fim (OBRIGATÓRIO)
│   └── PauseMenu.ts        # Menu de pausa (OPCIONAL)
│
├── entities/                # ⚙️ GERADO - Entidades do jogo
│   ├── Player.ts           # Jogador
│   ├── Enemy.ts            # Inimigos
│   └── [CustomEntity].ts   # Entidades customizadas
│
├── config/                  # 🔓 MUTÁVEL - Configurações
│   ├── constants.ts        # Constantes do jogo
│   ├── assets.ts           # Definição de assets
│   └── settings.ts         # Configurações gerais
│
├── utils/                   # 🔓 MUTÁVEL - Utilitários
│   ├── math.ts             # Funções matemáticas
│   ├── helpers.ts          # Funções auxiliares
│   └── pool.ts             # Object pooling
│
├── game.ts                  # 🔓 MUTÁVEL - Lógica principal do jogo
├── types.ts                 # 🔓 MUTÁVEL - Tipos TypeScript
└── index.ts                 # 🔒 PROTEGIDO - Entry point
```

---

## 2. Arquivos Obrigatórios (Core)

### 2.1. GameLoop.ts
**Status:** 🔒 PROTEGIDO  
**Propósito:** Loop principal do jogo

```typescript
// Estrutura mínima obrigatória
export class GameLoop {
  private lastTimestamp: number = 0
  private isRunning: boolean = false
  
  start(): void {
    this.isRunning = true
    requestAnimationFrame((timestamp) => this.loop(timestamp))
  }
  
  private loop(timestamp: number): void {
    if (!this.isRunning) return
    
    const deltaTime = this.calculateDeltaTime(timestamp)
    
    this.update(deltaTime)
    this.render()
    
    requestAnimationFrame((timestamp) => this.loop(timestamp))
  }
  
  private calculateDeltaTime(timestamp: number): number {
    const delta = timestamp - this.lastTimestamp
    this.lastTimestamp = timestamp
    return delta / 1000
  }
  
  protected update(deltaTime: number): void {
    // Implementado por subclasse ou composição
  }
  
  protected render(): void {
    // Implementado por subclasse ou composição
  }
  
  stop(): void {
    this.isRunning = false
  }
}
```

**Validação:**
- ✅ Deve usar `requestAnimationFrame`
- ✅ Deve calcular `deltaTime`
- ✅ Deve separar `update()` e `render()`
- ❌ Não pode usar `setInterval` ou `setTimeout`

---

### 2.2. TimeManager.ts
**Status:** 🔒 PROTEGIDO  
**Propósito:** Gerenciamento de tempo e deltaTime

```typescript
export class TimeManager {
  private lastTimestamp: number = 0
  private deltaTime: number = 0
  private totalTime: number = 0
  private fps: number = 0
  private frameCount: number = 0
  
  update(timestamp: number): void {
    this.deltaTime = (timestamp - this.lastTimestamp) / 1000
    this.lastTimestamp = timestamp
    this.totalTime += this.deltaTime
    
    this.frameCount++
    if (this.frameCount % 60 === 0) {
      this.fps = Math.round(1 / this.deltaTime)
    }
  }
  
  getDeltaTime(): number {
    return this.deltaTime
  }
  
  getTotalTime(): number {
    return this.totalTime
  }
  
  getFPS(): number {
    return this.fps
  }
}
```

**Validação:**
- ✅ Deve expor `getDeltaTime()`
- ✅ Deve calcular deltaTime em segundos
- ✅ Deve rastrear tempo total

---

### 2.3. InputManager.ts
**Status:** 🔒 PROTEGIDO  
**Propósito:** Gerenciamento centralizado de input

```typescript
export class InputManager {
  private keys: Map<string, boolean> = new Map()
  private mouse: { x: number; y: number; pressed: boolean } = { x: 0, y: 0, pressed: false }
  private touches: Map<number, { x: number; y: number }> = new Map()
  
  init(canvas: HTMLCanvasElement): void {
    // Keyboard
    window.addEventListener('keydown', (e) => this.keys.set(e.key, true))
    window.addEventListener('keyup', (e) => this.keys.set(e.key, false))
    
    // Mouse
    canvas.addEventListener('mousemove', (e) => {
      this.mouse.x = e.offsetX
      this.mouse.y = e.offsetY
    })
    canvas.addEventListener('mousedown', () => this.mouse.pressed = true)
    canvas.addEventListener('mouseup', () => this.mouse.pressed = false)
    
    // Touch
    canvas.addEventListener('touchstart', (e) => {
      for (let i = 0; i < e.touches.length; i++) {
        const touch = e.touches[i]
        this.touches.set(touch.identifier, { x: touch.clientX, y: touch.clientY })
      }
    })
    canvas.addEventListener('touchend', (e) => {
      for (let i = 0; i < e.changedTouches.length; i++) {
        this.touches.delete(e.changedTouches[i].identifier)
      }
    })
  }
  
  isKeyPressed(key: string): boolean {
    return this.keys.get(key) || false
  }
  
  getMousePosition(): { x: number; y: number } {
    return { x: this.mouse.x, y: this.mouse.y }
  }
  
  isMousePressed(): boolean {
    return this.mouse.pressed
  }
  
  getTouches(): Map<number, { x: number; y: number }> {
    return this.touches
  }
}
```

**Validação:**
- ✅ Deve suportar teclado, mouse e touch
- ✅ Deve expor métodos de consulta
- ✅ Deve centralizar todos os event listeners

---

### 2.4. StateManager.ts
**Status:** 🔒 PROTEGIDO  
**Propósito:** Máquina de estados do jogo

```typescript
export enum GameState {
  START = 'START',
  PLAYING = 'PLAYING',
  PAUSED = 'PAUSED',
  GAME_OVER = 'GAME_OVER'
}

export class StateManager {
  private currentState: GameState = GameState.START
  private previousState: GameState | null = null
  private listeners: Map<GameState, Function[]> = new Map()
  
  transitionTo(newState: GameState): void {
    if (this.currentState === newState) return
    
    this.previousState = this.currentState
    this.currentState = newState
    
    this.notifyListeners(newState)
  }
  
  getCurrentState(): GameState {
    return this.currentState
  }
  
  getPreviousState(): GameState | null {
    return this.previousState
  }
  
  onStateChange(state: GameState, callback: Function): void {
    if (!this.listeners.has(state)) {
      this.listeners.set(state, [])
    }
    this.listeners.get(state)!.push(callback)
  }
  
  private notifyListeners(state: GameState): void {
    const callbacks = this.listeners.get(state) || []
    callbacks.forEach(cb => cb())
  }
}
```

**Validação:**
- ✅ Deve ter enum `GameState` com 4 estados mínimos
- ✅ Deve expor `transitionTo()` e `getCurrentState()`
- ✅ Deve notificar listeners em mudanças de estado

---

### 2.5. SaveManager.ts
**Status:** 🔒 PROTEGIDO  
**Propósito:** Persistência de dados

```typescript
export interface SaveData {
  highScore: number
  settings?: any
  progress?: any
}

export class SaveManager {
  private readonly STORAGE_KEY: string
  
  constructor(gameId: string) {
    this.STORAGE_KEY = `ordax_${gameId}_save`
  }
  
  save(data: SaveData): void {
    try {
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(data))
    } catch (error) {
      console.error('Failed to save game data:', error)
    }
  }
  
  load(): SaveData {
    try {
      const data = localStorage.getItem(this.STORAGE_KEY)
      return data ? JSON.parse(data) : { highScore: 0 }
    } catch (error) {
      console.error('Failed to load game data:', error)
      return { highScore: 0 }
    }
  }
  
  saveHighScore(score: number): void {
    const data = this.load()
    if (score > data.highScore) {
      data.highScore = score
      this.save(data)
    }
  }
  
  loadHighScore(): number {
    return this.load().highScore
  }
  
  clear(): void {
    localStorage.removeItem(this.STORAGE_KEY)
  }
}
```

**Validação:**
- ✅ Deve usar `localStorage`
- ✅ Deve expor `save()`, `load()`, `saveHighScore()`, `loadHighScore()`
- ✅ Deve ter tratamento de erros

---

### 2.6. ViewportManager.ts
**Status:** 🔒 PROTEGIDO  
**Propósito:** Gerenciamento de viewport e resize

```typescript
export class ViewportManager {
  private canvas: HTMLCanvasElement
  private targetWidth: number
  private targetHeight: number
  private scale: number = 1
  
  constructor(canvas: HTMLCanvasElement, targetWidth: number, targetHeight: number) {
    this.canvas = canvas
    this.targetWidth = targetWidth
    this.targetHeight = targetHeight
  }
  
  init(): void {
    window.addEventListener('resize', () => this.handleResize())
    this.handleResize()
  }
  
  private handleResize(): void {
    const windowWidth = window.innerWidth
    const windowHeight = window.innerHeight
    
    const scaleX = windowWidth / this.targetWidth
    const scaleY = windowHeight / this.targetHeight
    this.scale = Math.min(scaleX, scaleY)
    
    this.canvas.width = this.targetWidth
    this.canvas.height = this.targetHeight
    this.canvas.style.width = `${this.targetWidth * this.scale}px`
    this.canvas.style.height = `${this.targetHeight * this.scale}px`
  }
  
  getScale(): number {
    return this.scale
  }
  
  getWidth(): number {
    return this.targetWidth
  }
  
  getHeight(): number {
    return this.targetHeight
  }
}
```

**Validação:**
- ✅ Deve ter listener de `resize`
- ✅ Deve adaptar canvas ao tamanho da janela
- ✅ Deve manter aspect ratio

---

### 2.7. EventManager.ts
**Status:** 🔒 PROTEGIDO  
**Propósito:** Sistema de eventos pub/sub

```typescript
export class EventManager {
  private listeners: Map<string, Function[]> = new Map()
  
  on(event: string, callback: Function): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, [])
    }
    this.listeners.get(event)!.push(callback)
  }
  
  off(event: string, callback: Function): void {
    const callbacks = this.listeners.get(event)
    if (callbacks) {
      const index = callbacks.indexOf(callback)
      if (index > -1) {
        callbacks.splice(index, 1)
      }
    }
  }
  
  emit(event: string, data?: any): void {
    const callbacks = this.listeners.get(event) || []
    callbacks.forEach(cb => cb(data))
  }
  
  clear(): void {
    this.listeners.clear()
  }
}
```

**Validação:**
- ✅ Deve expor `on()`, `off()`, `emit()`
- ✅ Deve suportar múltiplos listeners por evento

---

## 3. Arquivos Obrigatórios (UI)

### 3.1. StartScreen.ts
**Status:** 🔓 MUTÁVEL  
**Propósito:** Tela inicial do jogo

```typescript
export class StartScreen {
  render(ctx: CanvasRenderingContext2D, width: number, height: number): void {
    // Background
    ctx.fillStyle = '#000'
    ctx.fillRect(0, 0, width, height)
    
    // Title
    ctx.fillStyle = '#fff'
    ctx.font = 'bold 48px Arial'
    ctx.textAlign = 'center'
    ctx.fillText('GAME TITLE', width / 2, height / 2 - 50)
    
    // Start button
    ctx.font = '24px Arial'
    ctx.fillText('Click to Start', width / 2, height / 2 + 50)
  }
  
  handleClick(x: number, y: number, width: number, height: number): boolean {
    // Detectar clique na área de start
    return true // Simplificado
  }
}
```

**Validação:**
- ✅ Deve ter método `render()`
- ✅ Deve ter método `handleClick()` ou equivalente
- ✅ Deve exibir título do jogo e botão de start

---

### 3.2. HUD.ts
**Status:** 🔓 MUTÁVEL  
**Propósito:** Interface durante gameplay

```typescript
export class HUD {
  render(ctx: CanvasRenderingContext2D, score: number, lives: number): void {
    ctx.fillStyle = '#fff'
    ctx.font = '20px Arial'
    ctx.textAlign = 'left'
    
    // Score
    ctx.fillText(`Score: ${score}`, 10, 30)
    
    // Lives
    ctx.fillText(`Lives: ${lives}`, 10, 60)
  }
}
```

**Validação:**
- ✅ Deve ter método `render()`
- ✅ Deve exibir pelo menos score ou informação relevante

---

### 3.3. GameOverScreen.ts
**Status:** 🔓 MUTÁVEL  
**Propósito:** Tela de fim de jogo

```typescript
export class GameOverScreen {
  render(ctx: CanvasRenderingContext2D, width: number, height: number, score: number, highScore: number): void {
    // Background
    ctx.fillStyle = 'rgba(0, 0, 0, 0.8)'
    ctx.fillRect(0, 0, width, height)
    
    // Game Over text
    ctx.fillStyle = '#fff'
    ctx.font = 'bold 48px Arial'
    ctx.textAlign = 'center'
    ctx.fillText('GAME OVER', width / 2, height / 2 - 80)
    
    // Score
    ctx.font = '24px Arial'
    ctx.fillText(`Score: ${score}`, width / 2, height / 2 - 20)
    ctx.fillText(`High Score: ${highScore}`, width / 2, height / 2 + 20)
    
    // Restart button
    ctx.fillText('Click to Restart', width / 2, height / 2 + 80)
  }
  
  handleClick(x: number, y: number, width: number, height: number): boolean {
    // Detectar clique na área de restart
    return true // Simplificado
  }
}
```

**Validação:**
- ✅ Deve ter método `render()`
- ✅ Deve exibir score final e highScore
- ✅ Deve ter opção de restart

---

## 4. Arquivo Principal (game.ts)

**Status:** 🔓 MUTÁVEL  
**Propósito:** Lógica principal do jogo

```typescript
import { GameLoop } from './core/GameLoop'
import { TimeManager } from './core/TimeManager'
import { InputManager } from './core/InputManager'
import { StateManager, GameState } from './core/StateManager'
import { SaveManager } from './core/SaveManager'
import { ViewportManager } from './core/ViewportManager'
import { EventManager } from './core/EventManager'

import { StartScreen } from './ui/StartScreen'
import { HUD } from './ui/HUD'
import { GameOverScreen } from './ui/GameOverScreen'

export class Game extends GameLoop {
  private timeManager: TimeManager
  private inputManager: InputManager
  private stateManager: StateManager
  private saveManager: SaveManager
  private viewportManager: ViewportManager
  private eventManager: EventManager
  
  private startScreen: StartScreen
  private hud: HUD
  private gameOverScreen: GameOverScreen
  
  private score: number = 0
  private highScore: number = 0
  
  constructor(canvas: HTMLCanvasElement) {
    super()
    
    // Inicializar managers
    this.timeManager = new TimeManager()
    this.inputManager = new InputManager()
    this.stateManager = new StateManager()
    this.saveManager = new SaveManager('game-id')
    this.viewportManager = new ViewportManager(canvas, 800, 600)
    this.eventManager = new EventManager()
    
    // Inicializar UI
    this.startScreen = new StartScreen()
    this.hud = new HUD()
    this.gameOverScreen = new GameOverScreen()
    
    // Carregar save
    this.highScore = this.saveManager.loadHighScore()
    
    // Inicializar
    this.inputManager.init(canvas)
    this.viewportManager.init()
  }
  
  protected update(deltaTime: number): void {
    const state = this.stateManager.getCurrentState()
    
    if (state === GameState.PLAYING) {
      // Lógica do jogo usando deltaTime
      this.updateGameplay(deltaTime)
    }
  }
  
  protected render(): void {
    const state = this.stateManager.getCurrentState()
    
    if (state === GameState.START) {
      this.startScreen.render(ctx, width, height)
    } else if (state === GameState.PLAYING) {
      this.renderGameplay()
      this.hud.render(ctx, this.score, lives)
    } else if (state === GameState.GAME_OVER) {
      this.gameOverScreen.render(ctx, width, height, this.score, this.highScore)
    }
  }
  
  private updateGameplay(deltaTime: number): void {
    // Lógica específica do jogo
  }
  
  private renderGameplay(): void {
    // Renderização específica do jogo
  }
}
```

**Validação:**
- ✅ Deve estender `GameLoop` ou usar composição
- ✅ Deve inicializar todos os managers obrigatórios
- ✅ Deve inicializar todas as telas de UI obrigatórias
- ✅ Deve usar `deltaTime` em `update()`
- ✅ Deve renderizar baseado no estado atual

---

## 5. Entry Point (index.ts)

**Status:** 🔒 PROTEGIDO  
**Propósito:** Inicialização do jogo

```typescript
import { Game } from './game'

export function initGame(canvas: HTMLCanvasElement): Game {
  const game = new Game(canvas)
  game.start()
  return game
}

// Para uso standalone
if (typeof window !== 'undefined') {
  window.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('game-canvas') as HTMLCanvasElement
    if (canvas) {
      initGame(canvas)
    }
  })
}
```

**Validação:**
- ✅ Deve exportar função `initGame()`
- ✅ Deve aceitar canvas como parâmetro
- ✅ Deve iniciar o jogo

---

## 6. Classificação de Arquivos

### 🔒 PROTEGIDOS (Não modificar)
- `core/GameLoop.ts`
- `core/TimeManager.ts`
- `core/InputManager.ts`
- `core/StateManager.ts`
- `core/SaveManager.ts`
- `core/ViewportManager.ts`
- `core/EventManager.ts`
- `index.ts`

### 🔓 MUTÁVEIS (Podem ser modificados)
- `ui/StartScreen.ts`
- `ui/HUD.ts`
- `ui/GameOverScreen.ts`
- `ui/PauseMenu.ts`
- `game.ts`
- `types.ts`
- `config/*`
- `utils/*`

### ⚙️ GERADOS (Criados pelo AI)
- `systems/*`
- `entities/*`
- Arquivos customizados específicos do jogo

---

## 7. Validação de Schema

O validador deve verificar:

1. ✅ Todos os arquivos obrigatórios existem
2. ✅ Arquivos protegidos não foram modificados
3. ✅ Estrutura de diretórios está correta
4. ✅ Imports estão corretos
5. ✅ Interfaces obrigatórias estão implementadas

---

## 8. Assinatura

```
ORDAX RUNTIME CORE FILE SCHEMA
Versão: 1.0.0
Data: 2026-01-25
Status: CANÔNICO E IMUTÁVEL
```

**Este schema define a estrutura fixa de arquivos da Ordax Engine.**
