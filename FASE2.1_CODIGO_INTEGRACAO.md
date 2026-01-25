# 🔌 FASE 2.1 - CÓDIGO DE INTEGRAÇÃO

## 📝 Modificações no game-ai-chat-stream/index.ts

### 1. Adicionar Import no Topo do Arquivo

```typescript
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { CompilerSessionStore } from "../_shared/compiler-session-store.ts";
// 🆕 ADICIONAR ESTA LINHA
import { validateRuntimeAgainstProfile, formatProfileViolations } from "../_shared/runtime-profile-validator.ts";
```

---

### 2. Adicionar Validação de Perfil (Após Resposta da IA)

**Localização:** Após o bloco `if (resolvedMode === "code_patch")` e antes de `return new Response(response.body, ...)`

**Código a adicionar:**

```typescript
    // code_patch: validate on server and return as SSE (single chunk) for client compatibility.
    if (resolvedMode === "code_patch") {
      const gatewayPayload = (await response.json()) as any;
      const text = gatewayPayload?.choices?.[0]?.message?.content as string | undefined;
      const cleaned = (text ?? "").replace(/^```[a-zA-Z]*\n?/, "").replace(/\n?```$/, "").trim();

      let outText = cleaned;
      try {
        const parsed = JSON.parse(cleaned);
        if (!parsed?.error) {
          validateCodeSemanticPatchOrThrow(parsed?.patch, String(targetGameId ?? ""));
        }
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        outText = JSON.stringify({
          error: "COMPILER_ERROR",
          message: `Patch rejeitado pelo backend: ${msg}`,
          engineLimitationsHit: ["mutation_guide_violation"],
        });
      }

      return new Response(toSseFromFullText(outText), {
        headers: { ...corsHeaders, "Content-Type": "text/event-stream" },
      });
    }

    // ============================================================================
    // 🆕 PROFILE VALIDATION (SPEC MODE)
    // ============================================================================
    
    if (resolvedMode === "spec") {
      // Para spec mode, precisamos interceptar o stream, validar e retornar
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      const encoder = new TextEncoder();
      
      let accumulated = "";
      
      const stream = new ReadableStream({
        async start(controller) {
          try {
            while (true) {
              const { done, value } = await reader!.read();
              
              if (done) {
                // Stream completo - validar agora
                try {
                  // Extrair JSON do SSE
                  const lines = accumulated.split('\n');
                  let fullContent = "";
                  
                  for (const line of lines) {
                    if (line.startsWith('data: ') && !line.includes('[DONE]')) {
                      const data = line.slice(6);
                      try {
                        const parsed = JSON.parse(data);
                        const content = parsed?.choices?.[0]?.delta?.content || "";
                        fullContent += content;
                      } catch (e) {
                        // Ignorar linhas que não são JSON válido
                      }
                    }
                  }
                  
                  // Limpar markdown
                  const cleaned = fullContent.replace(/^```[a-zA-Z]*\n?/, "").replace(/\n?```$/, "").trim();
                  
                  if (cleaned) {
                    const parsed = JSON.parse(cleaned);
                    const spec = parsed?.spec;
                    
                    if (spec && !parsed?.error) {
                      // 🆕 VALIDAR PERFIL
                      console.log("🔍 Validating runtime profile...");
                      const profileResult = validateRuntimeAgainstProfile(spec);
                      
                      if (!profileResult.isValid) {
                        console.warn("⚠️ Profile validation failed:");
                        console.warn(formatProfileViolations(profileResult));
                        
                        // Adicionar violações ao response
                        parsed.profileValidation = {
                          isValid: false,
                          violations: profileResult.violations,
                          missingElements: profileResult.missingElements,
                          summary: profileResult.summary,
                          genre: profileResult.genre
                        };
                        
                        // Se houver violações críticas, adicionar aviso
                        if (profileResult.summary.critical > 0) {
                          if (!parsed.report) parsed.report = {};
                          if (!parsed.report.engineLimitationsHit) {
                            parsed.report.engineLimitationsHit = [];
                          }
                          parsed.report.engineLimitationsHit.push(
                            `PROFILE_VALIDATION: ${profileResult.summary.critical} violações críticas detectadas`
                          );
                          
                          // Adicionar warning ao assistantSummary
                          if (parsed.assistantSummary) {
                            parsed.assistantSummary += `\n\n⚠️ AVISO: Runtime incompleto. Faltam ${profileResult.summary.critical} elementos críticos.`;
                          }
                        }
                      } else {
                        console.log("✅ Profile validation passed");
                        parsed.profileValidation = {
                          isValid: true,
                          genre: profileResult.genre
                        };
                      }
                      
                      // Recriar SSE com JSON modificado
                      const modifiedContent = JSON.stringify(parsed);
                      const ssePayload = JSON.stringify({ 
                        choices: [{ delta: { content: modifiedContent } }] 
                      });
                      controller.enqueue(encoder.encode(`data: ${ssePayload}\n\n`));
                    } else {
                      // Passar conteúdo original se não houver spec
                      controller.enqueue(encoder.encode(accumulated));
                    }
                  } else {
                    // Passar conteúdo original se não conseguir parsear
                    controller.enqueue(encoder.encode(accumulated));
                  }
                } catch (e) {
                  console.error("Error validating profile:", e);
                  // Em caso de erro, passar conteúdo original
                  controller.enqueue(encoder.encode(accumulated));
                }
                
                controller.enqueue(encoder.encode(`data: [DONE]\n\n`));
                controller.close();
                break;
              }
              
              // Acumular chunks
              const chunk = decoder.decode(value, { stream: true });
              accumulated += chunk;
              
              // Passar chunk original para o cliente (streaming em tempo real)
              controller.enqueue(value);
            }
          } catch (error) {
            console.error("Stream error:", error);
            controller.error(error);
          }
        }
      });
      
      return new Response(stream, {
        headers: { ...corsHeaders, "Content-Type": "text/event-stream" },
      });
    }

    // spec: pass-through streaming SSE response (fallback se não for spec nem code_patch).
    return new Response(response.body, {
      headers: { ...corsHeaders, "Content-Type": "text/event-stream" },
    });
```

---

## 🎯 O que o Código Faz

### Fluxo de Validação

1. **Intercepta o stream SSE** da resposta da IA
2. **Acumula todos os chunks** até o stream terminar
3. **Extrai o JSON** do formato SSE
4. **Valida o runtimeSpec** contra o perfil do gênero
5. **Adiciona `profileValidation`** ao response
6. **Modifica o SSE** com o JSON atualizado
7. **Retorna ao frontend** com informações de validação

### Estrutura do Response Modificado

```typescript
{
  "spec": { ... },
  "assistantSummary": "...",
  "appliedEdits": [ ... ],
  "report": {
    "whatWasRequested": "...",
    "whatWasApplied": [ ... ],
    "whatCouldNotBeAppliedAndWhy": [ ... ],
    "engineLimitationsHit": [
      "PROFILE_VALIDATION: 4 violações críticas detectadas" // 🆕 ADICIONADO
    ]
  },
  "profileValidation": { // 🆕 ADICIONADO
    "isValid": false,
    "violations": [
      {
        "id": "SYS_COLLISIONSYSTEM",
        "level": "CRITICAL",
        "category": "system",
        "message": "Sistema obrigatório ausente: CollisionSystem",
        "expected": "CollisionSystem",
        "actual": "não encontrado",
        "fix": "Adicionar CollisionSystem à lista de sistemas"
      }
    ],
    "missingElements": {
      "systems": ["CollisionSystem", "AISystem"],
      "entities": ["enemy", "bullet"],
      "components": {
        "player": ["Health", "Weapon"]
      },
      "uiElements": [],
      "controls": [],
      "signals": []
    },
    "summary": {
      "critical": 4,
      "severe": 2,
      "minor": 0
    },
    "genre": "topdown-shooter-survival"
  }
}
```

---

## 🚀 Alternativa Simplificada (Sem Streaming)

Se preferir uma implementação mais simples (sem interceptar stream):

```typescript
    // spec: pass-through streaming SSE response.
    // 🆕 NOTA: Para validação de perfil, considere usar mode não-streaming
    // ou implementar validação no frontend após receber resposta completa
    return new Response(response.body, {
      headers: { ...corsHeaders, "Content-Type": "text/event-stream" },
    });
```

E adicionar validação no **frontend** após receber resposta:

```typescript
// src/components/ordax/StudioChatPanel.tsx

const handleStreamComplete = (fullResponse: any) => {
  if (fullResponse.spec) {
    const profileResult = validateRuntimeAgainstProfile(
      fullResponse.spec,
      TOPDOWN_SHOOTER_PROFILE
    );
    
    if (!profileResult.isValid) {
      toast.warning(
        `Runtime incompleto: ${profileResult.summary.critical} violações críticas`
      );
      
      // Mostrar painel de validação
      setValidationResult(profileResult);
    }
  }
};
```

---

## 🧪 Testar

### 1. Deploy da Função

```bash
supabase functions deploy game-ai-chat-stream
```

### 2. Testar com Curl

```bash
curl -X POST https://your-project.supabase.co/functions/v1/game-ai-chat-stream \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Crie um top-down shooter simples"}],
    "mode": "spec",
    "approvedPlan": {
      "gameType": "topdown",
      "title": "Test Shooter",
      "requiredSystems": ["PhysicsSystem"],
      "requiredEntities": ["player"]
    }
  }'
```

### 3. Verificar Logs

```bash
supabase functions logs game-ai-chat-stream --tail
```

Procure por:
- `🔍 Validating runtime profile...`
- `✅ Profile validation passed` ou `⚠️ Profile validation failed`

---

## 📊 Impacto

### Antes
- ❌ IA gera runtime incompleto
- ❌ Frontend não sabe o que falta
- ❌ Jogo não funciona

### Depois
- ✅ Validação automática no backend
- ✅ Frontend recebe lista de violações
- ✅ Usuário sabe exatamente o que falta
- ✅ Possibilidade de correção automática

---

## 🎯 Próximos Passos

1. **Implementar o código** no `game-ai-chat-stream/index.ts`
2. **Deploy e testar** com curl
3. **Atualizar frontend** para exibir `profileValidation`
4. **Implementar correção automática** (loop de 3 tentativas)
5. **Adicionar métricas** de validação

---

**Status:** ✅ Código pronto para implementação  
**Arquivo:** `supabase/functions/game-ai-chat-stream/index.ts`  
**Linhas a modificar:** ~50 linhas adicionadas
