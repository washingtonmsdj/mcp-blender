# 🎨 LEIA PRIMEIRO - FASE 8: REMIX ENGINE

## O Que É?

**Transforme qualquer jogo em infinitos novos jogos.**

Clique em "Remixar" → Escreva o que quer mudar → Novo jogo pronto!

## Como Usar

### Passo 1: Jogar um Jogo
```
Abra qualquer jogo no Studio
```

### Passo 2: Clicar em Remixar
```
Barra de controles → Botão "✨ Remixar este jogo"
```

### Passo 3: Escrever Intent
```
"transformar em zumbi"
"tema espacial"
"mais difícil"
"mais rápido"
```

### Passo 4: Gerar
```
Clique em "Gerar Remix"
```

### Passo 5: Revisar
```
Veja as mudanças
Revise o preview
```

### Passo 6: Aceitar
```
Clique em "Aceitar Remix"
Novo jogo está pronto!
```

## Intenções Suportadas

### 🧟 Zumbi
```
Input: "transformar em zumbi"
Resultado: Inimigos viram zumbis (mais lentos, mais resistentes)
```

### 🚀 Espacial
```
Input: "tema espacial"
Resultado: Player vira nave, inimigos viram asteroides
```

### 🗡️ Medieval
```
Input: "medieval"
Resultado: Player vira guerreiro, inimigos viram monstros
```

### ⚡ Mais Rápido
```
Input: "mais rápido"
Resultado: +50% velocidade em tudo, spawns mais rápidos
```

### 💪 Mais Difícil
```
Input: "mais difícil"
Resultado: Inimigos mais fortes, mais spawns
```

## Garantias

✅ **Nunca quebra** - Validação automática  
✅ **Sempre funciona** - Autofill preenche faltantes  
✅ **Preview claro** - Vê mudanças antes de aceitar  
✅ **Reversível** - Jogo original preservado  

## Arquitetura

```
src/lib/ordax/remix-engine/
├── generate-remix-patch.ts    # Gera mudanças
├── apply-remix-patch.ts       # Aplica mudanças
└── validate-remix.ts          # Valida resultado

src/components/ordax/
├── RemixButton.tsx            # Botão no Preview
└── RemixDialog.tsx            # Dialog de remix
```

## Fluxo Técnico

```
1. generateRemixPatch(baseSpec, intent)
   → SemanticPatch
   
2. applyRemixPatch(baseSpec, patch)
   → RuntimeSpec remixado
   
3. validateRemix(remixedSpec)
   → Validação
   
4. Mostrar preview
   → HumanGamePlanView
   
5. Usuário confirma
   → Novo jogo criado
```

## Exemplos Práticos

### Exemplo 1: Space Survival → Zombie Arena
```
Base: Space Survival (🚀 + ☄️ + 💎)
Intent: "transformar em zumbi"
Resultado: Zombie Arena (🧑 + 🧟 + ❤️)
```

### Exemplo 2: Aumentar Dificuldade
```
Base: Qualquer jogo
Intent: "mais difícil"
Resultado: 
- Inimigos: +50% HP, +30% dano
- Spawns: +50% quantidade, -20% intervalo
```

### Exemplo 3: Mudar Tema
```
Base: Dungeon Shooter
Intent: "tema espacial"
Resultado: Space Shooter
```

## Para Desenvolvedores

### Adicionar Nova Intenção

```typescript
// Em generate-remix-patch.ts

if (intent.includes('ninja')) {
  return generateNinjaRemix(baseSpec);
}

function generateNinjaRemix(baseSpec: RuntimeSpec) {
  const patch: SemanticPatch = {
    entities: {
      modify: {
        player: { sprite: '🥷', speed: 250 }
      }
    }
  };
  
  const changes: RemixChange[] = [{
    type: 'modify',
    category: 'entity',
    target: 'player',
    description: 'Player virou ninja (mais rápido)'
  }];
  
  return { patch, changes };
}
```

### Testar Remix

```typescript
import { generateRemixPatch, applyRemixPatch, validateRemix } from '@/lib/ordax/remix-engine';

const baseSpec = createSpaceSurvivalPreset().runtimeSpec;
const { patch, changes } = generateRemixPatch(baseSpec, "transformar em zumbi");
const remixed = applyRemixPatch(baseSpec, patch);
const validation = validateRemix(remixed);

console.log(validation.valid); // true
console.log(changes); // Lista de mudanças
```

## Troubleshooting

### Remix não aparece?
```
Verifique se há um jogo rodando no Preview
Botão só aparece quando spec está carregado
```

### Validação falha?
```
Verifique console para erros
Remix pode ter removido algo obrigatório
```

### Preview não mostra mudanças?
```
Verifique se intent foi reconhecido
Tente uma intenção suportada
```

## Próximos Passos

1. **Teste os remixes** - Experimente diferentes intents
2. **Adicione intenções** - Crie novos padrões de remix
3. **Compartilhe** - Mostre remixes para outros devs

## Conclusão

**Fase 8 = Infinitos jogos a partir de um.**

Remix. Remix. Remix. Nunca para de criar!

---

**Documentação completa**: `FASE8_REMIX_ENGINE.md`  
**Core**: `src/lib/ordax/remix-engine/`  
**UI**: `src/components/ordax/Remix*.tsx`
