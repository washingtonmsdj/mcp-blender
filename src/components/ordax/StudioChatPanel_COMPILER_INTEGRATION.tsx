/**
 * INSTRUÇÕES DE INTEGRAÇÃO DO COMPILER PROTOCOL
 * 
 * Este arquivo contém as funções modificadas que devem substituir as originais
 * em StudioChatPanel.tsx para integrar o protocolo do compilador.
 */

// ============================================================================
// 1. ADICIONAR FUNÇÃO handleApprove (após a função send)
// ============================================================================

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
      setStage("idle");
      return;
    }

    // Após aprovação, gerar o jogo
    await generateSpecStreaming(messages, undefined, lastResponse.plan);
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    toast.error(`Erro: ${msg}`);
    setIsLoading(false);
    setStage("idle");
  }
};

// ============================================================================
// 2. MODIFICAR A FUNÇÃO send - ADICIONAR NO INÍCIO
// ============================================================================

// Logo após: const trimmed = text.trim();
// ADICIONAR:

// Reset compiler state para novo jogo
if (!isEditMode && trimmed !== "continue") {
  setCompilerResponses([]);
  setCompilerPhase("interpretation");
  setSessionId(null);
}

// ============================================================================
// 3. MODIFICAR A CHAMADA DO BACKEND - SUBSTITUIR
// ============================================================================

// SUBSTITUIR:
// const { data, error } = await supabase.functions.invoke("game-ai-chat", {
//   body: {
//     mode: "spec",
//     phase: "plan",
//     messages: [...messages, userMessage],
//   },
// });

// POR:
const { data, error } = await supabase.functions.invoke("game-ai-chat", {
  body: {
    mode: "spec",
    messages: [...messages, userMessage],
    userId: "user-" + Date.now(),
    sessionId: sessionId || undefined,
  },
});

// ============================================================================
// 4. ADICIONAR DETECÇÃO DE RESPOSTAS ESTRUTURADAS - APÓS setIsLoading(false)
// ============================================================================

// ADICIONAR APÓS: setIsLoading(false);

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

  // Se for CONFIRMATION_REQUIRED, parar e aguardar aprovação
  if (responseKind === "CONFIRMATION_REQUIRED") {
    setStage("awaiting_accept");
    return;
  }

  // Se for COMPILER_PROTOCOL_VIOLATION, mostrar erro e parar
  if (responseKind === "COMPILER_PROTOCOL_VIOLATION") {
    setStage("idle");
    toast.error("Violação de protocolo do compilador");
    return;
  }

  // Se for INTERPRETATION_RESULT, GAME_PLAN_RESULT ou VALIDATION_RESULT,
  // continuar automaticamente para próxima fase
  if (responseKind === "INTERPRETATION_RESULT" || 
      responseKind === "GAME_PLAN_RESULT" || 
      responseKind === "VALIDATION_RESULT") {
    setStage("idle");
    // Continuar para próxima fase automaticamente
    setTimeout(() => {
      void send("continue");
    }, 500);
    return;
  }

  setStage("idle");
  return;
}

// Fallback para formato antigo (legacy) - manter código existente abaixo

// ============================================================================
// 5. RENDERIZAR RESPOSTAS ESTRUTURADAS - NA SEÇÃO DE MENSAGENS
// ============================================================================

// ENCONTRAR:
// <div className="space-y-3">
//   {messages.map((m, idx) => (

// ADICIONAR ANTES DO {messages.map(...)}:

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

// ============================================================================
// 6. ADICIONAR BADGE DE FASE NO HEADER
// ============================================================================

// ENCONTRAR:
// <div className="flex items-center gap-2">
//   <Sparkles className="h-4 w-4 text-primary" />
//   <span className="font-semibold text-sm">Ordax AI</span>
//   <Badge variant="outline" ...>
//     Online
//   </Badge>
// </div>

// ADICIONAR APÓS O BADGE "Online":

{!isEditMode && sessionId && (
  <CompilerPhaseBadge phase={compilerPhase} />
)}

// ============================================================================
// 7. DESABILITAR INPUT DURANTE CONFIRMAÇÃO/COMPILAÇÃO
// ============================================================================

// ENCONTRAR:
// <Textarea
//   value={input}
//   onChange={(e) => setInput(e.target.value)}
//   placeholder={placeholder}
//   ...
// />

// MODIFICAR PARA:
<Textarea
  value={input}
  onChange={(e) => setInput(e.target.value)}
  placeholder={placeholder}
  disabled={
    isLoading || 
    isStreaming || 
    (!isEditMode && (compilerPhase === "confirmation" || compilerPhase === "compilation"))
  }
  className={cn(
    "min-h-[80px] max-h-[120px] resize-none bg-background border-border/50 text-xs",
    (!isEditMode && (compilerPhase === "confirmation" || compilerPhase === "compilation")) && "opacity-50 cursor-not-allowed"
  )}
  onKeyDown={(e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      void send(input);
    }
  }}
/>

// ============================================================================
// 8. DESABILITAR BOTÃO SEND DURANTE CONFIRMAÇÃO/COMPILAÇÃO
// ============================================================================

// ENCONTRAR:
// <Button
//   size="icon"
//   className="h-auto shrink-0 self-end neon-glow"
//   onClick={() => void send(input)}
//   disabled={isLoading || !input.trim()}
// >

// MODIFICAR PARA:
<Button
  size="icon"
  className="h-auto shrink-0 self-end neon-glow"
  onClick={() => void send(input)}
  disabled={
    isLoading || 
    !input.trim() || 
    (!isEditMode && (compilerPhase === "confirmation" || compilerPhase === "compilation"))
  }
>

// ============================================================================
// FIM DAS MODIFICAÇÕES
// ============================================================================
