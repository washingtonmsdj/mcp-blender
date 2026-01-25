# ✅ FASE 2 - RUNTIME PROFILE IMPLEMENTADO

## 🎯 Objetivo
Tornar o runtime da Ordax capaz de gerar um único gênero funcional de verdade: **Top-down shooter survival**.

## 📦 Arquivos Criados/Atualizados

### 1. Perfil Canônico: `src/lib/ordax/runtime-profiles/topdown-shooter.ts`

**Conteúdo:**
- ✅ `RuntimeProfile` interface completa
- ✅ `TOPDOWN_SHOOTER_PROFILE` com especificação canônica:

#### Sistemas Obrigatórios (7)
```typescript
requiredSystems: [
  "PhysicsSystem",      // Movimento
  "CollisionSystem",    // Colisões
  "AISystem",           // Comportamento de inimigos
  "SpawnerSystem",      // Geração de ondas
  "ScoreSystem",        // Pontuação
  "TimerSystem",        // Tempo de sobrevivência
  "UISystem",           // Interface
]
```

#### Entidades Obrigatórias (4)
1. **player** - Componentes críticos:
   - Transform (posição/rotação)
   - Velocity (movimento)
   - Health (vida)
   - Weapon (atirar)
   - Collider (colisão)
   - Props: `health`, `speed`, `fireRate`

2. **enemy** - Componentes críticos:
   - Transform
   - Velocity
   - Health
   - AI (perseguir jogador)
   - Collider
   - Props: `health`, `speed`, `damage`

3. **bullet** - Componentes críticos:
   - Transform
   - Velocity
   - Collider
   - Lifetime (opcional)
   - Props: `speed`, `damage`

4. **spawner** - Componentes críticos:
   - Transform
   - Spawner (lógica de spawn)
   - Props: `spawnRate`, `maxEnemies`

#### UI Obrigatória
- **StartScreen**: title, startButton, instructions
- **HUD**: health, score, timer, wave
- **GameOverScreen**: finalScore, survivalTime, restartButton, highScore

#### Controles Obrigatórios
- **Movimento**: W, A, S, D (8 direções)
- **Ação**: SPACE ou MOUSE_LEFT (atirar)
- **Pause**: ESC ou P (opcional)

#### Sinais Obrigatórios
- `player_health` (CRÍTICO)
- `score` (CRÍTICO)
- `timer` (CRÍTICO)
- `wave` (opcional)

#### Lifecycle
- **Start**: Jogador clica em 'Start'
- **Lose**: `player.health <= 0`
- **Win**: undefined (survival não tem vitória)
- **Restart**: Jogador clica em 'Restart'

---

### 2. Validador: `src/lib/ordax/runtime-profiles/validator.ts`

**Função Principal:**
```typescript
validateRuntimeAgainstProfile(
  runtimeSpec: OrdaxSpec,
  profile: RuntimeProfile
): ProfileValidationResult
```

**Validações Implementadas:**

#### ✅ 1. Sistemas Faltantes
Detecta sistemas obrigatórios ausentes → Violação **CRITICAL**

#### ✅ 2. Entidades Faltantes
Detecta entidades obrigatórias ausentes → Violação **CRITICAL**

#### ✅ 3. Componentes Faltantes
Detecta componentes críticos ausentes em entidades → Violação **CRITICAL**

Heurísticas implementadas:
- `Transform`: verifica `x`, `y`, `rotation`
- `Velocity`: verifica `vx`, `vy`, `speed`
- `Health`: verifica `health`, `hp`
- `Weapon`: verifica `weapon`, `fireRate`, `damage`
- `Collider`: verifica `w`, `h`, `radius`, `collider`
- `AI`: verifica `ai`, `behavior`, `target`
- `Spawner`: verifica `spawner`, `spawnRate`
- `Lifetime`: verifica `lifetime`, `ttl`

#### ✅ 4. Props Obrigatórias
Detecta propriedades obrigatórias ausentes → Violação **SEVERE**

#### ✅ 5. UI Faltante
Detecta telas obrigatórias ausentes (StartScreen, HUD, GameOverScreen) → Violação **CRITICAL**

#### ✅ 6. Controles Faltantes
Detecta controles obrigatórios ausentes (movimento, ação) → Violação **CRITICAL**

#### ✅ 7. Sinais Faltantes
Detecta sinais obrigatórios ausentes → Violação **SEVERE**

**Resultado:**
```typescript
interface ProfileValidationResult {
  isValid: boolean;              // true se 0 violações CRITICAL
  genre: string;                 // "topdown-shooter-survival"
  violations: ProfileViolation[]; // Lista de violações
  summary: {
    critical: number;
    severe: number;
    minor: number;
  };
  missingElements: {
    systems: string[];
    entities: string[];
    components: Record<string, string[]>;
    uiElements: string[];
    controls: string[];
    signals: string[];
  };
}
```

**Helpers de Formatação:**
- `formatProfileViolations()` - Formata violações para console
- `generateMissingElementsReport()` - Gera relatório de elementos faltantes

---

### 3. Exemplos: `src/lib/ordax/runtime-profiles/example-validation.ts`

**Exemplos Implementados:**

#### Exemplo 1: Runtime Incompleto
Runtime com apenas 1 sistema e 1 entidade sem componentes → Muitas violações CRITICAL

#### Exemplo 2: Runtime Completo
Runtime com todos os sistemas, entidades e componentes → Válido ✅

#### Exemplo 3: Pipeline de Compilação
```typescript
function validateGameBeforeCompile(runtimeSpec: OrdaxSpec): boolean {
  const result = validateRuntimeAgainstProfile(runtimeSpec, TOPDOWN_SHOOTER_PROFILE);
  
  if (!result.isValid) {
    console.error("❌ COMPILATION BLOCKED");
    return false;
  }
  
  return true;
}
```

#### Exemplo 4: Feedback para IA
```typescript
function generateAIFeedback(runtimeSpec: OrdaxSpec): string {
  // Gera feedback amigável para IA sobre o que falta
}
```

---

### 4. Índice: `src/lib/ordax/runtime-profiles/index.ts`

Exporta tudo de forma organizada:
```typescript
export {
  TOPDOWN_SHOOTER_PROFILE,
  validateRuntimeAgainstProfile,
  formatProfileViolations,
  generateMissingElementsReport,
  // ... tipos
} from './runtime-profiles';
```

---

### 5. Testes: `src/lib/ordax/runtime-profiles/validator.test.ts`

**Testes Implementados:**
- ✅ Detecta sistemas faltantes
- ✅ Detecta entidades faltantes
- ✅ Detecta componentes faltantes em entidades
- ✅ Valida runtime completo como válido
- ✅ Detecta props obrigatórias faltantes

---

## 🎮 Como Usar

### Validar um Runtime
```typescript
import { TOPDOWN_SHOOTER_PROFILE, validateRuntimeAgainstProfile } from '@/lib/ordax/runtime-profiles';

const result = validateRuntimeAgainstProfile(myRuntimeSpec, TOPDOWN_SHOOTER_PROFILE);

if (!result.isValid) {
  console.error(formatProfileViolations(result));
  console.error(generateMissingElementsReport(result));
}
```

### Integrar no Protocolo de Compilação
```typescript
// Antes de compilar, validar contra perfil
const validationResult = validateRuntimeAgainstProfile(runtimeSpec, TOPDOWN_SHOOTER_PROFILE);

if (!validationResult.isValid) {
  return {
    phase: "validation",
    status: "error",
    violations: validationResult.violations,
    message: "Runtime não cumpre perfil do gênero"
  };
}

// Prosseguir com compilação...
```

### Feedback para IA
```typescript
const feedback = generateAIFeedback(runtimeSpec);
// "⚠️ Seu jogo ainda não está completo. Aqui está o que falta:
//  **Sistemas faltantes:**
//  - CollisionSystem
//  - AISystem
//  ..."
```

---

## 📊 Níveis de Violação

### CRITICAL 🔴
- **Sistemas faltantes**: Jogo não funciona sem eles
- **Entidades faltantes**: Gênero não existe sem elas
- **Componentes críticos faltantes**: Entidade não funciona
- **UI faltante**: Jogo não é jogável
- **Controles faltantes**: Jogador não consegue jogar

**Ação:** Bloquear compilação até corrigir

### SEVERE 🟠
- **Props obrigatórias faltantes**: Entidade não funciona corretamente
- **Sinais obrigatórios faltantes**: Feedback ao jogador comprometido

**Ação:** Avisar fortemente, mas permitir compilação

### MINOR 🟡
- **Componentes opcionais faltantes**: Funcionalidade extra
- **Sinais opcionais faltantes**: Nice-to-have

**Ação:** Avisar levemente

---

## ✅ Status

### Tarefa 1: Perfil Canônico ✅
- ✅ `requiredSystems` (7 sistemas)
- ✅ `requiredEntities` (4 entidades)
- ✅ `requiredComponents` por entidade (críticos marcados)
- ✅ `requiredUI` (StartScreen, HUD, GameOverScreen)
- ✅ `requiredControls` (WASD + SPACE)
- ✅ `requiredSignals` (player_health, score, timer, wave)
- ✅ `requiredLifecycle` (start, lose, restart)

### Tarefa 2: Validador ✅
- ✅ Detecta sistemas faltantes
- ✅ Detecta entidades faltantes
- ✅ Detecta componentes faltantes (com heurísticas)
- ✅ Detecta props obrigatórias faltantes
- ✅ Detecta UI faltante
- ✅ Detecta controles faltantes
- ✅ Detecta sinais faltantes
- ✅ Retorna lista estruturada de violações CRÍTICAS
- ✅ Helpers de formatação
- ✅ Testes unitários

---

## 🚀 Próximos Passos (Sugestões)

### Fase 2.1: Integração com Protocolo
1. Adicionar validação de perfil no `game-ai-chat-stream`
2. Retornar violações na fase de validação
3. IA usar violações para corrigir o código

### Fase 2.2: Geração Assistida
1. IA detecta violações CRITICAL
2. IA gera código para corrigir automaticamente
3. Loop até runtime estar válido

### Fase 2.3: Mais Gêneros
1. Criar `platformer.ts` profile
2. Criar `puzzle.ts` profile
3. Criar `racing.ts` profile

---

## 📝 Notas Importantes

### ✅ O que FOI feito:
- Perfil canônico completo e detalhado
- Validador robusto com heurísticas inteligentes
- Exemplos de uso práticos
- Testes unitários
- Documentação inline

### ❌ O que NÃO foi mexido (conforme solicitado):
- Chat (`StudioChatPanel.tsx`, `game-ai-chat/index.ts`)
- Backend (`supabase/functions/*`)
- Streaming (`ai-streaming.ts`)
- Protocolo (`ORDAX_COMPILER_PROTOCOL_V1.md`)

### 🎯 Foco:
Apenas criação do **profile** e do **validador** para estabelecer o contrato canônico do gênero top-down shooter survival.

---

## 🧪 Testar

```bash
# Rodar testes
npm test -- src/lib/ordax/runtime-profiles/validator.test.ts

# Rodar exemplo
npm run dev
# Importar e executar example-validation.ts no console
```

---

**Status Final:** ✅ **COMPLETO**

Perfil canônico e validador implementados e prontos para uso. O runtime da Ordax agora tem um contrato claro do que é necessário para um top-down shooter survival funcional.
