# Patch de Integração Frontend - Compiler Protocol

## MUDANÇAS NECESSÁRIAS NO StudioChatPanel.tsx

### 1. Estado já adicionado ✅
```typescript
// Compiler Protocol State
const [compilerPhase, setCompilerPhase] = useState<CompilerPhase>("interpretation");
const [compilerResponses, setCompilerResponses] = useState<CompilerResponse[]>([]);
const [sessionId, setSessionId] = useState<string | null>(null);
```

### 2. Função handleApprove já adicionada ✅
```typescript
const handleApprove = async () => {
  const lastResponse = compilerResponses[compilerResponses.length - 1];
  if (!lastResponse || lastResponse.kind !== "CONFIRMATION_REQUIRED") return;
  // ... implementação completa
};
```

### 3. Reset de estado no send() já adicionado ✅
```typescript
// Reset compiler state para novo jogo
if (!isEditMode) {
  setCompilerResponses([]);
  setCompilerPhase("interpretation");
  setSessionId(null);
}
```

### 4. FALTA: Detecção de respostas estruturadas

No bloco NEW_GAME (linha ~460), ADICIONAR após `if (error)`:

```typescript
// Detectar resposta estruturada do compilador
const responseKind = (data as any)?.kind;

if (responseKind) {
  // Resposta estruturada do protocolo do compilador
  const compilerResponse = data as CompilerResponse;
  
  // Atualizar fase e sessionId
  if (compilerResponse.phase) {
    setCompilerPhase(compilerResponse.phase);
  }
  if (compilerResponse.sessionId) {
    setSessionId(compilerResponse.sessionId);
  }

  // Adicionar resposta estruturada
  setCompilerResponses(prev => [...prev, compilerResponse]);

  // Se for CONFIRMATION_REQUIRED, parar aqui
  if (responseKind === "CONFIRMATION_REQUIRED") {
    setStage("awaiting_accept");
    return;
  }

  // Se for fase intermediária, continuar automaticamente
  if (responseKind === "INTERPRETATION_RESULT" || 
      responseKind === "GAME_PLAN_RESULT" || 
      responseKind === "VALIDATION_RESULT") {
    setTimeout(() => void send("continue"), 500);
    return;
  }

  return;
}

// Fallback para formato antigo (manter código existente)
```

### 5. FALTA: Renderizar respostas estruturadas

Na seção de mensagens (linha ~1100), ADICIONAR antes de `{messages.map(...)}`:

```typescript
{/* Respostas estruturadas do compilador */}
{compilerResponses.map((response, idx) => (
  <div key={`compiler-${idx}`} className="animate-fade-in mb-3">
    <CompilerPhaseRenderer
      response={response}
      onApprove={response.kind === "CONFIRMATION_REQUIRED" ? handleApprove : undefined}
      approving={isLoading}
    />
  </div>
))}
```

### 6. FALTA: Badge de fase no header

No header (linha ~1000), ADICIONAR após Badge "Online":

```typescript
{!isEditMode && sessionId && (
  <CompilerPhaseBadge phase={compilerPhase} />
)}
```

## RESULTADO ESPERADO

Quando usuário pede novo jogo:
1. Aparece badge "1/5: Interpretação"
2. Aparece card estruturado com interpretação
3. Avança automaticamente para "2/5: Plano"
4. Aparece card estruturado com plano
5. Avança automaticamente para "3/5: Validação"
6. Aparece card estruturado com validação
7. Avança automaticamente para "4/5: Confirmação"
8. Aparece card com botão "✅ Aceitar plano e compilar"
9. Usuário clica no botão
10. Badge muda para "5/5: Compilação"
11. Jogo é gerado

## TESTE RÁPIDO

```bash
# 1. Abrir Ordax Studio
# 2. Pedir: "Crie um jogo de plataforma com moedas"
# 3. Verificar se badges e cards aparecem
# 4. Clicar no botão de aprovação
# 5. Verificar se jogo é gerado
```
