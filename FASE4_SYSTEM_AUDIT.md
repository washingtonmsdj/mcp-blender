# 🔍 FASE 4 - CANONICAL SYSTEM BEHAVIOR AUDIT

## 🎯 Objetivo

Fazer cada System da Ordax cumprir **100% do contrato mínimo** assumido pelo runtime profile + autofill.

**Escopo FECHADO:**
- ❌ Não criar features novas
- ❌ Não mudar IA, Chat, Protocolo ou JSON
- ❌ Não refatorar arquitetura
- ❌ Não criar ECS
- ❌ Não otimizar performance

**Critério de Sucesso:**
Qualquer runtimeSpec que passe por `validateRuntimeAgainstProfile` + `autofillTopDownShooter` deve gerar um jogo onde:
- ✅ Player se move
- ✅ Player atira
- ✅ Enemy spawna
- ✅ Enemy persegue
- ✅ Colisão funciona
- ✅ Vida reduz
- ✅ Game Over dispara
- ✅ Restart funciona

---

## 📋 SISTEMAS AUDITADOS

### 1. PhysicsSystem ⚠️

**Contrato Mínimo:**
- Mover entidades baseado em velocidade (vx, vy)
- Aplicar deltaTime corretamente
- Suportar movimento top-down (sem gravidade)
- Atualizar posição (x, y) das entidades

**Violações Identificadas:**
1. ❌ **Sistema muito complexo** - Usa forças, massa, fricção (desnecessário para top-down)
2. ❌ **Não funciona com props simples** - Espera componentes registrados, mas autofill injeta props direto
3. ❌ **Não lê vx/vy das props** - Espera registro manual
4. ❌ **Não atualiza props.vx/props.vy** - Só atualiza componente interno

**Correção Necessária:**
- Simplificar para ler `props.vx`, `props.vy`, `props.speed` diretamente
- Atualizar `entity.x`, `entity.y` baseado em velocidade
- Remover complexidade de forças/massa (manter para compatibilidade mas não exigir)

---

### 2. CollisionSystem ✅

**Contrato Mínimo:**
- Detectar colisões entre entidades
- Suportar AABB (bounding box)
- Chamar callbacks quando colidir

**Status:** ✅ **FUNCIONA**

**Observações:**
- Sistema já funciona com entidades simples
- AABB detection está correto
- Callbacks funcionam

**Ação:** Nenhuma correção necessária

---

### 3. AISystem ⚠️

**Contrato Mínimo:**
- Comportamento "chase" - perseguir player
- Ler `props.ai`, `props.speed`, `props.target`
- Mover enemy em direção ao player
- Aplicar deltaTime

**Violações Identificadas:**
1. ❌ **Requer registro manual** - Não funciona com props direto
2. ❌ **Não lê props.ai** - Espera registro com setBehavior
3. ❌ **Não lê props.speed** - Usa speed do agente registrado
4. ❌ **Não lê props.target** - Assume "player" hardcoded

**Correção Necessária:**
- Ler `props.ai`, `props.speed`, `props.target` diretamente
- Funcionar sem registro prévio
- Suportar comportamento "chase" out-of-the-box

---

### 4. SpawnerSystem ❌

**Contrato Mínimo:**
- Spawnar enemies periodicamente
- Ler `props.spawner`, `props.spawnRate`, `props.maxEnemies`
- Criar novas entidades do tipo especificado
- Respeitar limite máximo

**Violações Identificadas:**
1. ❌ **SISTEMA NÃO EXISTE** - Não há SpawnerSystem implementado!
2. ❌ **Sem lógica de spawn** - Nenhum código para criar entidades

**Correção Necessária:**
- **CRIAR SpawnerSystem do zero**
- Ler props das entidades tipo "spawner"
- Spawnar enemies baseado em spawnRate
- Respeitar maxEnemies

---

### 5. CombatSystem ❌

**Contrato Mínimo:**
- Aplicar dano quando colisão acontece
- Reduzir `props.health`
- Remover entidade quando health <= 0
- Disparar eventos de morte

**Violações Identificadas:**
1. ❌ **SISTEMA NÃO EXISTE** - Não há CombatSystem implementado!
2. ❌ **Sem lógica de dano** - Colisões não causam dano
3. ❌ **Sem lógica de morte** - Entidades não morrem

**Correção Necessária:**
- **CRIAR CombatSystem do zero**
- Integrar com CollisionSystem
- Aplicar dano baseado em `props.damage`
- Remover entidades mortas

---

### 6. GameStateSystem ❌

**Contrato Mínimo:**
- Estados: START, PLAYING, GAME_OVER
- Transições: start → playing → gameover → restart
- Detectar condição de game over (player.health <= 0)
- Permitir restart

**Violações Identificadas:**
1. ❌ **SISTEMA NÃO EXISTE** - Não há GameStateSystem implementado!
2. ❌ **Sem FSM** - Não há máquina de estados
3. ❌ **Sem detecção de game over** - Jogo não termina
4. ❌ **Sem restart** - Não há como reiniciar

**Correção Necessária:**
- **CRIAR GameStateSystem do zero**
- Implementar FSM (START, PLAYING, GAME_OVER)
- Detectar player.health <= 0
- Implementar restart

---

### 7. InputSystem ⚠️

**Contrato Mínimo:**
- Capturar WASD para movimento
- Capturar SPACE para atirar
- Aplicar velocidade ao player
- Criar bullets quando atirar

**Violações Identificadas:**
1. ❌ **SISTEMA NÃO EXISTE** - Não há InputSystem implementado!
2. ❌ **Input espalhado** - Cada jogo implementa input próprio
3. ❌ **Sem padrão** - Não há contrato de input

**Correção Necessária:**
- **CRIAR InputSystem do zero**
- Capturar WASD e SPACE
- Aplicar movimento ao player
- Criar bullets

---

### 8. ScoreSystem ✅

**Contrato Mínimo:**
- Adicionar pontos
- Salvar highscore
- Resetar score

**Status:** ✅ **FUNCIONA**

**Observações:**
- Sistema já funciona
- Salva highscore em localStorage
- Tem combo/multiplier (bonus)

**Ação:** Nenhuma correção necessária

---

### 9. TimerSystem ✅

**Contrato Mínimo:**
- Criar timers
- Atualizar com deltaTime
- Chamar callbacks

**Status:** ✅ **FUNCIONA**

**Observações:**
- Sistema já funciona
- Suporta repeat
- Callbacks funcionam

**Ação:** Nenhuma correção necessária

---

### 10. UISystem ⚠️

**Contrato Mínimo:**
- Renderizar HUD (health, score, timer)
- Renderizar StartScreen
- Renderizar GameOverScreen
- Ler configuração de `props.ui`

**Violações Identificadas:**
1. ❌ **Não lê props.ui** - Não usa metadata de UI do autofill
2. ❌ **Sem StartScreen** - Não renderiza tela inicial
3. ❌ **Sem GameOverScreen** - Não renderiza tela final
4. ❌ **HUD manual** - Precisa adicionar elementos manualmente

**Correção Necessária:**
- Ler `props.ui` das entidades metadata
- Renderizar StartScreen automaticamente
- Renderizar GameOverScreen automaticamente
- Renderizar HUD baseado em config

---

## 📊 RESUMO DE VIOLAÇÕES

| Sistema | Status | Violações | Ação |
|---------|--------|-----------|------|
| PhysicsSystem | ⚠️ Parcial | 4 | Simplificar |
| CollisionSystem | ✅ OK | 0 | Nenhuma |
| AISystem | ⚠️ Parcial | 4 | Simplificar |
| SpawnerSystem | ❌ Falta | - | **CRIAR** |
| CombatSystem | ❌ Falta | - | **CRIAR** |
| GameStateSystem | ❌ Falta | - | **CRIAR** |
| InputSystem | ❌ Falta | - | **CRIAR** |
| ScoreSystem | ✅ OK | 0 | Nenhuma |
| TimerSystem | ✅ OK | 0 | Nenhuma |
| UISystem | ⚠️ Parcial | 4 | Melhorar |

**Total:**
- ✅ OK: 3 sistemas
- ⚠️ Parcial: 3 sistemas
- ❌ Falta: 4 sistemas

---

## 🔧 PLANO DE CORREÇÃO

### Prioridade 1: CRIAR sistemas faltantes
1. **SpawnerSystem** - Crítico para gameplay
2. **CombatSystem** - Crítico para dano/morte
3. **GameStateSystem** - Crítico para game over/restart
4. **InputSystem** - Crítico para controle

### Prioridade 2: SIMPLIFICAR sistemas existentes
1. **PhysicsSystem** - Ler props direto
2. **AISystem** - Ler props direto
3. **UISystem** - Ler metadata de UI

### Prioridade 3: INTEGRAR tudo
1. Fazer sistemas trabalharem juntos
2. Testar fluxo completo
3. Validar contra contrato mínimo

---

## 🎯 CRITÉRIO DE SUCESSO

Após correções, este código deve funcionar:

```typescript
import { autofillTopDownShooter } from '@/lib/ordax/runtime-autofill';

const minimalRuntime = {
  gameType: 'topdown',
  title: 'Test',
  description: 'Test',
  systems: [],
  scene: {
    gravity: { x: 0, y: 0 },
    entities: []
  }
};

// Autofill
const { spec } = autofillTopDownShooter(minimalRuntime);

// Inicializar sistemas
const physics = new PhysicsSystem();
const collision = new CollisionSystem();
const ai = new AISystem();
const spawner = new SpawnerSystem();
const combat = new CombatSystem();
const gameState = new GameStateSystem();
const input = new InputSystem();
const score = new ScoreSystem();
const timer = new TimerSystem();
const ui = new UISystem();

// Game loop
function update(dt: number) {
  if (gameState.current !== 'PLAYING') return;
  
  input.update(dt, spec.scene.entities);
  physics.update(dt, spec.scene.entities);
  ai.update(dt, spec.scene.entities);
  spawner.update(dt, spec.scene.entities);
  collision.update(spec.scene.entities);
  combat.update(dt, spec.scene.entities);
  gameState.update(dt, spec.scene.entities);
  score.update(dt);
  timer.update(dt);
}

function render(ctx: CanvasRenderingContext2D) {
  ui.render(ctx, gameState.current, spec.scene.entities, score, timer);
}
```

**Resultado esperado:**
- ✅ Player se move com WASD
- ✅ Player atira com SPACE
- ✅ Enemies spawnam periodicamente
- ✅ Enemies perseguem player
- ✅ Colisões detectadas
- ✅ Dano aplicado
- ✅ Entidades morrem
- ✅ Game over quando player morre
- ✅ Restart funciona

---

**Status:** 📋 **AUDITORIA COMPLETA**  
**Próximo:** Implementar correções
