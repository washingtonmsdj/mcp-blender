# Guia de Implementação - Compiler Protocol V1

**Data:** 25 de Janeiro de 2026  
**Status:** GUIA DE IMPLEMENTAÇÃO

---

## Objetivo

Transformar o Chat da Ordax em um Game Compiler Agent determinístico com protocolo rígido de 4 fases.

---

## Arquivos Criados

### ✅ 1. ORDAX_COMPILER_PROTOCOL_V1.md
**Localização:** `docs/ordax/ORDAX_COMPILER_PROTOCOL_V1.md`  
**Status:** ✅ Completo

**Conteúdo:**
- Protocolo completo das 4 fases obrigatórias
- Formato de resposta estruturado
- Comportamentos proibidos
- Mensagens de status obrigatórias
- Exemplos completos de cada fase

---

## Mudanças Necessárias nos Prompts do AI

### Arquivo: `supabase/functions/game-ai-chat/index.ts`

#### Mudança 1: Atualizar `systemPrompt()`

**Adicionar no início do prompt:**

```typescript
🤖 VOCÊ É UM GAME COMPILER AGENT (não um assistente genérico)

PROTOCOLO OBRIGATÓRIO (4 FASES):
Toda resposta deve seguir estas fases na ordem:

1. INTERPRETATION: Interpretar o pedido do usuário
2. PLAN CONSTRUCTION: Construir GAME_PLAN estruturado
3. CONSTITUTIONAL VALIDATION: Validar contra contrato
4. USER CONFIRMATION: Pedir confirmação explícita

COMPORTAMENTOS PROIBIDOS:
❌ Sugerir sistemas essenciais ("você pode adicionar X depois")
❌ Responder com listas genéricas
❌ Ignorar estado atual do jogo
❌ Fingir que aplicou algo que não aplicou

MENSAGENS DE STATUS OBRIGATÓRIAS:
Durante compilação, emita:
- "📖 Lendo estado atual do jogo..."
- "🧠 Construindo plano do jogo..."
- "⚖️ Validando contra contrato constitucional..."
- "🔨 Gerando código do jogo..."
```

#### Mudança 2: Adicionar Formato de Resposta Estruturado

```typescript
FORMATO DE RESPOSTA (SEMPRE):

Para NEW_GAME:
{
  "phase": "interpretation" | "plan" | "validation" | "confirmation" | "compilation",
  "interpretation": {
    "gameType": string,
    "mechanics": string[],
    "restrictions": string[],
    "objective": string
  },
  "plan": {
    "coreLoop": string,
    "mechanics": string[],
    "controls": string[],
    "hud": string[],
    "fsm": { "START": string, "PLAYING": string, "PAUSED": string, "GAME_OVER": string },
    "systems": string[],
    "lifecycle": {
      "start": string,
      "loseCondition": string,
      "winCondition": string,
      "restart": string,
      "signal": "player_health" | "objective_progress" | "timer"
    }
  },
  "validation": {
    "status": "valid" | "incomplete" | "invalid",
    "pillarChecklist": {
      "timeManagement": boolean,
      "fsm": boolean,
      "uiSystem": boolean,
      "inputSystem": boolean,
      "saveSystem": boolean,
      "viewportManagement": boolean,
      "gameLoop": boolean
    },
    "promptValidation": {
      "allMechanicsIncluded": boolean,
      "restrictionsRespected": boolean,
      "objectiveImplementable": boolean
    },
    "autoCompletions": string[],
    "warnings": string[]
  },
  "confirmation": {
    "summary": string,
    "whatWillBeGenerated": string[],
    "engineLimitations": string[],
    "question": "Este é o jogo que você quer gerar?"
  },
  "spec": <OrdaxSpec> (apenas após confirmação),
  "assistantSummary": string,
  "appliedEdits": string[],
  "semanticPatch": {...},
  "report": {...}
}
```

### Arquivo: `supabase/functions/game-ai-chat-stream/index.ts`

**Mesmas mudanças do arquivo acima.**

---

## Mudanças no Frontend (Opcional)

### Arquivo: `src/components/ordax/ChatPanel.tsx` (ou equivalente)

#### Adicionar Renderização de Fases

```typescript
// Detectar fase atual da resposta
if (message.phase === 'interpretation') {
  return <InterpretationView data={message.interpretation} />
}

if (message.phase === 'plan') {
  return <PlanView data={message.plan} />
}

if (message.phase === 'validation') {
  return <ValidationView data={message.validation} />
}

if (message.phase === 'confirmation') {
  return <ConfirmationView data={message.confirmation} onConfirm={handleConfirm} />
}

if (message.phase === 'compilation') {
  return <CompilationView status={message.compilationStatus} />
}
```

#### Adicionar Componentes de Visualização

```typescript
// InterpretationView.tsx
function InterpretationView({ data }) {
  return (
    <div className="interpretation-phase">
      <h3>📖 INTERPRETAÇÃO DO PEDIDO</h3>
      <p><strong>Tipo de jogo:</strong> {data.gameType}</p>
      <p><strong>Mecânicas solicitadas:</strong></p>
      <ul>
        {data.mechanics.map(m => <li key={m}>{m}</li>)}
      </ul>
      <p><strong>Objetivo:</strong> {data.objective}</p>
    </div>
  )
}

// PlanView.tsx
function PlanView({ data }) {
  return (
    <div className="plan-phase">
      <h3>🧠 PLANO DO JOGO</h3>
      <p><strong>Loop Principal:</strong> {data.coreLoop}</p>
      <details>
        <summary>Ver Mecânicas</summary>
        <ul>
          {data.mechanics.map(m => <li key={m}>{m}</li>)}
        </ul>
      </details>
      <details>
        <summary>Ver Sistemas</summary>
        <ul>
          {data.systems.map(s => <li key={s}>{s}</li>)}
        </ul>
      </details>
    </div>
  )
}

// ValidationView.tsx
function ValidationView({ data }) {
  return (
    <div className="validation-phase">
      <h3>⚖️ VALIDAÇÃO CONSTITUCIONAL</h3>
      <p><strong>Status:</strong> {data.status === 'valid' ? '✅ VÁLIDO' : '⚠️ INCOMPLETO'}</p>
      <details>
        <summary>Checklist dos 7 Pilares</summary>
        <ul>
          {Object.entries(data.pillarChecklist).map(([key, value]) => (
            <li key={key}>{value ? '✅' : '❌'} {key}</li>
          ))}
        </ul>
      </details>
      {data.autoCompletions.length > 0 && (
        <details>
          <summary>Auto-Completações</summary>
          <ul>
            {data.autoCompletions.map(a => <li key={a}>{a}</li>)}
          </ul>
        </details>
      )}
    </div>
  )
}

// ConfirmationView.tsx
function ConfirmationView({ data, onConfirm }) {
  return (
    <div className="confirmation-phase">
      <h3>✅ PLANO PRONTO PARA COMPILAÇÃO</h3>
      <p>{data.summary}</p>
      <details>
        <summary>O que será gerado</summary>
        <ul>
          {data.whatWillBeGenerated.map(item => <li key={item}>{item}</li>)}
        </ul>
      </details>
      {data.engineLimitations.length > 0 && (
        <details>
          <summary>Limitações da Engine</summary>
          <ul>
            {data.engineLimitations.map(l => <li key={l}>{l}</li>)}
          </ul>
        </details>
      )}
      <p><strong>{data.question}</strong></p>
      <button onClick={() => onConfirm(true)}>Sim, compilar</button>
      <button onClick={() => onConfirm(false)}>Fazer ajustes</button>
    </div>
  )
}

// CompilationView.tsx
function CompilationView({ status }) {
  return (
    <div className="compilation-phase">
      <h3>🛠️ COMPILANDO JOGO...</h3>
      <ul>
        <li>{status.readingState ? '✅' : '⏳'} Lendo estado atual do jogo...</li>
        <li>{status.buildingPlan ? '✅' : '⏳'} Construindo plano do jogo...</li>
        <li>{status.validating ? '✅' : '⏳'} Validando contra contrato constitucional...</li>
        <li>{status.generating ? '✅' : '⏳'} Gerando código do jogo...</li>
      </ul>
      {status.complete && <p>✅ COMPILAÇÃO CONCLUÍDA</p>}
    </div>
  )
}
```

---

## Fluxo de Implementação Recomendado

### Fase 1: Documentação (✅ Completo)
- ✅ Criar `ORDAX_COMPILER_PROTOCOL_V1.md`
- ✅ Criar `COMPILER_PROTOCOL_IMPLEMENTATION_GUIDE.md`

### Fase 2: Backend (Prompts do AI)
1. Atualizar `systemPrompt()` em `game-ai-chat/index.ts`
2. Atualizar `baseSpecPrompt` em `game-ai-chat-stream/index.ts`
3. Adicionar lógica de fases no backend
4. Adicionar validação de confirmação do usuário

### Fase 3: Frontend (UI)
1. Criar componentes de visualização de fases
2. Adicionar lógica de confirmação
3. Adicionar indicadores de progresso
4. Adicionar mensagens de status

### Fase 4: Testes
1. Testar NEW_GAME com protocolo completo
2. Testar CODE_MUTATION
3. Testar modo COACH
4. Testar validação constitucional

---

## Exemplo de Fluxo Completo

### Usuário: "Crie um jogo de plataforma onde eu pulo e coleto moedas"

### Resposta do AI (Fase 1-4):

```json
{
  "phase": "interpretation",
  "interpretation": {
    "gameType": "platformer",
    "mechanics": [
      "Pular entre plataformas",
      "Coletar moedas"
    ],
    "restrictions": [],
    "objective": "Coletar todas as moedas"
  }
}
```

```json
{
  "phase": "plan",
  "plan": {
    "coreLoop": "Jogador pula entre plataformas e coleta moedas. Jogo termina quando todas as moedas são coletadas.",
    "mechanics": [
      "Movimento horizontal com setas",
      "Pulo com espaço",
      "Coleta de moedas ao tocar"
    ],
    "controls": [
      "Setas Esquerda/Direita: Mover",
      "Espaço: Pular",
      "Enter: Iniciar/Reiniciar"
    ],
    "hud": [
      "Score (moedas coletadas)",
      "Timer"
    ],
    "fsm": {
      "START": "Tela inicial com botão Iniciar",
      "PLAYING": "Gameplay ativo",
      "PAUSED": "Jogo pausado",
      "GAME_OVER": "Tela de fim com score"
    },
    "systems": [
      "PhysicsSystem",
      "CollisionSystem",
      "ScoreSystem",
      "UISystem",
      "TimerSystem",
      "CameraSystem"
    ],
    "lifecycle": {
      "start": "Jogador clica Iniciar",
      "loseCondition": "Timer chega a 0",
      "winCondition": "Todas as moedas coletadas",
      "restart": "Jogador clica Reiniciar",
      "signal": "objective_progress"
    }
  }
}
```

```json
{
  "phase": "validation",
  "validation": {
    "status": "valid",
    "pillarChecklist": {
      "timeManagement": true,
      "fsm": true,
      "uiSystem": true,
      "inputSystem": true,
      "saveSystem": true,
      "viewportManagement": true,
      "gameLoop": true
    },
    "promptValidation": {
      "allMechanicsIncluded": true,
      "restrictionsRespected": true,
      "objectiveImplementable": true
    },
    "autoCompletions": [
      "TimerSystem adicionado (obrigatório para o gênero)",
      "CameraSystem adicionado (obrigatório para o gênero)"
    ],
    "warnings": []
  }
}
```

```json
{
  "phase": "confirmation",
  "confirmation": {
    "summary": "Um jogo de plataforma onde você pula entre plataformas e coleta moedas. O jogo termina quando você coleta todas as moedas ou o tempo acaba.",
    "whatWillBeGenerated": [
      "Jogador com movimento horizontal e pulo",
      "Plataformas fixas",
      "Moedas colecionáveis",
      "Sistema de score",
      "Timer",
      "Telas de início, jogo e fim"
    ],
    "engineLimitations": [
      "Física será básica (sem momentum complexo)"
    ],
    "question": "Este é o jogo que você quer gerar?"
  }
}
```

### Usuário: "sim"

```json
{
  "phase": "compilation",
  "compilationStatus": {
    "readingState": true,
    "buildingPlan": true,
    "validating": true,
    "generating": true,
    "complete": true
  },
  "spec": { ... },
  "assistantSummary": "Jogo de plataforma gerado com sucesso...",
  "appliedEdits": [...],
  "semanticPatch": {...},
  "report": {...}
}
```

---

## Benefícios da Implementação

### 1. Transparência
- Usuário vê exatamente o que será gerado
- Usuário pode corrigir antes da compilação
- Sem surpresas ou "jogo pronto" incompleto

### 2. Determinismo
- Mesma entrada → mesma saída
- Protocolo rígido elimina variabilidade
- Validação automática garante qualidade

### 3. Confiabilidade
- AI não pode "fingir" que fez algo
- AI não pode sugerir "adicionar depois"
- AI não pode ignorar mecânicas solicitadas

### 4. Inteligência Aparente
- Chat parece mais inteligente e profissional
- Respostas estruturadas e organizadas
- Feedback claro e acionável

---

## Status de Implementação

### ✅ Completo
- Documentação do protocolo
- Guia de implementação
- Exemplos completos

### ⏳ Pendente
- Atualização dos prompts do AI
- Implementação da lógica de fases no backend
- Componentes de UI no frontend
- Testes end-to-end

---

## Próximos Passos

1. **Atualizar Prompts do AI** (Backend)
   - Modificar `systemPrompt()` em `game-ai-chat/index.ts`
   - Modificar `baseSpecPrompt` em `game-ai-chat-stream/index.ts`
   - Adicionar lógica de fases

2. **Implementar UI de Fases** (Frontend)
   - Criar componentes de visualização
   - Adicionar lógica de confirmação
   - Adicionar indicadores de progresso

3. **Testar Protocolo**
   - Testar NEW_GAME
   - Testar CODE_MUTATION
   - Testar validação

---

## Assinatura

```
ORDAX COMPILER PROTOCOL IMPLEMENTATION GUIDE
Versão: 1.0.0
Data: 2026-01-25
Status: GUIA DE IMPLEMENTAÇÃO
```

**Este guia define como implementar o protocolo do compilador de jogos da Ordax.**
