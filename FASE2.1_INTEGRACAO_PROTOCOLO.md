# 🔌 FASE 2.1 - INTEGRAÇÃO COM PROTOCOLO

## 🎯 Objetivo

Integrar o **validador de perfil** no fluxo de compilação para que a IA receba feedback estruturado sobre o que falta no runtime e possa corrigir automaticamente.

---

## 📦 Arquivos Criados

### 1. Validador para Deno
**Arquivo:** `supabase/functions/_shared/runtime-profile-validator.ts`

Versão adaptada do validador de perfil para uso em Deno Edge Functions (Supabase).

**Exports:**
- `validateRuntimeAgainstProfile()` - Valida runtime contra perfil
- `formatProfileViolations()` - Formata violações para log
- `ProfileValidationResult` - Interface do resultado
- `ProfileViolation` - Interface de violação

**Diferenças da versão frontend:**
- ✅ Sem imports externos (tudo inline)
- ✅ Compatível com Deno
- ✅ Apenas perfil top-down shooter (por enquanto)
- ✅ Validação automática por gameType

---

## 🔄 Fluxo de Integração

### Antes (Sem Validação de Perfil)

```
User Prompt
    ↓
AI gera runtimeSpec
    ↓
Constitutional Validation (pilares gerais)
    ↓
Retorna para frontend
    ↓
Frontend renderiza
```

**Problema:** IA pode gerar runtime incompleto (faltando entidades, componentes, etc.)

---

### Depois (Com Validação de Perfil)

```
User Prompt
    ↓
AI gera runtimeSpec
    ↓
Constitutional Validation (pilares gerais)
    ↓
🆕 Profile Validation (gênero específico)
    ↓
    ├─ Se válido → Retorna para frontend ✅
    │
    └─ Se inválido → Gera feedback estruturado
           ↓
       AI corrige automaticamente
           ↓
       Valida novamente (loop até 3x)
           ↓
       Retorna para frontend
```

**Benefício:** Garante que runtime está completo antes de retornar ao frontend

---

## 🛠️ Como Integrar

### Opção 1: Validação Pós-Geração (Recomendado)

Adicionar validação após a IA gerar o runtimeSpec, mas antes de retornar ao frontend.

**Arquivo:** `supabase/functions/game-ai-chat-stream/index.ts`

**Localização:** Após receber resposta da IA, antes de retornar stream

```typescript
import { validateRuntimeAgainstProfile, formatProfileViolations } from "../_shared/runtime-profile-validator.ts";

// ... após receber resposta da IA

// Parsear resposta
const parsed = JSON.parse(cleaned);
const spec = parsed?.spec;

if (spec && !parsed?.error) {
  // 🆕 VALIDAR PERFIL
  const profileResult = validateRuntimeAgainstProfile(spec);
  
  if (!profileResult.isValid) {
    console.warn("⚠️ Profile validation failed:", formatProfileViolations(profileResult));
    
    // Adicionar violações ao response
    parsed.profileValidation = {
      isValid: false,
      violations: profileResult.violations,
      missingElements: profileResult.missingElements,
      summary: profileResult.summary
    };
    
    // Opcional: Bloquear se houver violações críticas
    if (profileResult.summary.critical > 0) {
      parsed.error = "PROFILE_VALIDATION_FAILED";
      parsed.message = `Runtime incompleto: ${profileResult.summary.critical} violações críticas`;
    }
  } else {
    console.log("✅ Profile validation passed");
    parsed.profileValidation = {
      isValid: true,
      genre: profileResult.genre
    };
  }
}

// Retornar resposta modificada
outText = JSON.stringify(parsed);
```

---

### Opção 2: Validação com Correção Automática (Avançado)

Loop de correção automática: se runtime inválido, gera novo prompt para IA corrigir.

```typescript
import { validateRuntimeAgainstProfile, formatProfileViolations } from "../_shared/runtime-profile-validator.ts";

// ... após receber resposta da IA

let parsed = JSON.parse(cleaned);
let spec = parsed?.spec;
let attempts = 0;
const MAX_ATTEMPTS = 3;

while (spec && !parsed?.error && attempts < MAX_ATTEMPTS) {
  // Validar perfil
  const profileResult = validateRuntimeAgainstProfile(spec);
  
  if (profileResult.isValid) {
    console.log("✅ Profile validation passed");
    parsed.profileValidation = {
      isValid: true,
      genre: profileResult.genre
    };
    break;
  }
  
  // Se inválido e ainda há tentativas
  attempts++;
  console.warn(`⚠️ Profile validation failed (attempt ${attempts}/${MAX_ATTEMPTS})`);
  console.warn(formatProfileViolations(profileResult));
  
  if (attempts >= MAX_ATTEMPTS) {
    // Máximo de tentativas atingido
    parsed.profileValidation = {
      isValid: false,
      violations: profileResult.violations,
      missingElements: profileResult.missingElements,
      summary: profileResult.summary,
      attempts
    };
    parsed.error = "PROFILE_VALIDATION_FAILED";
    parsed.message = `Runtime incompleto após ${attempts} tentativas: ${profileResult.summary.critical} violações críticas`;
    break;
  }
  
  // Gerar prompt de correção
  const correctionPrompt = generateCorrectionPrompt(profileResult);
  
  // Chamar IA novamente para corrigir
  const correctionResponse = await fetch("https://ai.gateway.lovable.dev/v1/chat/completions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${LOVABLE_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: "google/gemini-3-flash-preview",
      messages: [
        { role: "system", content: systemPrompt },
        { role: "assistant", content: JSON.stringify(parsed) },
        { role: "user", content: correctionPrompt }
      ],
      temperature: 0.2,
      stream: false,
    }),
  });
  
  const correctionPayload = await correctionResponse.json();
  const correctionText = correctionPayload?.choices?.[0]?.message?.content;
  const correctionCleaned = (correctionText ?? "").replace(/^```[a-zA-Z]*\n?/, "").replace(/\n?```$/, "").trim();
  
  parsed = JSON.parse(correctionCleaned);
  spec = parsed?.spec;
}

// Retornar resposta final
outText = JSON.stringify(parsed);
```

**Helper: Gerar Prompt de Correção**

```typescript
function generateCorrectionPrompt(profileResult: ProfileValidationResult): string {
  let prompt = `⚠️ VALIDAÇÃO DE PERFIL FALHOU\n\n`;
  prompt += `Seu runtime está incompleto para o gênero '${profileResult.genre}'.\n\n`;
  
  prompt += `**Violações Críticas (${profileResult.summary.critical}):**\n`;
  profileResult.violations
    .filter(v => v.level === 'CRITICAL')
    .forEach(v => {
      prompt += `- [${v.id}] ${v.message}\n`;
      prompt += `  Fix: ${v.fix}\n`;
    });
  
  prompt += `\n**Elementos Faltantes:**\n`;
  
  if (profileResult.missingElements.systems.length > 0) {
    prompt += `- Sistemas: ${profileResult.missingElements.systems.join(', ')}\n`;
  }
  
  if (profileResult.missingElements.entities.length > 0) {
    prompt += `- Entidades: ${profileResult.missingElements.entities.join(', ')}\n`;
  }
  
  if (Object.keys(profileResult.missingElements.components).length > 0) {
    prompt += `- Componentes:\n`;
    for (const [entity, components] of Object.entries(profileResult.missingElements.components)) {
      prompt += `  - ${entity}: ${components.join(', ')}\n`;
    }
  }
  
  if (profileResult.missingElements.uiElements.length > 0) {
    prompt += `- UI: ${profileResult.missingElements.uiElements.join(', ')}\n`;
  }
  
  if (profileResult.missingElements.controls.length > 0) {
    prompt += `- Controles: ${profileResult.missingElements.controls.join(', ')}\n`;
  }
  
  if (profileResult.missingElements.signals.length > 0) {
    prompt += `- Sinais: ${profileResult.missingElements.signals.join(', ')}\n`;
  }
  
  prompt += `\n**AÇÃO REQUERIDA:**\n`;
  prompt += `Corrija TODAS as violações CRÍTICAS acima.\n`;
  prompt += `Retorne o JSON COMPLETO atualizado com todos os elementos faltantes.\n`;
  prompt += `NÃO remova nada que já existe, apenas ADICIONE o que falta.\n`;
  
  return prompt;
}
```

---

### Opção 3: Validação no Frontend (Alternativa)

Se preferir validar no frontend antes de enviar para compilação.

**Arquivo:** `src/components/ordax/StudioChatPanel.tsx`

```typescript
import { validateRuntimeAgainstProfile, formatProfileViolations } from '@/lib/ordax/runtime-profiles';

// ... antes de enviar mensagem

const handleSendMessage = async () => {
  // ... código existente
  
  // Se houver spec atual, validar antes de enviar
  if (currentSpec) {
    const profileResult = validateRuntimeAgainstProfile(currentSpec, TOPDOWN_SHOOTER_PROFILE);
    
    if (!profileResult.isValid && profileResult.summary.critical > 0) {
      // Mostrar aviso ao usuário
      toast.warning(
        `Runtime incompleto: ${profileResult.summary.critical} violações críticas. ` +
        `Enviando para IA corrigir...`
      );
      
      // Adicionar contexto de correção à mensagem
      const correctionContext = generateCorrectionPrompt(profileResult);
      message = `${message}\n\n${correctionContext}`;
    }
  }
  
  // Enviar mensagem
  // ...
};
```

---

## 📊 Exemplo de Resposta com Validação

### Runtime Válido ✅

```json
{
  "spec": { ... },
  "assistantSummary": "Jogo completo implementado",
  "appliedEdits": [ ... ],
  "profileValidation": {
    "isValid": true,
    "genre": "topdown-shooter-survival"
  }
}
```

### Runtime Inválido ❌

```json
{
  "spec": { ... },
  "assistantSummary": "Jogo parcialmente implementado",
  "appliedEdits": [ ... ],
  "profileValidation": {
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
      },
      {
        "id": "ENT_ENEMY",
        "level": "CRITICAL",
        "category": "entity",
        "message": "Entidade obrigatória ausente: enemy",
        "expected": "Pelo menos 1 entidade do tipo 'enemy'",
        "actual": "0 entidades encontradas",
        "fix": "Adicionar entidade do tipo 'enemy' à scene.entities"
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
    }
  },
  "error": "PROFILE_VALIDATION_FAILED",
  "message": "Runtime incompleto: 4 violações críticas"
}
```

---

## 🎯 Benefícios

### Antes
- ❌ IA gera runtime incompleto
- ❌ Usuário não sabe o que falta
- ❌ Jogo não funciona
- ❌ Feedback genérico

### Depois
- ✅ Validação automática de completude
- ✅ Feedback estruturado e específico
- ✅ IA corrige automaticamente
- ✅ Garantia de runtime funcional

---

## 🧪 Testar

### 1. Testar Validador Isolado

```typescript
// Deno REPL ou teste local
import { validateRuntimeAgainstProfile } from "./supabase/functions/_shared/runtime-profile-validator.ts";

const testSpec = {
  gameType: "topdown",
  title: "Test",
  description: "Test",
  systems: ["PhysicsSystem"],
  scene: {
    gravity: { x: 0, y: 0 },
    entities: []
  }
};

const result = validateRuntimeAgainstProfile(testSpec);
console.log("Valid?", result.isValid);
console.log("Critical:", result.summary.critical);
console.log("Missing:", result.missingElements);
```

### 2. Testar Integração no Backend

```bash
# Deploy função
supabase functions deploy game-ai-chat-stream

# Testar com curl
curl -X POST https://your-project.supabase.co/functions/v1/game-ai-chat-stream \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Crie um top-down shooter"}],
    "mode": "spec",
    "approvedPlan": { ... }
  }'
```

### 3. Testar no Frontend

```typescript
// Console do navegador
const response = await fetch('/api/game-ai-chat-stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    messages: [{ role: 'user', content: 'Crie um top-down shooter' }],
    mode: 'spec',
    approvedPlan: { ... }
  })
});

const data = await response.json();
console.log('Profile Validation:', data.profileValidation);
```

---

## 📝 Checklist de Integração

### Backend
- [x] Criar `runtime-profile-validator.ts` para Deno
- [ ] Importar validador no `game-ai-chat-stream/index.ts`
- [ ] Adicionar validação após geração de spec
- [ ] Adicionar `profileValidation` ao response
- [ ] (Opcional) Implementar loop de correção automática
- [ ] Testar com curl

### Frontend
- [ ] Atualizar tipos para incluir `profileValidation`
- [ ] Exibir violações na UI (se houver)
- [ ] Mostrar indicador de validação
- [ ] (Opcional) Validar antes de enviar

### Documentação
- [x] Criar guia de integração
- [ ] Atualizar README
- [ ] Adicionar exemplos de uso

---

## 🚀 Próximos Passos

### Fase 2.2: Melhorias
- [ ] Adicionar mais gêneros (platformer, puzzle, racing)
- [ ] Validador genérico para qualquer perfil
- [ ] Cache de validações
- [ ] Métricas de validação

### Fase 2.3: UI
- [ ] Componente `ValidationPanel`
- [ ] Indicador visual de validação em tempo real
- [ ] Botão "Corrigir Automaticamente"
- [ ] Histórico de violações

---

**Status:** ✅ Validador criado, pronto para integração  
**Próximo:** Integrar no `game-ai-chat-stream/index.ts`
