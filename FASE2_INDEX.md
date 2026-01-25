# 📚 FASE 2 - ÍNDICE DE DOCUMENTAÇÃO

## 🎯 Visão Geral

A Fase 2 implementa o **perfil canônico de runtime** para o gênero **top-down shooter survival** e um **validador robusto** que detecta violações CRÍTICAS.

---

## 📖 Documentação

### 1. 📋 [RESUMO EXECUTIVO](./FASE2_RESUMO_EXECUTIVO.md)
**Leia primeiro!** Visão geral da implementação, entregáveis e status.

**Conteúdo:**
- Objetivo alcançado
- Entregáveis
- O que o validador detecta
- Níveis de violação
- Como usar
- Status de implementação
- Próximos passos

---

### 2. 📊 [DIAGRAMA VISUAL](./FASE2_DIAGRAMA_PROFILE_VALIDATOR.md)
Diagramas e fluxos visuais do sistema.

**Conteúdo:**
- Arquitetura do validador
- Perfil canônico visual
- Fluxo de validação
- Níveis de violação
- Integração com protocolo
- Exemplos visuais

---

### 3. 📝 [DOCUMENTAÇÃO COMPLETA](./FASE2_RUNTIME_PROFILE_IMPLEMENTADO.md)
Documentação técnica detalhada.

**Conteúdo:**
- Arquivos criados/atualizados
- Perfil canônico detalhado
- Validador detalhado
- Exemplos de uso
- Testes implementados
- Notas importantes

---

### 4. 🚀 [GUIA DE INTEGRAÇÃO RÁPIDO](./FASE2_GUIA_INTEGRACAO_RAPIDO.md)
Como integrar o validador no seu código.

**Conteúdo:**
- Uso básico
- Integração com protocolo (3 opções)
- Integração com IA (feedback loop)
- Exibir violações no frontend
- Testar
- Checklist de integração
- Exemplo completo end-to-end

---

### 5. 🎮 [EXEMPLOS PRÁTICOS](./FASE2_EXEMPLOS_PRATICOS.md)
Exemplos de runtimes válidos e inválidos.

**Conteúdo:**
- Runtime mínimo (inválido)
- Runtime com sistemas mas sem entidades (inválido)
- Runtime com player incompleto (inválido)
- Runtime completo e válido ✅
- Runtime quase completo (falta UI)
- Corrigindo violações passo a passo
- Resumo de violações por categoria
- Dicas para criar runtime válido

---

## 💻 Código Fonte

### Perfil Canônico
📄 `src/lib/ordax/runtime-profiles/topdown-shooter.ts`

**Exports:**
- `TOPDOWN_SHOOTER_PROFILE` - Perfil canônico completo
- `RuntimeProfile` - Interface do perfil
- `EntityProfile` - Interface de entidade
- `ComponentProfile` - Interface de componente
- `UIProfile` - Interface de UI
- `ControlProfile` - Interface de controles
- `SignalProfile` - Interface de sinais
- `LifecycleProfile` - Interface de lifecycle
- Helpers: `isSystemRequired()`, `isEntityRequired()`, `getEntityProfile()`, `getCriticalComponents()`

---

### Validador
📄 `src/lib/ordax/runtime-profiles/validator.ts`

**Exports:**
- `validateRuntimeAgainstProfile()` - Função principal de validação
- `formatProfileViolations()` - Formata violações para console
- `generateMissingElementsReport()` - Gera relatório de elementos faltantes
- `ProfileValidationResult` - Interface do resultado
- `ProfileViolation` - Interface de violação
- `ProfileViolationLevel` - Tipo de nível de violação

---

### Exemplos
📄 `src/lib/ordax/runtime-profiles/example-validation.ts`

**Exports:**
- `validateGameBeforeCompile()` - Validação em pipeline de compilação
- `generateAIFeedback()` - Feedback para IA
- Exemplos de runtimes incompletos e completos

---

### Índice
📄 `src/lib/ordax/runtime-profiles/index.ts`

**Exports:**
- Re-exporta tudo de forma organizada
- Ponto de entrada único para importações

---

### Testes
📄 `src/lib/ordax/runtime-profiles/validator.test.ts`

**Testes:**
- Detecta sistemas faltantes
- Detecta entidades faltantes
- Detecta componentes faltantes
- Valida runtime completo
- Detecta props obrigatórias faltantes

---

## 🎯 Perfil Canônico: Top-Down Shooter Survival

### Resumo Rápido

```typescript
TOPDOWN_SHOOTER_PROFILE = {
  genre: "topdown-shooter-survival",
  
  // 7 Sistemas
  requiredSystems: [
    "PhysicsSystem", "CollisionSystem", "AISystem",
    "SpawnerSystem", "ScoreSystem", "TimerSystem", "UISystem"
  ],
  
  // 4 Entidades
  requiredEntities: [
    { type: "player", requiredComponents: [Transform, Velocity, Health, Weapon, Collider] },
    { type: "enemy", requiredComponents: [Transform, Velocity, Health, AI, Collider] },
    { type: "bullet", requiredComponents: [Transform, Velocity, Collider, Lifetime] },
    { type: "spawner", requiredComponents: [Transform, Spawner] }
  ],
  
  // UI
  requiredUI: {
    startScreen: { required: true, mustHave: ["title", "startButton", "instructions"] },
    hud: { required: true, mustDisplay: ["health", "score", "timer", "wave"] },
    gameOverScreen: { required: true, mustHave: ["finalScore", "survivalTime", "restartButton"] }
  },
  
  // Controles
  requiredControls: {
    movement: { keys: ["W", "A", "S", "D"] },
    action: { keys: ["SPACE", "MOUSE_LEFT"] }
  },
  
  // Sinais
  requiredSignals: [
    { name: "player_health", required: true },
    { name: "score", required: true },
    { name: "timer", required: true },
    { name: "wave", required: false }
  ]
}
```

---

## 🔍 Validador: Como Funciona

### Entrada
```typescript
validateRuntimeAgainstProfile(
  runtimeSpec: OrdaxSpec,
  profile: RuntimeProfile
)
```

### Saída
```typescript
{
  isValid: boolean,
  genre: string,
  violations: ProfileViolation[],
  summary: {
    critical: number,
    severe: number,
    minor: number
  },
  missingElements: {
    systems: string[],
    entities: string[],
    components: Record<string, string[]>,
    uiElements: string[],
    controls: string[],
    signals: string[]
  }
}
```

### Validações
1. ✅ Sistemas faltantes → CRITICAL
2. ✅ Entidades faltantes → CRITICAL
3. ✅ Componentes faltantes → CRITICAL
4. ✅ Props obrigatórias faltantes → SEVERE
5. ✅ UI faltante → CRITICAL
6. ✅ Controles faltantes → CRITICAL
7. ✅ Sinais faltantes → SEVERE

---

## 🚀 Quick Start

### 1. Importar
```typescript
import {
  TOPDOWN_SHOOTER_PROFILE,
  validateRuntimeAgainstProfile,
  formatProfileViolations
} from '@/lib/ordax/runtime-profiles';
```

### 2. Validar
```typescript
const result = validateRuntimeAgainstProfile(myRuntimeSpec, TOPDOWN_SHOOTER_PROFILE);

if (!result.isValid) {
  console.error(formatProfileViolations(result));
}
```

### 3. Verificar Violações
```typescript
if (result.summary.critical > 0) {
  console.error("❌ Jogo não pode ser compilado");
}
```

---

## 📊 Estrutura de Arquivos

```
src/lib/ordax/runtime-profiles/
├── topdown-shooter.ts        # Perfil canônico
├── validator.ts              # Validador
├── index.ts                  # Exports
├── example-validation.ts     # Exemplos
└── validator.test.ts         # Testes

docs/
├── FASE2_INDEX.md                        # Este arquivo
├── FASE2_RESUMO_EXECUTIVO.md             # Resumo executivo
├── FASE2_DIAGRAMA_PROFILE_VALIDATOR.md   # Diagramas
├── FASE2_RUNTIME_PROFILE_IMPLEMENTADO.md # Documentação completa
├── FASE2_GUIA_INTEGRACAO_RAPIDO.md       # Guia de integração
└── FASE2_EXEMPLOS_PRATICOS.md            # Exemplos práticos
```

---

## 🧪 Testar

### Rodar Testes
```bash
npm test -- src/lib/ordax/runtime-profiles/validator.test.ts
```

### Teste Manual
```typescript
import { TOPDOWN_SHOOTER_PROFILE, validateRuntimeAgainstProfile } from '@/lib/ordax/runtime-profiles';

const testRuntime = {
  gameType: 'topdown',
  title: 'Test',
  description: 'Test',
  systems: ['PhysicsSystem'],
  scene: { gravity: { x: 0, y: 0 }, entities: [] }
};

const result = validateRuntimeAgainstProfile(testRuntime, TOPDOWN_SHOOTER_PROFILE);
console.log('Valid?', result.isValid);
console.log('Critical:', result.summary.critical);
```

---

## 📈 Próximos Passos

### Fase 2.1: Integração com Protocolo
- [ ] Adicionar validação no `game-ai-chat-stream`
- [ ] Retornar violações na fase de validação
- [ ] IA usar violações para corrigir código

### Fase 2.2: Geração Assistida
- [ ] IA detecta violações CRITICAL
- [ ] IA gera código para corrigir automaticamente
- [ ] Loop até runtime estar válido

### Fase 2.3: Mais Gêneros
- [ ] Criar `platformer.ts` profile
- [ ] Criar `puzzle.ts` profile
- [ ] Criar `racing.ts` profile

### Fase 2.4: UI de Validação
- [ ] Criar `ValidationPanel` component
- [ ] Exibir violações em tempo real
- [ ] Botão para corrigir automaticamente

---

## 🎯 Status

| Item | Status |
|------|--------|
| Perfil Canônico | ✅ Completo |
| Validador | ✅ Completo |
| Testes | ✅ Completo |
| Documentação | ✅ Completo |
| Exemplos | ✅ Completo |
| Integração | ⏳ Pendente |

---

## 📞 Suporte

### Dúvidas sobre o Perfil?
Leia: [FASE2_RUNTIME_PROFILE_IMPLEMENTADO.md](./FASE2_RUNTIME_PROFILE_IMPLEMENTADO.md)

### Dúvidas sobre Integração?
Leia: [FASE2_GUIA_INTEGRACAO_RAPIDO.md](./FASE2_GUIA_INTEGRACAO_RAPIDO.md)

### Precisa de Exemplos?
Leia: [FASE2_EXEMPLOS_PRATICOS.md](./FASE2_EXEMPLOS_PRATICOS.md)

### Quer Visão Geral?
Leia: [FASE2_RESUMO_EXECUTIVO.md](./FASE2_RESUMO_EXECUTIVO.md)

---

**Data:** 25/01/2026  
**Versão:** 1.0  
**Status:** ✅ **COMPLETO**
