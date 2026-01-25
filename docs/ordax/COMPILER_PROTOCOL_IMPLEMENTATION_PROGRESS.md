# Ordax Compiler Protocol Implementation Progress

**Data:** 25 de Janeiro de 2026  
**Status:** EM PROGRESSO

---

## Resumo

Implementação do protocolo de compilação de 5 fases obrigatórias no backend da Ordax Engine.

---

## ✅ Parte 1: Máquina de Estados (COMPLETO)

### Implementado em `supabase/functions/game-ai-chat/index.ts`

```typescript
// Tipos de fase do compilador
type CompilerPhase = "interpretation" | "plan" | "validation" | "confirmation" | "compilation";

// Estado da sessão do compilador
interface CompilerSessionState {
  phase: CompilerPhase;
  gamePlan?: any;
  validationReport?: ValidationResult;
  approvedByUser: boolean;
  interpretation?: {
    gameType: string;
    mechanics: string[];
    restrictions: string[];
    objective: string;
  };
}

// Storage em memória (produção: usar Redis)
const compilerSessions = new Map<string, CompilerSessionState>();

// Funções de gerenciamento
function getSessionId(messages: any[]): string
function getOrCreateSession(sessionId: string, isNewGame: boolean): CompilerSessionState
function updateSession(sessionId: string, updates: Partial<CompilerSessionState>): void
```

**Status:** ✅ Implementado e funcionando

---

## ✅ Parte 2: Validação de Fase (COMPLETO)

### Implementado em `supabase/functions/game-ai-chat/index.ts` (linhas ~1020-1055)

```typescript
// Obter ou criar sessão do compilador
const sessionId = getSessionId(messages);
const isNewGame = resolvedMode === "spec" && !currentSpec;
const session = getOrCreateSession(sessionId, isNewGame);

// Validar fase atual antes de permitir geração
if (isNewGame) {
  // Se tentando compilar sem passar pelas fases anteriores
  if (phase === "spec" && session.phase !== "confirmation") {
    return new Response(JSON.stringify({
      error: "COMPILER_PROTOCOL_VIOLATION",
      message: `Cannot compile game. Current phase: ${session.phase}...`,
      currentPhase: session.phase,
      requiredPhase: "confirmation",
      protocol: "ORDAX_COMPILER_PROTOCOL_V1"
    }), { status: 400, ... });
  }

  // Se tentando compilar sem aprovação do usuário
  if (phase === "spec" && !session.approvedByUser) {
    return new Response(JSON.stringify({
      error: "COMPILER_PROTOCOL_VIOLATION",
      message: "Cannot compile game without user approval...",
      currentPhase: session.phase,
      approvedByUser: session.approvedByUser,
      protocol: "ORDAX_COMPILER_PROTOCOL_V1"
    }), { status: 400, ... });
  }
}
```

**Status:** ✅ Implementado - Bloqueia compilação sem passar pelas fases

---

## ✅ Parte 3: Lógica de Fases (COMPLETO)

### FASE 1: INTERPRETATION (linhas ~1075-1125)

```typescript
if (currentPhase === "interpretation") {
  // Gera interpretação do pedido usando AI
  const interpretationPrompt = `Você é o Ordax Interpreter...`;
  
  // Chama AI para interpretar
  const interpretationResp = await fetch(...);
  
  // Atualiza sessão e avança para próxima fase
  updateSession(sessionId, {
    interpretation: interpretationResult.interpretation,
    phase: "plan"
  });

  return new Response(JSON.stringify({
    kind: "INTERPRETATION_RESULT",
    phase: "interpretation",
    interpretation: interpretationResult.interpretation,
    nextPhase: "plan"
  }), ...);
}
```

**Status:** ✅ Implementado

### FASE 2: PLAN CONSTRUCTION (linhas ~1127-1200)

```typescript
if (currentPhase === "plan" && !approvedPlan) {
  // Gera GAME_PLAN estruturado usando AI
  const planPrompt = `Você é o Ordax Planner...`;
  
  // Chama AI para gerar plano
  const planResp = await fetch(...);
  
  // Valida e completa o plano
  const completed = validateAndCompletePlan(planJson, userPrompt);
  validatedPlan = completed.plan;
  planWarnings = uniq([...planWarnings, ...completed.warnings]);
  planDiff = completed.diff;

  // Atualiza sessão e avança para validação
  updateSession(sessionId, {
    gamePlan: validatedPlan,
    phase: "validation"
  });

  return new Response(JSON.stringify({
    kind: "GAME_PLAN_RESULT",
    phase: "plan",
    plan: validatedPlan,
    planWarnings,
    planDiff,
    nextPhase: "validation"
  }), ...);
}
```

**Status:** ✅ Implementado

### FASE 3: CONSTITUTIONAL VALIDATION (linhas ~1202-1240)

```typescript
if (currentPhase === "validation") {
  // Obter plano da sessão
  const planToValidate = session.gamePlan;
  
  // Criar runtimeSpec simulado para validação
  const mockSpec: RuntimeSpec = {
    code: JSON.stringify(planToValidate),
    hasTimeManager: true,
    hasStateManager: true,
    hasInputManager: true,
    hasSaveManager: true,
    hasViewportManager: true,
    hasStartScreen: true,
    hasHUD: planToValidate.mustHave?.hasHUD ?? true,
    hasGameOverScreen: true
  };

  const validationResult = validateConstitutionalCompliance(mockSpec);

  // Atualiza sessão e avança para confirmação
  updateSession(sessionId, {
    validationReport: validationResult,
    phase: "confirmation"
  });

  return new Response(JSON.stringify({
    kind: "VALIDATION_RESULT",
    phase: "validation",
    validation: validationResult,
    plan: planToValidate,
    nextPhase: "confirmation"
  }), ...);
}
```

**Status:** ✅ Implementado

### FASE 4: USER CONFIRMATION (linhas ~1242-1260)

```typescript
if (currentPhase === "confirmation" && !session.approvedByUser) {
  // Retornar plano para confirmação do usuário
  const planToConfirm = session.gamePlan;
  const validationReport = session.validationReport;

  return new Response(JSON.stringify({
    kind: "CONFIRMATION_REQUIRED",
    phase: "confirmation",
    plan: planToConfirm,
    validation: validationReport,
    message: "Please review and approve the game plan before compilation",
    nextPhase: "compilation"
  }), ...);
}
```

**Status:** ✅ Implementado

### FASE 5: COMPILATION (linhas ~1262-1280)

```typescript
if (approvedPlan) {
  // Marcar como aprovado e avançar para compilação
  updateSession(sessionId, {
    approvedByUser: true,
    phase: "compilation"
  });

  // Continuar com a compilação normal
  const completed = validateAndCompletePlan(planJson, userPrompt);
  validatedPlan = completed.plan;
  planWarnings = uniq([...planWarnings, ...completed.warnings]);
  planDiff = completed.diff;
}
```

**Status:** ✅ Implementado

---

## ❌ Parte 4: Frontend UI (NÃO IMPLEMENTADO)

### O que falta:

1. **Exibir fase atual do compilador**
   - Mostrar indicador visual: "Fase 1/5: Interpretação"
   - Mostrar progresso das fases

2. **Desabilitar input durante validation**
   - Bloquear chat enquanto valida
   - Mostrar spinner/loading

3. **Botão "Aceitar plano e compilar"**
   - Botão explícito para aprovar plano
   - Não permitir compilação sem aceite

4. **Exibir resultados de cada fase**
   - Mostrar interpretação formatada
   - Mostrar plano estruturado
   - Mostrar resultado da validação
   - Pedir confirmação explícita

**Arquivos a modificar:**
- `src/components/ordax/StudioChatPanel.tsx` (ou similar)
- `src/components/ordax/OrdaxStudio.tsx` (ou similar)

**Status:** ❌ NÃO IMPLEMENTADO

---

## ❌ Parte 5: Streaming Version (NÃO IMPLEMENTADO)

### O que falta:

Aplicar as mesmas mudanças em:
- `supabase/functions/game-ai-chat-stream/index.ts`

**Status:** ❌ NÃO IMPLEMENTADO

---

## 🎯 Resultado Atual

### O que funciona:

✅ Backend bloqueia compilação sem passar pelas 5 fases  
✅ Sessões do compilador são gerenciadas em memória  
✅ Cada fase retorna output específico (INTERPRETATION_RESULT, GAME_PLAN_RESULT, etc.)  
✅ Validação constitucional integrada na fase 3  
✅ Aprovação do usuário é obrigatória antes da compilação  

### O que NÃO funciona:

❌ Frontend não sabe lidar com as novas fases  
❌ Usuário não consegue aprovar planos (sem UI)  
❌ Streaming version não tem o protocolo  
❌ Mensagens de status não são exibidas  

---

## 📋 Próximos Passos

### Prioridade ALTA:

1. **Implementar UI mínima no frontend**
   - Detectar `kind: "INTERPRETATION_RESULT"` e exibir
   - Detectar `kind: "GAME_PLAN_RESULT"` e exibir
   - Detectar `kind: "VALIDATION_RESULT"` e exibir
   - Detectar `kind: "CONFIRMATION_REQUIRED"` e mostrar botão "Aceitar"

2. **Adicionar botão de aprovação**
   - Quando receber `CONFIRMATION_REQUIRED`, mostrar botão
   - Ao clicar, enviar `{ approvedPlan: plan, phase: "spec" }`

3. **Aplicar no streaming version**
   - Copiar lógica de fases para `game-ai-chat-stream/index.ts`

### Prioridade MÉDIA:

4. **Melhorar persistência de sessões**
   - Usar Redis ou Supabase para persistir sessões
   - Evitar perda de estado ao recarregar página

5. **Adicionar mensagens de status**
   - Emitir "🛠️ COMPILANDO JOGO..." durante compilação
   - Emitir "📖 Lendo estado atual..." etc.

---

## 🔒 Regra de Ouro

**É IMPOSSÍVEL gerar um jogo sem passar pelas 5 fases.**

O backend agora BLOQUEIA qualquer tentativa de pular fases.

---

## 📝 Notas Técnicas

### Limitações Atuais:

1. **Sessões em memória**: Perdidas ao reiniciar servidor
2. **SessionId simplificado**: Baseado em primeiras 2 mensagens (pode colidir)
3. **Frontend desatualizado**: Não sabe lidar com novas respostas
4. **Streaming não implementado**: Apenas versão não-streaming tem protocolo

### Decisões de Design:

- **5 fases obrigatórias**: interpretation → plan → validation → confirmation → compilation
- **Bloqueio no backend**: Frontend não pode pular fases
- **Validação constitucional**: Integrada na fase 3
- **Aprovação explícita**: Usuário DEVE aceitar plano antes de compilar

---

**Assinatura:**
```
ORDAX COMPILER PROTOCOL IMPLEMENTATION
Versão: 1.0.0 (Parcial)
Data: 2026-01-25
Status: Backend implementado, Frontend pendente
```
