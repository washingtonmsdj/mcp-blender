# 🐛 Correção dos 3 Bugs Identificados

## 📋 BUGS REPORTADOS

### 1. ❌ Jogo de corrida com fundo espacial
**Problema**: Pediu "jogo de corrida top-down" mas gerou com estrelas/espaço ao fundo

**Causa**: A IA está gerando `starfield` background para todos os tipos de jogo

### 2. ❌ HUD bugado/sobreposto
**Problema**: HUD aparecendo duplicado e mal posicionado

**Causa**: UISystem renderizando + HUD manual = duplicação

### 3. ❌ Estrutura não atualiza e não mostra código
**Problema**: Árvore de arquivos não atualiza e ao clicar não mostra código

**Causa**: Código duplicado no StudioWorkspace.tsx

---

## ✅ CORREÇÕES IMPLEMENTADAS

### 1. HUD Corrigido ✨

**ANTES** (Bugado):
```typescript
// UISystem renderizando
uiSystemRef.current.render(ctx);

// + HUD manual renderizando
ctx.fillText("Score: ...", ox + 10, oy + 20);
ctx.fillText("Health: ...", ox + 10, oy + 40);

// = DUPLICADO E SOBREPOSTO ❌
```

**DEPOIS** (Limpo):
```typescript
// UISystem NÃO renderiza mais
// Apenas mantém dados internos

// HUD manual único e bem posicionado
ctx.save();
const hudX = ox + 15;
let hudY = oy + 25;

// Score
ctx.fillText(`Score: ${score}`, hudX, hudY);
hudY += 25;

// Health
ctx.fillText(`Health: ${health}`, hudX, hudY);
hudY += 10;

// Health bar
ctx.fillRect(hudX, hudY, barWidth, barHeight);

ctx.restore();

// ✅ ÚNICO E BEM POSICIONADO
```

**Melhorias**:
- ✅ Fonte maior (14px)
- ✅ Espaçamento adequado (25px entre elementos)
- ✅ Health bar mais visível (12px altura, borda 2px)
- ✅ Cores mais fortes (rgba 0.9 para texto)
- ✅ Posicionamento consistente (hudX, hudY)

### 2. Estrutura Corrigida ✨

**ANTES** (Duplicado):
```typescript
export function StudioWorkspace() {
  const [spec, setSpec] = useState<OrdaxSpec | undefined>(undefined);
  const [rawJson, setRawJson] = useState<string | undefined>(undefined);
  const [openFileId, setOpenFileId] = useState<string | null>(null);
  const [showEditor, setShowEditor] = useState(false);
  const { project, save, exportProject, updateSpec } = useProject();

export function StudioWorkspace() {  // ❌ DUPLICADO
  const [spec, setSpec] = useState<OrdaxSpec | undefined>(undefined);
  const [rawJson, setRawJson] = useState<string | undefined>(undefined);
  const { project, save, exportProject, updateSpec } = useProject();
```

**DEPOIS** (Único):
```typescript
export function StudioWorkspace() {
  const [spec, setSpec] = useState<OrdaxSpec | undefined>(undefined);
  const [rawJson, setRawJson] = useState<string | undefined>(undefined);
  const [openFileId, setOpenFileId] = useState<string | null>(null);
  const [showEditor, setShowEditor] = useState(false);
  const { project, save, exportProject, updateSpec } = useProject();

  // ✅ ÚNICO E FUNCIONAL
```

**Resultado**:
- ✅ Estrutura atualiza corretamente
- ✅ Clique em arquivo abre o editor
- ✅ Código aparece no painel central

### 3. Fundo Espacial em Jogo de Corrida ⚠️

**Problema**: A IA está gerando este JSON para jogos de corrida:

```json
{
  "gameType": "racing",
  "visual": {
    "background": {
      "layers": [
        {
          "type": "starfield",  // ❌ ERRADO para corrida
          "density": 200,
          "speedY": 50
        }
      ]
    }
  }
}
```

**Solução**: Melhorar o prompt da IA no Supabase Function

---

## 🔧 CORREÇÃO DO PROMPT DA IA

Vou atualizar o `supabase/functions/game-ai-chat/index.ts`:

<function_calls>
<invoke name="readFile">
<parameter name="explanation">Lendo a função da IA para melhorar o prompt