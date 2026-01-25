# Ordax Game Validator

## Sistema de Validação Constitucional de Jogos

**Versão:** 1.0.0  
**Data:** 25 de Janeiro de 2026  
**Status:** CANÔNICO

---

## 1. Propósito

O Ordax Game Validator é o guardião do Contrato Constitucional. Nenhum jogo pode ser considerado válido sem passar por esta validação.

**Regra de Ouro:** Se o validador falhar, o jogo não pode ser executado.

---

## 2. Níveis de Violação

### 🔴 CRÍTICO (BLOQUEANTE)
Jogo **INVÁLIDO** - Execução bloqueada

### 🟡 GRAVE (AVISO FORTE)
Jogo **INCOMPLETO** - Execução permitida com avisos

### 🟢 MENOR (SUGESTÃO)
Jogo **FUNCIONAL** - Sugestões de melhoria

---

## 3. Regras de Validação

### 3.1. Pilar 1: Gerenciamento de Tempo

#### 🔴 CRÍTICO: Uso de deltaTime
```typescript
{
  id: 'TIME_001',
  level: 'CRITICAL',
  rule: 'deltaTime must be used in all movement/physics updates',
  check: (code) => {
    // Verificar se update() recebe deltaTime
    const hasUpdateWithDelta = /update\s*\(\s*deltaTime\s*:\s*number\s*\)/.test(code)
    
    // Verificar se deltaTime é usado em movimento
    const usesDeltaInMovement = /[+\-*\/]=?\s*.*\s*\*\s*deltaTime/.test(code)
    
    return hasUpdateWithDelta && usesDeltaInMovement
  },
  message: 'Game must use deltaTime for frame-independent movement',
  fix: 'Add deltaTime parameter to update() and multiply all movement by deltaTime'
}
```

#### 🟡 GRAVE: TimeManager presente
```typescript
{
  id: 'TIME_002',
  level: 'SEVERE',
  rule: 'TimeManager must exist',
  check: (spec) => spec.hasTimeManager,
  message: 'TimeManager is required for proper time management',
  fix: 'Add TimeManager to core systems'
}
```

---

### 3.2. Pilar 2: Máquina de Estados (FSM)

#### 🔴 CRÍTICO: GameState enum existe
```typescript
{
  id: 'FSM_001',
  level: 'CRITICAL',
  rule: 'GameState enum must exist with minimum 4 states',
  check: (code) => {
    const hasEnum = /enum\s+GameState\s*{/.test(code)
    const hasStart = /START\s*=/.test(code)
    const hasPlaying = /PLAYING\s*=/.test(code)
    const hasPaused = /PAUSED\s*=/.test(code)
    const hasGameOver = /GAME_OVER\s*=/.test(code)
    
    return hasEnum && hasStart && hasPlaying && hasPaused && hasGameOver
  },
  message: 'GameState enum must exist with START, PLAYING, PAUSED, GAME_OVER',
  fix: 'Add GameState enum with all required states'
}
```

#### 🔴 CRÍTICO: StateManager presente
```typescript
{
  id: 'FSM_002',
  level: 'CRITICAL',
  rule: 'StateManager must exist',
  check: (spec) => spec.hasStateManager,
  message: 'StateManager is required for game state management',
  fix: 'Add StateManager to core systems'
}
```

#### 🟡 GRAVE: Transições de estado
```typescript
{
  id: 'FSM_003',
  level: 'SEVERE',
  rule: 'State transitions must be explicit',
  check: (code) => /transitionTo\s*\(/.test(code) || /setState\s*\(/.test(code),
  message: 'State transitions must be explicit and managed',
  fix: 'Use transitionTo() or setState() for state changes'
}
```

---

### 3.3. Pilar 3: Interface de Usuário

#### 🔴 CRÍTICO: StartScreen existe
```typescript
{
  id: 'UI_001',
  level: 'CRITICAL',
  rule: 'StartScreen must exist',
  check: (spec) => spec.hasStartScreen,
  message: 'StartScreen is required for game initialization',
  fix: 'Add StartScreen component with render() and handleClick()'
}
```

#### 🔴 CRÍTICO: GameOverScreen existe
```typescript
{
  id: 'UI_002',
  level: 'CRITICAL',
  rule: 'GameOverScreen must exist',
  check: (spec) => spec.hasGameOverScreen,
  message: 'GameOverScreen is required for game completion',
  fix: 'Add GameOverScreen component with score display and restart option'
}
```

#### 🟡 GRAVE: HUD existe
```typescript
{
  id: 'UI_003',
  level: 'SEVERE',
  rule: 'HUD must exist',
  check: (spec) => spec.hasHUD,
  message: 'HUD is required for displaying game information',
  fix: 'Add HUD component to display score, lives, or other game info'
}
```

#### 🟡 GRAVE: Renderização condicional por estado
```typescript
{
  id: 'UI_004',
  level: 'SEVERE',
  rule: 'UI must render based on game state',
  check: (code) => {
    const hasStartRender = /state\s*===?\s*GameState\.START/.test(code)
    const hasPlayingRender = /state\s*===?\s*GameState\.PLAYING/.test(code)
    const hasGameOverRender = /state\s*===?\s*GameState\.GAME_OVER/.test(code)
    
    return hasStartRender && hasPlayingRender && hasGameOverRender
  },
  message: 'UI must render different screens based on game state',
  fix: 'Add conditional rendering for each game state'
}
```

---

### 3.4. Pilar 4: Sistema de Input

#### 🔴 CRÍTICO: InputManager existe
```typescript
{
  id: 'INPUT_001',
  level: 'CRITICAL',
  rule: 'InputManager must exist',
  check: (spec) => spec.hasInputManager,
  message: 'InputManager is required for centralized input handling',
  fix: 'Add InputManager to core systems'
}
```

#### 🟡 GRAVE: Suporte a múltiplos dispositivos
```typescript
{
  id: 'INPUT_002',
  level: 'SEVERE',
  rule: 'InputManager must support keyboard and mouse/touch',
  check: (code) => {
    const hasKeyboard = /keydown|keyup/.test(code)
    const hasMouseOrTouch = /mousedown|mouseup|touchstart|touchend/.test(code)
    
    return hasKeyboard && hasMouseOrTouch
  },
  message: 'InputManager must support at least keyboard and mouse/touch',
  fix: 'Add event listeners for keyboard and mouse/touch'
}
```

#### 🟢 MENOR: Input mapeado
```typescript
{
  id: 'INPUT_003',
  level: 'MINOR',
  rule: 'Input should be mapped to actions',
  check: (code) => /inputMap|keyMap|actionMap/.test(code),
  message: 'Consider mapping input to actions for better maintainability',
  fix: 'Create input mapping object for cleaner code'
}
```

---

### 3.5. Pilar 5: Sistema de Persistência

#### 🔴 CRÍTICO: SaveManager existe
```typescript
{
  id: 'SAVE_001',
  level: 'CRITICAL',
  rule: 'SaveManager must exist',
  check: (spec) => spec.hasSaveManager,
  message: 'SaveManager is required for data persistence',
  fix: 'Add SaveManager to core systems'
}
```

#### 🔴 CRÍTICO: HighScore salvo
```typescript
{
  id: 'SAVE_002',
  level: 'CRITICAL',
  rule: 'HighScore must be saved to localStorage',
  check: (code) => {
    const hasSave = /localStorage\.setItem/.test(code) || /saveHighScore/.test(code)
    const hasLoad = /localStorage\.getItem/.test(code) || /loadHighScore/.test(code)
    
    return hasSave && hasLoad
  },
  message: 'HighScore must be persisted using localStorage',
  fix: 'Add saveHighScore() and loadHighScore() methods'
}
```

#### 🟡 GRAVE: HighScore exibido
```typescript
{
  id: 'SAVE_003',
  level: 'SEVERE',
  rule: 'HighScore must be displayed in GameOverScreen',
  check: (code) => /highScore/.test(code) && /GameOverScreen/.test(code),
  message: 'HighScore should be displayed in GameOverScreen',
  fix: 'Display highScore in GameOverScreen render()'
}
```

---

### 3.6. Pilar 6: Gerenciamento de Viewport

#### 🔴 CRÍTICO: Resize handler existe
```typescript
{
  id: 'VIEWPORT_001',
  level: 'CRITICAL',
  rule: 'Resize handler must exist',
  check: (code) => /addEventListener\s*\(\s*['"]resize['"]/.test(code) || /handleResize/.test(code),
  message: 'Resize handler is required for responsive canvas',
  fix: 'Add window resize event listener'
}
```

#### 🟡 GRAVE: ViewportManager existe
```typescript
{
  id: 'VIEWPORT_002',
  level: 'SEVERE',
  rule: 'ViewportManager should exist',
  check: (spec) => spec.hasViewportManager,
  message: 'ViewportManager is recommended for viewport management',
  fix: 'Add ViewportManager to core systems'
}
```

#### 🟢 MENOR: Aspect ratio mantido
```typescript
{
  id: 'VIEWPORT_003',
  level: 'MINOR',
  rule: 'Aspect ratio should be maintained',
  check: (code) => /aspectRatio|Math\.min\(scaleX,\s*scaleY\)/.test(code),
  message: 'Consider maintaining aspect ratio for better visuals',
  fix: 'Calculate scale based on aspect ratio'
}
```

---

### 3.7. Pilar 7: Loop de Jogo

#### 🔴 CRÍTICO: requestAnimationFrame usado
```typescript
{
  id: 'LOOP_001',
  level: 'CRITICAL',
  rule: 'Must use requestAnimationFrame',
  check: (code) => /requestAnimationFrame/.test(code),
  message: 'Game loop must use requestAnimationFrame',
  fix: 'Replace setInterval/setTimeout with requestAnimationFrame'
}
```

#### 🔴 CRÍTICO: Separação update/render
```typescript
{
  id: 'LOOP_002',
  level: 'CRITICAL',
  rule: 'Must separate update() and render()',
  check: (code) => {
    const hasUpdate = /function\s+update\s*\(|update\s*\(.*\)\s*{/.test(code)
    const hasRender = /function\s+render\s*\(|render\s*\(.*\)\s*{/.test(code)
    
    return hasUpdate && hasRender
  },
  message: 'Game loop must separate update() and render() logic',
  fix: 'Create separate update() and render() functions'
}
```

#### 🟡 GRAVE: GameLoop estruturado
```typescript
{
  id: 'LOOP_003',
  level: 'SEVERE',
  rule: 'GameLoop should follow standard structure',
  check: (code) => {
    const hasLoop = /function\s+gameLoop|class\s+GameLoop/.test(code)
    const hasDeltaCalc = /deltaTime\s*=/.test(code)
    
    return hasLoop && hasDeltaCalc
  },
  message: 'GameLoop should follow standard structure with deltaTime calculation',
  fix: 'Structure game loop with proper deltaTime calculation'
}
```

---

## 4. Erros Constitucionais Comuns

### Erro 1: Movimento sem deltaTime
```typescript
// ❌ ERRADO
player.x += 5

// ✅ CORRETO
player.x += speed * deltaTime
```

### Erro 2: Sem FSM
```typescript
// ❌ ERRADO
let gameStarted = false
let gameOver = false

// ✅ CORRETO
enum GameState { START, PLAYING, GAME_OVER }
let currentState = GameState.START
```

### Erro 3: UI incompleta
```typescript
// ❌ ERRADO
function render() {
  // Apenas gameplay
  renderPlayer()
  renderEnemies()
}

// ✅ CORRETO
function render() {
  if (state === GameState.START) {
    renderStartScreen()
  } else if (state === GameState.PLAYING) {
    renderGameplay()
    renderHUD()
  } else if (state === GameState.GAME_OVER) {
    renderGameOverScreen()
  }
}
```

### Erro 4: Input desorganizado
```typescript
// ❌ ERRADO
window.addEventListener('keydown', (e) => {
  if (e.key === 'ArrowLeft') player.x -= 5
})

// ✅ CORRETO
class InputManager {
  keys = new Map()
  init() {
    window.addEventListener('keydown', (e) => this.keys.set(e.key, true))
  }
  isKeyPressed(key) { return this.keys.get(key) || false }
}
```

### Erro 5: Sem persistência
```typescript
// ❌ ERRADO
let highScore = 0 // Perdido ao recarregar

// ✅ CORRETO
class SaveManager {
  saveHighScore(score) {
    localStorage.setItem('highScore', score.toString())
  }
  loadHighScore() {
    return parseInt(localStorage.getItem('highScore') || '0')
  }
}
```

### Erro 6: Canvas fixo
```typescript
// ❌ ERRADO
canvas.width = 800
canvas.height = 600

// ✅ CORRETO
function handleResize() {
  canvas.width = window.innerWidth
  canvas.height = window.innerHeight
}
window.addEventListener('resize', handleResize)
```

### Erro 7: Loop caótico
```typescript
// ❌ ERRADO
setInterval(() => {
  update()
  render()
}, 16)

// ✅ CORRETO
function gameLoop(timestamp) {
  const deltaTime = calculateDeltaTime(timestamp)
  update(deltaTime)
  render()
  requestAnimationFrame(gameLoop)
}
```

---

## 5. Formato de Resposta do Validador

```typescript
interface ValidationResult {
  isValid: boolean
  violations: ConstitutionalViolation[]
  summary: {
    critical: number
    severe: number
    minor: number
  }
}

interface ConstitutionalViolation {
  id: string                    // Ex: 'TIME_001'
  level: 'CRITICAL' | 'SEVERE' | 'MINOR'
  pilar: string                 // Ex: 'Time Management'
  rule: string                  // Descrição da regra
  message: string               // Mensagem de erro
  fix: string                   // Como corrigir
  location?: {                  // Onde ocorreu (opcional)
    file: string
    line: number
  }
}
```

### Exemplo de Resposta
```json
{
  "isValid": false,
  "violations": [
    {
      "id": "TIME_001",
      "level": "CRITICAL",
      "pilar": "Time Management",
      "rule": "deltaTime must be used in all movement/physics updates",
      "message": "Game must use deltaTime for frame-independent movement",
      "fix": "Add deltaTime parameter to update() and multiply all movement by deltaTime",
      "location": {
        "file": "game.ts",
        "line": 45
      }
    },
    {
      "id": "UI_001",
      "level": "CRITICAL",
      "pilar": "UI System",
      "rule": "StartScreen must exist",
      "message": "StartScreen is required for game initialization",
      "fix": "Add StartScreen component with render() and handleClick()"
    }
  ],
  "summary": {
    "critical": 2,
    "severe": 0,
    "minor": 0
  }
}
```

---

## 6. Comportamento do Sistema

### Quando Validar
1. **NEW_GAME:** Após AI gerar código
2. **CODE_MUTATION:** Após aplicar patches
3. **RUNTIME_LOAD:** Antes de executar jogo

### Resposta a Violações

#### 🔴 CRÍTICO (1+ violação)
- ❌ **BLOQUEAR** execução do jogo
- 🚫 **PROIBIR** resposta "jogo pronto" do AI
- 📋 **EXIBIR** violações no chat
- 🔧 **FORÇAR** AI a corrigir

#### 🟡 GRAVE (1+ violação, 0 críticas)
- ⚠️ **PERMITIR** execução com avisos
- 📋 **EXIBIR** avisos no chat
- 💡 **SUGERIR** correções

#### 🟢 MENOR (apenas violações menores)
- ✅ **PERMITIR** execução
- 💡 **SUGERIR** melhorias (opcional)

---

## 7. Integração com AI

### Prompt do AI Deve Incluir
```
CONSTITUTIONAL VALIDATION FAILED

The game violates the Ordax Engine Contract V1.
You MUST fix all CRITICAL violations before proceeding.

Violations:
1. [TIME_001] CRITICAL: Game must use deltaTime for frame-independent movement
   Fix: Add deltaTime parameter to update() and multiply all movement by deltaTime

2. [UI_001] CRITICAL: StartScreen is required for game initialization
   Fix: Add StartScreen component with render() and handleClick()

You cannot respond "game ready" until all violations are fixed.
Generate corrected code that passes constitutional validation.
```

### AI Não Pode
- ❌ Ignorar violações
- ❌ Sugerir "adicionar depois"
- ❌ Gerar jogos incompletos
- ❌ Responder "jogo pronto" com violações

### AI Deve
- ✅ Corrigir todas as violações críticas
- ✅ Gerar código completo desde o início
- ✅ Validar antes de responder
- ✅ Falhar explicitamente se não conseguir

---

## 8. Mensagens de Erro Padronizadas

### Para o Usuário
```
🚫 CONSTITUTIONAL ERROR

This game violates the Ordax Engine Contract and cannot be executed.

Critical Issues (2):
• Game must use deltaTime for frame-independent movement
• StartScreen is required for game initialization

The AI is working to fix these issues...
```

### Para o AI
```
CONSTITUTIONAL_VALIDATION_FAILED

violations: [
  { id: 'TIME_001', level: 'CRITICAL', ... },
  { id: 'UI_001', level: 'CRITICAL', ... }
]

REQUIRED_ACTION: Fix all CRITICAL violations and regenerate code.
PROHIBITED: Responding "game ready" or suggesting "add later".
```

---

## 9. Checklist de Validação Rápida

```
✅ Usa deltaTime em movimento?
✅ Tem GameState enum com 4 estados?
✅ Tem StartScreen?
✅ Tem HUD?
✅ Tem GameOverScreen?
✅ Tem InputManager?
✅ Tem SaveManager com highScore?
✅ Tem resize handler?
✅ Usa requestAnimationFrame?
✅ Separa update() e render()?
```

Se **TODAS** as respostas forem SIM → Jogo VÁLIDO ✅  
Se **QUALQUER** resposta for NÃO → Jogo INVÁLIDO ❌

---

## 10. Assinatura

```
ORDAX GAME VALIDATOR
Versão: 1.0.0
Data: 2026-01-25
Status: ATIVO E OBRIGATÓRIO
```

**Este validador é o guardião do Contrato Constitucional da Ordax Engine.**
