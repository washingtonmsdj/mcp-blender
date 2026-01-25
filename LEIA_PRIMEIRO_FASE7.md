# 🎮 LEIA PRIMEIRO - FASE 7: CANONICAL PRESETS

## O Que É?

**3 jogos prontos que funcionam perfeitamente sem usar o chat.**

Clique → Revise → Jogue. Simples assim.

## Os 3 Jogos

### 🚀 Space Survival
Sobreviva no espaço coletando cristais e evitando asteroides.
- **Tempo para jogar**: 10 segundos
- **Dificuldade**: Fácil
- **Objetivo**: 1000 pontos

### 🧟 Zombie Arena
Enfrente ondas crescentes de zumbis.
- **Tempo para jogar**: 10 segundos
- **Dificuldade**: Média
- **Objetivo**: 500 pontos

### 🗡️ Dungeon Shooter
Explore dungeons e derrote monstros.
- **Tempo para jogar**: 10 segundos
- **Dificuldade**: Média
- **Objetivo**: 800 pontos

## Como Usar

### Passo 1: Abrir
```
Ordax Studio → Botão "Jogos Canônicos" (roxo/rosa)
```

### Passo 2: Escolher
```
Clique em um dos 3 cards
```

### Passo 3: Revisar
```
Leia o resumo do jogo (10 segundos)
```

### Passo 4: Confirmar
```
Clique em "Aceitar e Criar Jogo"
```

### Passo 5: Jogar
```
Jogo está rodando! 🎉
```

## Garantias

✅ **Sempre funciona** - Todos os presets são testados  
✅ **Sem bugs** - Validação automática  
✅ **Sem chat** - Zero prompts necessários  
✅ **Rápido** - Menos de 30 segundos  
✅ **Claro** - Você entende o jogo em 10s  

## Para Desenvolvedores

### Arquivos Principais
```
src/lib/ordax/canonical-presets/
├── space-survival.ts       # Preset 1
├── zombie-arena.ts         # Preset 2
└── dungeon-shooter.ts      # Preset 3

src/components/ordax/
├── CanonicalPresetButtons.tsx    # UI dos botões
├── PresetSelectionModal.tsx      # Modal de seleção
└── StudioTopBar.tsx              # Integração
```

### Criar Novo Preset
```typescript
export function createMyGamePreset(): CanonicalPreset {
  const runtimeSpec: RuntimeSpec = {
    profile: 'topdown-shooter',
    entities: { /* ... */ },
    spawners: { /* ... */ },
    rules: { /* ... */ },
    ui: { /* ... */ }
  };

  return {
    id: 'my-game',
    name: 'My Game',
    description: 'Description',
    emoji: '🎮',
    runtimeSpec
  };
}
```

### Testar Preset
```bash
npm test canonical-presets
```

## Fluxo Técnico

```
Usuário clica
    ↓
Gera RuntimeSpec
    ↓
Valida (validateRuntimeSpec)
    ↓
Aplica Autofill (applyAutofill)
    ↓
Gera Resumo (generateHumanSummary)
    ↓
Mostra HumanGamePlanView
    ↓
Usuário confirma
    ↓
Converte para OrdaxSpec
    ↓
Salva no VFS
    ↓
Jogo roda!
```

## Diferença das Outras Fases

| Fase | O Que Faz | Requer Chat? |
|------|-----------|--------------|
| Fase 1-6 | Infraestrutura | Sim |
| **Fase 7** | **Jogos Prontos** | **Não** |

## Por Que Isso É Importante?

### Antes da Fase 7:
```
Usuário: "Quero fazer um jogo de zumbis"
Chat: "Ok, vou criar..."
[5 minutos de conversa]
[Ajustes e correções]
[Finalmente funciona]
```

### Depois da Fase 7:
```
Usuário: [Clica em "Zombie Arena"]
[10 segundos depois]
Jogo rodando perfeitamente!
```

## Próximos Passos

1. **Teste os 3 presets** - Veja como funcionam
2. **Leia FASE7_CANONICAL_PRESETS.md** - Documentação completa
3. **Crie seus presets** - Adicione novos jogos
4. **Compartilhe** - Mostre para outros devs

## Troubleshooting

### Preset não carrega?
```typescript
// Verifique o console
// Deve passar na validação
const validation = validateRuntimeSpec(preset.runtimeSpec);
console.log(validation);
```

### Jogo não roda?
```typescript
// Verifique o autofill
const filled = applyAutofill(preset.runtimeSpec);
console.log(filled);
```

### Resumo não aparece?
```typescript
// Verifique a geração
const summary = generateHumanSummary(filled);
console.log(summary);
```

## Conclusão

**Fase 7 = Jogos instantâneos sem chat.**

Clique. Revise. Jogue. Pronto.

---

**Documentação completa**: `FASE7_CANONICAL_PRESETS.md`  
**Testes**: `src/lib/ordax/canonical-presets/presets.test.ts`  
**Código**: `src/lib/ordax/canonical-presets/`
