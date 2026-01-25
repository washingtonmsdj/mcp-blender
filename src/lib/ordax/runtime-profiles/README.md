# 🎮 Runtime Profiles

Perfis canônicos de gêneros de jogos para a Ordax Engine.

## 📖 O que é um Runtime Profile?

Um **Runtime Profile** define EXATAMENTE o que um jogo funcional de um determinado gênero DEVE ter para ser considerado jogável.

Cada perfil especifica:
- **Sistemas obrigatórios** (ex: PhysicsSystem, CollisionSystem)
- **Entidades obrigatórias** (ex: player, enemy, bullet)
- **Componentes críticos** por entidade (ex: Health, Weapon)
- **UI obrigatória** (ex: StartScreen, HUD, GameOverScreen)
- **Controles obrigatórios** (ex: WASD, SPACE)
- **Sinais obrigatórios** (ex: player_health, score)
- **Lifecycle** (ex: start, lose, restart)

## 🎯 Gêneros Suportados

### ✅ Top-Down Shooter Survival
**Arquivo:** `topdown-shooter.ts`

Jogo onde o jogador sobrevive ondas de inimigos, atirando e se movendo em 360°.

**Elementos obrigatórios:**
- 7 sistemas (Physics, Collision, AI, Spawner, Score, Timer, UI)
- 4 entidades (player, enemy, bullet, spawner)
- UI completa (StartScreen, HUD, GameOverScreen)
- Controles (WASD + SPACE)

### 🚧 Outros Gêneros (Futuros)
- Platformer
- Puzzle
- Racing
- Sports

## 🚀 Quick Start

### Importar
```typescript
import {
  TOPDOWN_SHOOTER_PROFILE,
  validateRuntimeAgainstProfile,
  formatProfileViolations
} from '@/lib/ordax/runtime-profiles';
```

### Validar Runtime
```typescript
const result = validateRuntimeAgainstProfile(
  myRuntimeSpec,
  TOPDOWN_SHOOTER_PROFILE
);

if (!result.isValid) {
  console.error(formatProfileViolations(result));
}
```

### Verificar Violações
```typescript
if (result.summary.critical > 0) {
  console.error("❌ Jogo não pode ser compilado");
  
  // Listar elementos faltantes
  console.log("Sistemas faltantes:", result.missingElements.systems);
  console.log("Entidades faltantes:", result.missingElements.entities);
}
```

## 📦 Arquivos

### `topdown-shooter.ts`
Perfil canônico do gênero top-down shooter survival.

**Exports:**
- `TOPDOWN_SHOOTER_PROFILE` - Perfil completo
- `RuntimeProfile` - Interface do perfil
- `EntityProfile` - Interface de entidade
- `ComponentProfile` - Interface de componente
- Helpers: `isSystemRequired()`, `isEntityRequired()`, etc.

### `validator.ts`
Validador de runtime contra perfil.

**Exports:**
- `validateRuntimeAgainstProfile()` - Função principal
- `formatProfileViolations()` - Formata violações
- `generateMissingElementsReport()` - Gera relatório
- `ProfileValidationResult` - Interface do resultado
- `ProfileViolation` - Interface de violação

### `index.ts`
Ponto de entrada único com todos os exports organizados.

### `example-validation.ts`
Exemplos práticos de uso do validador.

**Exports:**
- `validateGameBeforeCompile()` - Validação em pipeline
- `generateAIFeedback()` - Feedback para IA

### `validator.test.ts`
Testes unitários do validador.

## 🔍 Como Funciona o Validador

### Entrada
```typescript
validateRuntimeAgainstProfile(
  runtimeSpec: OrdaxSpec,
  profile: RuntimeProfile
): ProfileValidationResult
```

### Validações Realizadas

1. **Sistemas** - Verifica se todos os sistemas obrigatórios estão presentes
2. **Entidades** - Verifica se todas as entidades obrigatórias existem
3. **Componentes** - Verifica se entidades têm componentes críticos
4. **Props** - Verifica se props obrigatórias estão presentes
5. **UI** - Verifica se telas obrigatórias existem
6. **Controles** - Verifica se controles obrigatórios estão definidos
7. **Sinais** - Verifica se sinais obrigatórios existem

### Saída
```typescript
{
  isValid: boolean,              // true se 0 violações CRITICAL
  genre: string,                 // Nome do gênero
  violations: ProfileViolation[], // Lista de violações
  summary: {
    critical: number,            // Violações críticas
    severe: number,              // Violações graves
    minor: number                // Violações menores
  },
  missingElements: {
    systems: string[],           // Sistemas faltantes
    entities: string[],          // Entidades faltantes
    components: Record<string, string[]>, // Componentes faltantes por entidade
    uiElements: string[],        // UI faltante
    controls: string[],          // Controles faltantes
    signals: string[]            // Sinais faltantes
  }
}
```

## 🚦 Níveis de Violação

### 🔴 CRITICAL
Elementos essenciais sem os quais o jogo não funciona.

**Exemplos:**
- Sistemas faltantes
- Entidades faltantes
- Componentes críticos faltantes
- UI faltante
- Controles faltantes

**Ação:** ❌ Bloquear compilação

### 🟠 SEVERE
Elementos importantes que comprometem a funcionalidade.

**Exemplos:**
- Props obrigatórias faltantes
- Sinais obrigatórios faltantes

**Ação:** ⚠️ Avisar fortemente

### 🟡 MINOR
Elementos opcionais que melhoram a experiência.

**Exemplos:**
- Componentes opcionais faltantes
- Sinais opcionais faltantes

**Ação:** ℹ️ Avisar levemente

## 📊 Exemplo Completo

### Runtime Válido
```typescript
const validRuntime: OrdaxSpec = {
  gameType: "topdown",
  title: "Space Shooter",
  description: "Survive waves of enemies",
  
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
          health: 100,
          speed: 200,
          fireRate: 0.2,
          vx: 0,
          vy: 0,
          damage: 25
        }
      },
      {
        id: "enemy1",
        type: "enemy",
        x: 200,
        y: 100,
        w: 24,
        h: 24,
        props: {
          health: 50,
          speed: 100,
          damage: 10,
          ai: "chase",
          target: "player"
        }
      },
      {
        id: "bullet1",
        type: "bullet",
        x: 0,
        y: 0,
        w: 4,
        h: 4,
        props: {
          speed: 400,
          damage: 25
        }
      },
      {
        id: "spawner1",
        type: "spawner",
        x: 400,
        y: 50,
        w: 1,
        h: 1,
        props: {
          spawnRate: 2.0,
          spawner: true
        }
      }
    ]
  }
};

const result = validateRuntimeAgainstProfile(validRuntime, TOPDOWN_SHOOTER_PROFILE);
console.log(result.isValid); // true ✅
```

### Runtime Inválido
```typescript
const invalidRuntime: OrdaxSpec = {
  gameType: "topdown",
  title: "Incomplete Game",
  description: "Missing many elements",
  systems: ["PhysicsSystem"], // Faltam 6 sistemas
  scene: {
    gravity: { x: 0, y: 0 },
    entities: [] // Faltam todas as entidades
  }
};

const result = validateRuntimeAgainstProfile(invalidRuntime, TOPDOWN_SHOOTER_PROFILE);
console.log(result.isValid); // false ❌
console.log(result.summary.critical); // 11
console.log(result.missingElements.systems); // ["CollisionSystem", "AISystem", ...]
console.log(result.missingElements.entities); // ["player", "enemy", "bullet", "spawner"]
```

## 🧪 Testar

### Rodar Testes
```bash
npm test -- src/lib/ordax/runtime-profiles/validator.test.ts
```

### Teste Manual
```typescript
import { TOPDOWN_SHOOTER_PROFILE, validateRuntimeAgainstProfile } from './index';

const testRuntime = {
  gameType: 'topdown',
  title: 'Test',
  description: 'Test',
  systems: [],
  scene: { gravity: { x: 0, y: 0 }, entities: [] }
};

const result = validateRuntimeAgainstProfile(testRuntime, TOPDOWN_SHOOTER_PROFILE);
console.log('Valid?', result.isValid);
console.log('Critical:', result.summary.critical);
console.log('Missing:', result.missingElements);
```

## 📚 Documentação Completa

Para documentação completa, veja:
- `FASE2_INDEX.md` - Índice de documentação
- `FASE2_RESUMO_EXECUTIVO.md` - Resumo executivo
- `FASE2_GUIA_INTEGRACAO_RAPIDO.md` - Guia de integração
- `FASE2_EXEMPLOS_PRATICOS.md` - Exemplos práticos

## 🎯 Próximos Passos

1. **Integrar no Protocolo** - Adicionar validação no fluxo de compilação
2. **Feedback para IA** - IA usar violações para corrigir código
3. **Mais Gêneros** - Criar perfis para platformer, puzzle, racing
4. **UI de Validação** - Exibir violações em tempo real no frontend

## 📝 Contribuir

Para adicionar um novo gênero:

1. Criar arquivo `[genero].ts` com perfil canônico
2. Definir `requiredSystems`, `requiredEntities`, etc.
3. Adicionar testes em `validator.test.ts`
4. Atualizar este README

## 📞 Suporte

Dúvidas? Consulte a documentação completa em `FASE2_INDEX.md`.

---

**Status:** ✅ Implementado e testado  
**Versão:** 1.0  
**Data:** 25/01/2026
