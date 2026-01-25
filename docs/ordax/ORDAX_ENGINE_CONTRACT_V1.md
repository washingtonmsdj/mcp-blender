# Ordax Engine Contract V1

## Contrato Constitucional da Engine Ordax

**Data de Vigência:** 25 de Janeiro de 2026  
**Versão:** 1.0.0  
**Status:** ATIVO E OBRIGATÓRIO

---

## 1. Declaração de Propósito

A Ordax **não é um gerador de protótipos**. É uma engine de jogos com contrato constitucional rígido.

**Nenhum jogo pode ser considerado "válido" ou "pronto" se não cumprir os 7 pilares operacionais mínimos de um produto jogável.**

---

## 2. Os 7 Pilares Operacionais Obrigatórios

Todo jogo válido na Ordax **DEVE** implementar:

### Pilar 1: Gerenciamento de Tempo (Time Management)
- **Obrigatório:** Uso de `deltaTime` em todas as atualizações de movimento/física
- **Proibido:** Usar valores fixos ou frame-dependent para movimento
- **Validação:** Todo `update()` deve receber e usar `deltaTime`

### Pilar 2: Máquina de Estados (FSM - Finite State Machine)
- **Obrigatório:** Sistema de estados do jogo (START, PLAYING, PAUSED, GAME_OVER)
- **Obrigatório:** Transições explícitas entre estados
- **Validação:** Deve existir `GameState` enum e `currentState` gerenciado

### Pilar 3: Interface de Usuário Completa (UI System)
- **Obrigatório:** StartScreen (tela inicial com botão "Start")
- **Obrigatório:** HUD (exibição de score/vida durante gameplay)
- **Obrigatório:** GameOverScreen (tela de fim com opção de restart)
- **Validação:** Todas as 3 telas devem existir e ser renderizadas condicionalmente

### Pilar 4: Sistema de Input (Input Manager)
- **Obrigatório:** Gerenciamento centralizado de input (teclado/mouse/touch)
- **Obrigatório:** Mapeamento de teclas/ações
- **Obrigatório:** Suporte a múltiplos dispositivos
- **Validação:** Deve existir `InputManager` ou equivalente

### Pilar 5: Sistema de Persistência (Save Manager)
- **Obrigatório:** Salvamento de highScore no localStorage
- **Obrigatório:** Carregamento de dados salvos ao iniciar
- **Obrigatório:** Exibição de highScore na UI
- **Validação:** Deve existir `SaveManager` ou funções de save/load

### Pilar 6: Gerenciamento de Viewport (Viewport Manager)
- **Obrigatório:** Handler de resize do canvas
- **Obrigatório:** Adaptação a diferentes resoluções
- **Obrigatório:** Manutenção de aspect ratio ou scaling adequado
- **Validação:** Deve existir listener de `resize` e lógica de adaptação

### Pilar 7: Loop de Jogo Estruturado (Game Loop)
- **Obrigatório:** Separação clara entre `update()` e `render()`
- **Obrigatório:** RequestAnimationFrame ou equivalente
- **Obrigatório:** Cálculo de deltaTime
- **Validação:** Estrutura de loop deve seguir padrão da engine

---

## 3. Regras Explícitas - O Que É PROIBIDO

### 🚫 Proibições Absolutas

1. **Movimento sem deltaTime**
   - ❌ `player.x += 5`
   - ✅ `player.x += speed * deltaTime`

2. **Jogo sem FSM**
   - ❌ Lógica de jogo sem estados
   - ✅ Estados explícitos (START, PLAYING, PAUSED, GAME_OVER)

3. **UI Incompleta**
   - ❌ Apenas gameplay sem telas de início/fim
   - ✅ StartScreen + HUD + GameOverScreen

4. **Input Desorganizado**
   - ❌ Event listeners espalhados pelo código
   - ✅ InputManager centralizado

5. **Sem Persistência**
   - ❌ Score que desaparece ao recarregar
   - ✅ HighScore salvo no localStorage

6. **Canvas Fixo**
   - ❌ Tamanho hardcoded sem adaptação
   - ✅ Resize handler e viewport responsivo

7. **Loop Caótico**
   - ❌ setInterval ou setTimeout para game loop
   - ✅ requestAnimationFrame com deltaTime

---

## 4. Estrutura Mínima Obrigatória

Todo jogo válido deve conter:

```typescript
// 1. Game States (FSM)
enum GameState {
  START = 'START',
  PLAYING = 'PLAYING',
  PAUSED = 'PAUSED',
  GAME_OVER = 'GAME_OVER'
}

// 2. Input Manager
class InputManager {
  keys: Map<string, boolean>
  mouse: { x: number, y: number, pressed: boolean }
  // ... métodos de gerenciamento
}

// 3. Save Manager
class SaveManager {
  saveHighScore(score: number): void
  loadHighScore(): number
  // ... métodos de persistência
}

// 4. UI Components
function renderStartScreen(ctx: CanvasRenderingContext2D): void
function renderHUD(ctx: CanvasRenderingContext2D, score: number, lives: number): void
function renderGameOverScreen(ctx: CanvasRenderingContext2D, score: number, highScore: number): void

// 5. Game Loop
function gameLoop(timestamp: number): void {
  const deltaTime = calculateDeltaTime(timestamp)
  
  update(deltaTime) // Atualiza lógica
  render()          // Renderiza frame
  
  requestAnimationFrame(gameLoop)
}

// 6. Viewport Manager
function handleResize(): void {
  canvas.width = window.innerWidth
  canvas.height = window.innerHeight
  // ... lógica de scaling
}
window.addEventListener('resize', handleResize)
```

---

## 5. Níveis de Violação Constitucional

### 🔴 CRÍTICO (Jogo Inválido - Bloqueio Total)
- Ausência de deltaTime
- Ausência de FSM
- Ausência de StartScreen ou GameOverScreen
- Ausência de Game Loop estruturado

### 🟡 GRAVE (Jogo Incompleto - Aviso Forte)
- Ausência de HUD
- Ausência de InputManager
- Ausência de SaveManager
- Ausência de Viewport Manager

### 🟢 MENOR (Jogo Funcional - Sugestão)
- Falta de comentários
- Falta de otimizações
- Falta de features avançadas

---

## 6. Processo de Validação

### Quando Validar
1. **NEW_GAME:** Após geração do código pelo AI
2. **CODE_MUTATION:** Após aplicar patches/mudanças
3. **RUNTIME_LOAD:** Antes de executar o jogo

### Como Validar
```typescript
const validation = validateConstitutionalCompliance(runtimeSpec)

if (!validation.isValid) {
  throw new ConstitutionalError(validation.violations)
}
```

### Resposta a Violações
- **Bloquear execução do jogo**
- **Exibir violações no chat**
- **Forçar AI a corrigir antes de prosseguir**
- **Não permitir resposta "jogo pronto" se houver violações**

---

## 7. Contrato com o AI

O AI da Ordax **NÃO PODE:**
- Sugerir "adicionar depois"
- Gerar jogos incompletos
- Ignorar pilares obrigatórios
- Responder "jogo pronto" sem validação

O AI da Ordax **DEVE:**
- Gerar todos os 7 pilares desde o início
- Validar constitucionalmente antes de responder
- Corrigir violações automaticamente
- Falhar explicitamente se não conseguir cumprir o contrato

---

## 8. Exceções e Casos Especiais

### Não Há Exceções
Este contrato **não admite exceções**. Todo jogo, independente de:
- Complexidade
- Gênero
- Escopo
- Propósito

**DEVE** cumprir os 7 pilares operacionais.

---

## 9. Versionamento do Contrato

- **V1.0.0:** Contrato inicial com 7 pilares obrigatórios
- **Futuro:** Novos pilares podem ser adicionados, mas nunca removidos
- **Compatibilidade:** Jogos antigos devem ser migrados para nova versão do contrato

---

## 10. Assinatura Digital

```
ORDAX ENGINE CONTRACT V1
Estabelecido em: 2026-01-25
Autoridade: Ordax Core Team
Status: CONSTITUCIONAL E IMUTÁVEL
```

**Este documento é a fonte da verdade para validação de jogos na Ordax Engine.**
