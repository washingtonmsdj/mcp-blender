# 🚀 GUIA RÁPIDO: Integração do Profile Validator

## 📦 O que foi criado

```
src/lib/ordax/runtime-profiles/
├── topdown-shooter.ts        # Perfil canônico do gênero
├── validator.ts              # Validador de runtime
├── index.ts                  # Exports organizados
├── example-validation.ts     # Exemplos de uso
└── validator.test.ts         # Testes unitários
```

---

## 🎯 Uso Básico

### 1. Importar

```typescript
import {
  TOPDOWN_SHOOTER_PROFILE,
  validateRuntimeAgainstProfile,
  formatProfileViolations,
  generateMissingElementsReport
} from '@/lib/ordax/runtime-profiles';
```

### 2. Validar Runtime

```typescript
const result = validateRuntimeAgainstProfile(
  myRuntimeSpec,
  TOPDOWN_SHOOTER_PROFILE
);

if (!result.isValid) {
  console.error(formatProfileViolations(result));
  console.error(generateMissingElementsReport(result));
}
```

### 3. Verificar Violações

```typescript
// Verificar se há violações críticas
if (result.summary.critical > 0) {
  console.error("❌ Jogo não pode ser compilado");
  
  // Listar violações críticas
  result.violations
    .filter(v => v.level === 'CRITICAL')
    .forEach(v => {
      console.error(`[${v.id}] ${v.message}`);
      console.error(`Fix: ${v.fix}`);
    });
}
```

---

## 🔌 Integração com Protocolo de Compilação

### Opção 1: Validação no Backend (Supabase Function)

**Arquivo:** `supabase/functions/game-ai-chat-stream/index.ts`

```typescript
import {
  TOPDOWN_SHOOTER_PROFILE,
  validateRuntimeAgainstProfile
} from '../../../src/lib/ordax/runtime-profiles/index.ts';

// ... dentro do handler

// Após extrair runtimeSpec
const runtimeSpec = extractRuntimeSpecFromGameCode(generatedCode);

// VALIDAR CONTRA PERFIL
const validationResult = validateRuntimeAgainstProfile(
  runtimeSpec,
  TOPDOWN_SHOOTER_PROFILE
);

if (!validationResult.isValid) {
  // Retornar violações para o frontend
  return new Response(
    JSON.stringify({
      phase: 'validation',
      status: 'error',
      violations: validationResult.violations,
      missingElements: validationResult.missingElements,
      summary: validationResult.summary
    }),
    { headers: { 'Content-Type': 'application/json' } }
  );
}

// Prosseguir com compilação...
```

### Opção 2: Validação no Frontend (antes de enviar)

**Arquivo:** `src/components/ordax/StudioChatPanel.tsx`

```typescript
import {
  TOPDOWN_SHOOTER_PROFILE,
  validateRuntimeAgainstProfile,
  generateAIFeedback
} from '@/lib/ordax/runtime-profiles';

// ... dentro do componente

const handleValidateBeforeSend = () => {
  // Extrair runtimeSpec do código atual
  const runtimeSpec = extractRuntimeSpecFromGameCode(currentCode);
  
  // Validar
  const result = validateRuntimeAgainstProfile(
    runtimeSpec,
    TOPDOWN_SHOOTER_PROFILE
  );
  
  if (!result.isValid) {
    // Mostrar feedback ao usuário
    const feedback = generateAIFeedback(runtimeSpec);
    toast.error(feedback);
    return false;
  }
  
  return true;
};
```

### Opção 3: Validação Contínua (durante edição)

**Arquivo:** `src/components/ordax/CodeEditorPanel.tsx`

```typescript
import {
  TOPDOWN_SHOOTER_PROFILE,
  validateRuntimeAgainstProfile
} from '@/lib/ordax/runtime-profiles';

// ... dentro do componente

useEffect(() => {
  // Validar a cada mudança no código
  const validateCode = async () => {
    try {
      const runtimeSpec = extractRuntimeSpecFromGameCode(code);
      const result = validateRuntimeAgainstProfile(
        runtimeSpec,
        TOPDOWN_SHOOTER_PROFILE
      );
      
      // Atualizar estado de validação
      setValidationResult(result);
      
      // Mostrar indicador visual
      if (result.isValid) {
        setValidationStatus('✅ Runtime válido');
      } else {
        setValidationStatus(
          `⚠️ ${result.summary.critical} violações críticas`
        );
      }
    } catch (error) {
      console.error('Erro ao validar:', error);
    }
  };
  
  // Debounce para não validar a cada tecla
  const timer = setTimeout(validateCode, 1000);
  return () => clearTimeout(timer);
}, [code]);
```

---

## 🤖 Integração com IA (Feedback Loop)

### Cenário: IA gera código incompleto

```typescript
// 1. IA gera código
const generatedCode = await generateGameCode(userPrompt);

// 2. Extrair runtime
const runtimeSpec = extractRuntimeSpecFromGameCode(generatedCode);

// 3. Validar
const result = validateRuntimeAgainstProfile(
  runtimeSpec,
  TOPDOWN_SHOOTER_PROFILE
);

// 4. Se inválido, gerar prompt de correção
if (!result.isValid) {
  const correctionPrompt = `
O código gerado está incompleto. Faltam os seguintes elementos:

${generateMissingElementsReport(result)}

Por favor, adicione os elementos faltantes ao código.
  `.trim();
  
  // 5. IA corrige
  const correctedCode = await generateGameCode(correctionPrompt, {
    previousCode: generatedCode,
    violations: result.violations
  });
  
  // 6. Validar novamente (loop até válido)
  // ...
}
```

---

## 📊 Exibir Violações no Frontend

### Componente de Validação

```typescript
// src/components/ordax/ValidationPanel.tsx

import { ProfileValidationResult } from '@/lib/ordax/runtime-profiles';

interface ValidationPanelProps {
  result: ProfileValidationResult;
}

export function ValidationPanel({ result }: ValidationPanelProps) {
  if (result.isValid) {
    return (
      <div className="p-4 bg-green-50 border border-green-200 rounded">
        <p className="text-green-800">
          ✅ Runtime válido para gênero '{result.genre}'
        </p>
      </div>
    );
  }
  
  return (
    <div className="p-4 bg-red-50 border border-red-200 rounded">
      <h3 className="font-bold text-red-800 mb-2">
        ❌ Validação Falhou
      </h3>
      
      <div className="mb-4">
        <p className="text-sm text-red-700">
          Críticas: {result.summary.critical} |
          Graves: {result.summary.severe} |
          Menores: {result.summary.minor}
        </p>
      </div>
      
      {result.summary.critical > 0 && (
        <div className="mb-4">
          <h4 className="font-semibold text-red-800 mb-2">
            Violações Críticas:
          </h4>
          <ul className="space-y-2">
            {result.violations
              .filter(v => v.level === 'CRITICAL')
              .map(v => (
                <li key={v.id} className="text-sm">
                  <span className="font-mono text-xs bg-red-100 px-1 rounded">
                    {v.id}
                  </span>
                  <p className="mt-1">{v.message}</p>
                  <p className="text-xs text-red-600 mt-1">
                    Fix: {v.fix}
                  </p>
                </li>
              ))}
          </ul>
        </div>
      )}
      
      {result.missingElements.systems.length > 0 && (
        <div className="mb-2">
          <h5 className="font-semibold text-sm">Sistemas faltantes:</h5>
          <p className="text-sm text-red-700">
            {result.missingElements.systems.join(', ')}
          </p>
        </div>
      )}
      
      {result.missingElements.entities.length > 0 && (
        <div className="mb-2">
          <h5 className="font-semibold text-sm">Entidades faltantes:</h5>
          <p className="text-sm text-red-700">
            {result.missingElements.entities.join(', ')}
          </p>
        </div>
      )}
    </div>
  );
}
```

---

## 🧪 Testar

### Teste Manual

```typescript
// Console do navegador ou Node.js

import {
  TOPDOWN_SHOOTER_PROFILE,
  validateRuntimeAgainstProfile
} from './src/lib/ordax/runtime-profiles';

const testRuntime = {
  gameType: 'topdown',
  title: 'Test Game',
  description: 'Testing validation',
  systems: ['PhysicsSystem'], // Incompleto
  scene: {
    gravity: { x: 0, y: 0 },
    entities: []
  }
};

const result = validateRuntimeAgainstProfile(
  testRuntime,
  TOPDOWN_SHOOTER_PROFILE
);

console.log('Valid?', result.isValid);
console.log('Critical:', result.summary.critical);
console.log('Missing systems:', result.missingElements.systems);
```

### Teste Automatizado

```bash
npm test -- src/lib/ordax/runtime-profiles/validator.test.ts
```

---

## 📝 Checklist de Integração

### Backend (Supabase Function)
- [ ] Importar `validateRuntimeAgainstProfile`
- [ ] Adicionar validação após extração de runtime
- [ ] Retornar violações se inválido
- [ ] Bloquear compilação se violações críticas

### Frontend (StudioChatPanel)
- [ ] Importar validador
- [ ] Validar antes de enviar mensagem
- [ ] Exibir feedback de validação
- [ ] Mostrar violações ao usuário

### IA (Feedback Loop)
- [ ] Detectar violações
- [ ] Gerar prompt de correção
- [ ] Loop até runtime válido
- [ ] Limitar tentativas (max 3)

### UI (ValidationPanel)
- [ ] Criar componente de validação
- [ ] Exibir violações críticas
- [ ] Exibir elementos faltantes
- [ ] Botão para corrigir automaticamente

---

## 🎯 Exemplo Completo: Fluxo End-to-End

```typescript
// 1. Usuário envia prompt
const userPrompt = "Crie um top-down shooter survival";

// 2. IA gera código
const generatedCode = await aiGenerateCode(userPrompt);

// 3. Extrair runtime
const runtimeSpec = extractRuntimeSpecFromGameCode(generatedCode);

// 4. Validar
const result = validateRuntimeAgainstProfile(
  runtimeSpec,
  TOPDOWN_SHOOTER_PROFILE
);

// 5. Se inválido, corrigir
let attempts = 0;
while (!result.isValid && attempts < 3) {
  const correctionPrompt = generateCorrectionPrompt(result);
  generatedCode = await aiGenerateCode(correctionPrompt, {
    previousCode: generatedCode
  });
  
  runtimeSpec = extractRuntimeSpecFromGameCode(generatedCode);
  result = validateRuntimeAgainstProfile(
    runtimeSpec,
    TOPDOWN_SHOOTER_PROFILE
  );
  
  attempts++;
}

// 6. Se ainda inválido, avisar usuário
if (!result.isValid) {
  showError("Não foi possível gerar um jogo válido. Tente ser mais específico.");
  showValidationPanel(result);
} else {
  // 7. Compilar e executar
  const compiledGame = await compileGame(generatedCode);
  runGame(compiledGame);
}
```

---

## 🚀 Próximos Passos

1. **Integrar no Backend**
   - Adicionar validação no `game-ai-chat-stream`
   - Retornar violações estruturadas

2. **Integrar no Frontend**
   - Criar `ValidationPanel` component
   - Exibir violações em tempo real

3. **Feedback Loop com IA**
   - IA detecta violações
   - IA corrige automaticamente
   - Loop até válido

4. **Expandir para outros gêneros**
   - Criar `platformer.ts` profile
   - Criar `puzzle.ts` profile
   - Validador genérico para qualquer perfil

---

**Status:** ✅ Pronto para integração

Todos os arquivos estão criados, testados e sem erros. Basta seguir este guia para integrar o validador no fluxo de compilação.
