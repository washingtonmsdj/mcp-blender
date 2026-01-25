# Guia de Integração Frontend - Compiler Protocol

**Tempo estimado:** 30 minutos  
**Arquivo:** `src/components/ordax/StudioChatPanel.tsx`

---

## PASSO 1: Adicionar Import (linha ~30)

```typescript
import { CompilerPhaseRenderer, CompilerPhaseBadge, type CompilerResponse, type CompilerPhase } from "@/components/ordax/CompilerPhaseRenderer";
```

---

## PASSO 2: Adicionar Estado (após linha ~250)

```typescript
// Compiler Protocol State
const [compilerPhase, setCompilerPhase] = useState<CompilerPhase>("interpretation");
const [compilerResponses, setCompilerResponses] = useState<CompilerResponse[]>([]);
const [sessionId, setSessionId] = useState<string | null>(null);
```

---

## PASSO 3: Modificar função `send()` (linha ~400)

Encontre este bloco:
```typescript
const { data, error } = await supabase.functions.invoke("game-ai-chat", {
  body: {
    mode: "spec",
    phase: "plan",
    messages: [...messages, userMessage],
  },
});
```

Substitua por:
```typescript
const { data, error } = await supabase.functions.invoke("game-ai-chat", {
  body: {
    mode: "spec",
    phase: "plan",
    messages: [...messages, userMessage],
    userId: "user-" + Date.now(), // Temporary user ID
  },
});

setIsLoading(false);

if (error) {
  toast.error(`Erro: ${error.message}`);
  return;
}

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

  // Se for CONFIRMATION_REQUIRED, parar aqui (usuário precisa aprovar)
  if (responseKind === "CONFIRMATION_REQUIRED") {
    setStage("awaiting_accept");
    return;
  }

  // Se for INTERPRETATION_RESULT, GAME_PLAN_RESULT ou VALIDATION_RESULT,
  // continuar automaticamente para próxima fase
  if (responseKind === "INTERPRETATION_RESULT" || 
      responseKind === "GAME_PLAN_RESULT" || 
      responseKind === "VALIDATION_RESULT") {
    // Continuar para próxima fase automaticamente
    setTimeout(() => {
      void send("continue"); // Trigger próxima fase
    }, 500);
    return;
  }

  return;
}

// Fallback para formato antigo (legacy) - manter código existente abaixo
```

---

## PASSO 4: Adicionar função `handleApprove()` (após função `send()`)

```typescript
const handleApprove = async () => {
  const lastResponse = compilerResponses[compilerResponses.length - 1];
  if (!lastResponse || lastResponse.kind !== "CONFIRMATION_REQUIRED") return;

  setIsLoading(true);
  setStage("generating");

  try {
    const { data, error } = await supabase.functions.invoke("game-ai-chat", {
      body: {
        action: "APPROVE_PLAN",
        sessionId,
        userId: "user-" + Date.now(),
        messages,
      },
    });

    if (error) {
      toast.error(`Erro: ${error.message}`);
      setIsLoading(false);
      return;
    }

    // Após aprovação, gerar o jogo
    await generateSpecStreaming(messages, undefined, lastResponse.plan);
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    toast.error(`Erro: ${msg}`);
    setIsLoading(false);
  }
};
```

---

## PASSO 5: Renderizar respostas estruturadas (na seção de mensagens, linha ~1100)

Encontre este bloco:
```typescript
<div className="space-y-3">
  {messages.map((m, idx) => (
    // ... renderização de mensagens
  ))}
</div>
```

Adicione ANTES do `{messages.map(...)}`:
```typescript
{/* Respostas estruturadas do compilador */}
{compilerResponses.map((response, idx) => (
  <div key={`compiler-${idx}`} className="animate-fade-in">
    <CompilerPhaseRenderer
      response={response}
      onApprove={response.kind === "CONFIRMATION_REQUIRED" ? handleApprove : undefined}
      approving={isLoading}
    />
  </div>
))}
```

---

## PASSO 6: Adicionar badge de fase no header (linha ~1000)

Encontre este bloco:
```typescript
<div className="flex items-center gap-2">
  <Sparkles className="h-4 w-4 text-primary" />
  <span className="font-semibold text-sm">Ordax AI</span>
  <Badge variant="outline" className="border-neon-green/30 bg-neon-green/10 text-neon-green text-[10px] h-5">
    <span className="w-1 h-1 rounded-full bg-neon-green mr-1 animate-pulse"></span>
    Online
  </Badge>
</div>
```

Adicione após o Badge "Online":
```typescript
{!isEditMode && sessionId && (
  <CompilerPhaseBadge phase={compilerPhase} />
)}
```

---

## PASSO 7: Resetar estado ao criar novo jogo (início da função `send()`)

Adicione no início da função `send()`:
```typescript
// Reset compiler state para novo jogo
if (!isEditMode) {
  setCompilerResponses([]);
  setCompilerPhase("interpretation");
  setSessionId(null);
}
```

---

## TESTE

1. Abra Ordax Studio
2. Peça um novo jogo: "Crie um jogo de plataforma com moedas"
3. Verifique se aparece:
   - Badge de fase no header (1/5, 2/5, etc.)
   - Resposta estruturada de interpretação
   - Resposta estruturada de plano
   - Resposta estruturada de validação
   - Botão "✅ Aceitar plano e compilar"
4. Clique no botão
5. Verifique se o jogo é gerado

---

## TROUBLESHOOTING

### Problema: Respostas não aparecem estruturadas
**Solução:** Verificar se backend está retornando `kind` no response

### Problema: Botão de aprovação não funciona
**Solução:** Verificar se `sessionId` está sendo setado corretamente

### Problema: Fases não avançam automaticamente
**Solução:** Verificar se `setTimeout(() => void send("continue"), 500)` está sendo chamado

### Problema: Badge de fase não aparece
**Solução:** Verificar se `!isEditMode && sessionId` está true

---

## CHECKLIST

- [ ] Import adicionado
- [ ] Estado adicionado
- [ ] Função `send()` modificada
- [ ] Função `handleApprove()` adicionada
- [ ] Renderização de respostas estruturadas adicionada
- [ ] Badge de fase adicionado no header
- [ ] Reset de estado adicionado
- [ ] Testado fluxo completo

---

**Tempo total:** ~30 minutos  
**Dificuldade:** Média  
**Impacto:** Alto - Torna o protocolo visível ao usuário
