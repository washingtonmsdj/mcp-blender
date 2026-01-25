# FASE 10: UI GUIDE - Como Usar o Genome Viewer

## 1. Visualizar Genoma no Studio

### Localização
No **Studio Preview Panel**, você verá uma nova aba:

```
┌─────────────────────────────────────────────────────────┐
│ [Preview] [Visual Editor] [Genome] ← NOVA ABA          │
└─────────────────────────────────────────────────────────┘
```

### Como Acessar
1. Abra um jogo no Studio (preset ou criado via chat)
2. Clique na aba **"Genome"**
3. Veja a representação canônica do jogo

### O Que Você Vê

```
┌─────────────────────────────────────────────────────────┐
│ 🧬 Game Genome                                          │
│ Representação canônica da identidade do jogo           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Genre                                                   │
│ [topdown-shooter]                                       │
│                                                         │
│ Themes                                                  │
│ [space] [survival]                                      │
│                                                         │
│ ─────────────────────────────────────────────────────  │
│                                                         │
│ Difficulty    Speed        Boss                        │
│ [normal]      [normal]     [No]                        │
│                                                         │
│ ─────────────────────────────────────────────────────  │
│                                                         │
│ Progression                                             │
│   Win:  score (1000)                                   │
│   Lose: health (0)                                     │
│                                                         │
│ ─────────────────────────────────────────────────────  │
│                                                         │
│ Enemy Types                                             │
│   [basic] (chase): 1x                                  │
│   [fast] (chase): 2x                                   │
│                                                         │
│ ─────────────────────────────────────────────────────  │
│                                                         │
│ Mechanics                                               │
│ [movement] [combat] [collection] [spawning]            │
│ [health] [score]                                       │
│                                                         │
│ ─────────────────────────────────────────────────────  │
│                                                         │
│ HUD Elements                                            │
│ [health] [score] [timer]                               │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## 2. Comparar Genomas no Remix

### Fluxo Completo

#### Passo 1: Iniciar Remix
```
┌─────────────────────────────────────────────────────────┐
│ ✨ Remixar Jogo                                         │
│ Descreva o que você quer mudar neste jogo              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ O que você quer mudar?                                 │
│ ┌─────────────────────────────────────────────────┐   │
│ │ zombie medieval hard boss                       │   │
│ │                                                 │   │
│ │                                                 │   │
│ └─────────────────────────────────────────────────┘   │
│                                                         │
│ 💡 Combine temas, dificuldade, velocidade e boss       │
│                                                         │
│                          [Cancelar] [✨ Gerar Remix]   │
└─────────────────────────────────────────────────────────┘
```

#### Passo 2: Ver Preview com Comparação

```
┌─────────────────────────────────────────────────────────┐
│ ✨ Preview do Remix                                     │
│ Revise as mudanças antes de confirmar                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ ┌─────────────────────────────────────────────────┐   │
│ │ 🎯 Intent Detectado:                            │   │
│ │   Temas: zombie + medieval                      │   │
│ │   Dificuldade: hard                             │   │
│ │   Boss: Sim 👑                                  │   │
│ └─────────────────────────────────────────────────┘   │
│                                                         │
│ ┌──────────────────────┬──────────────────────────┐   │
│ │ Jogo Original:       │ Jogo Remixado:           │   │
│ ├──────────────────────┼──────────────────────────┤   │
│ │ 🧬 Game Genome       │ 🧬 Game Genome           │   │
│ │                      │                          │   │
│ │ Genre                │ Genre                    │   │
│ │ [topdown-shooter]    │ [topdown-shooter]        │   │
│ │                      │                          │   │
│ │ Themes               │ Themes                   │   │
│ │ [space]              │ [zombie] [medieval]      │   │
│ │                      │                          │   │
│ │ Difficulty  Speed    │ Difficulty  Speed        │   │
│ │ [normal]    [normal] │ [hard]      [normal]     │   │
│ │                      │                          │   │
│ │ Boss                 │ Boss                     │   │
│ │ [No]                 │ [Yes 👑]                 │   │
│ │                      │                          │   │
│ │ Enemy Types          │ Enemy Types              │   │
│ │ [basic] (chase): 1x  │ [basic] (chase): 2x      │   │
│ │                      │ [boss] (boss): 1x        │   │
│ └──────────────────────┴──────────────────────────┘   │
│                                                         │
│ ┌─────────────────────────────────────────────────┐   │
│ │ Mudanças Aplicadas:                             │   │
│ │ • Temas alterados: space → zombie, medieval     │   │
│ │ • Dificuldade aumentada: normal → hard          │   │
│ │ • Boss adicionado                               │   │
│ │ • Inimigos mais fortes                          │   │
│ └─────────────────────────────────────────────────┘   │
│                                                         │
│                          [← Voltar] [✓ Aceitar Remix]  │
└─────────────────────────────────────────────────────────┘
```

## 3. Modo Compact

Para uso inline, o GenomeViewer tem um modo compact:

```tsx
<GenomeViewer genome={genome} compact />
```

Renderiza como:
```
🧬 [zombie+medieval] [hard] [faster] [👑] 5 enemies 8 mechanics
```

Útil para:
- Listas de jogos
- Cards de preview
- Histórico de versões
- Comparações rápidas

## 4. Casos de Uso

### Caso 1: Explorar Preset
```
Usuário → Clica "Space Survival"
       → Jogo carrega
       → Clica aba "Genome"
       → Vê estrutura completa
       → Entende o que o jogo é
```

### Caso 2: Remix Informado
```
Usuário → Tem jogo rodando
       → Clica "Remixar"
       → Digita mudanças
       → Vê comparação lado a lado
       → Entende exatamente o que vai mudar
       → Aceita ou volta
```

### Caso 3: Debug
```
Dev → Jogo não está como esperado
    → Abre aba "Genome"
    → Vê estrutura canônica
    → Identifica problema
    → Corrige
```

### Caso 4: Aprendizado
```
Usuário → Quer entender jogos
        → Abre vários presets
        → Compara genomas
        → Entende padrões
        → Cria jogos melhores
```

## 5. Interpretação dos Campos

### Genre
- `topdown-shooter`: Jogo de tiro top-down
- Outros gêneros virão no futuro

### Themes
- `space`: Tema espacial (🚀, ☄️, 🛸)
- `zombie`: Tema zumbi (🧟)
- `medieval`: Tema medieval (🗡️, 👺, 🏰)
- `ninja`: Tema ninja (🥷, 👹)
- `pirate`: Tema pirata (🏴‍☠️, 🦜)
- `robot`: Tema robô (🤖, 👾)

### Difficulty
- `easy`: Inimigos fracos, pouco dano
- `normal`: Balanceado
- `hard`: Inimigos fortes, muito dano

### Speed
- `slower`: Jogo mais lento
- `normal`: Velocidade padrão
- `faster`: Jogo mais rápido

### Boss
- `Yes 👑`: Tem boss fight
- `No`: Sem boss

### Progression
- **Win Condition**: Como ganhar
  - `score`: Atingir pontuação
  - `time`: Sobreviver tempo
  - `survival`: Sobreviver indefinidamente
  - `collection`: Coletar itens
- **Lose Condition**: Como perder
  - `health`: Vida chegar a zero
  - `time`: Tempo acabar
  - `capture`: Ser capturado

### Enemy Types
- **Archetypes**:
  - `basic`: Inimigo padrão
  - `fast`: Inimigo rápido
  - `tank`: Inimigo resistente
  - `ranged`: Inimigo à distância
  - `boss`: Chefe
- **Behaviors**:
  - `chase`: Persegue jogador
  - `patrol`: Patrulha área
  - `ranged`: Ataca à distância
  - `boss`: Comportamento de boss

### Mechanics
Lista de mecânicas presentes:
- `movement`: Movimentação
- `combat`: Combate
- `shooting`: Tiro
- `collection`: Coleta
- `spawning`: Spawn de inimigos
- `health`: Sistema de vida
- `score`: Sistema de pontuação

### UI Elements
- **HUD**: Elementos na tela durante jogo
  - `health`: Barra de vida
  - `score`: Pontuação
  - `timer`: Temporizador
  - `ammo`: Munição
  - `wave`: Onda atual
  - `keys`: Chaves coletadas
- **Screens**: Telas do jogo
  - `game`: Tela de jogo
  - `victory`: Tela de vitória
  - `gameover`: Tela de game over

## 6. Dicas de Uso

### Para Usuários
1. **Explore presets**: Veja genomas de diferentes jogos
2. **Compare antes de aceitar**: Use comparação no remix
3. **Aprenda padrões**: Entenda o que faz um jogo bom

### Para Desenvolvedores
1. **Debug visual**: Use genome para debug
2. **Validação**: Confirme que jogo está correto
3. **Documentação**: Genome é documentação viva

### Para Designers
1. **Análise**: Entenda estrutura de jogos
2. **Balanceamento**: Veja stats de inimigos
3. **Iteração**: Compare versões rapidamente

## 7. Atalhos de Teclado (Futuro)

Possíveis atalhos para implementar:
- `G`: Abrir aba Genome
- `Ctrl+G`: Copiar genome como JSON
- `Ctrl+Shift+G`: Exportar genome
- `R`: Abrir Remix Dialog
- `Ctrl+R`: Remix rápido

## 8. Acessibilidade

O GenomeViewer é acessível:
- ✅ Cores com contraste adequado
- ✅ Badges com texto legível
- ✅ Estrutura semântica (headings, sections)
- ✅ Navegação por teclado
- ✅ Screen reader friendly

## Conclusão

O Genome Viewer torna a estrutura de jogos **visível e compreensível**.

**Antes**: Jogo era uma caixa preta  
**Depois**: Jogo tem identidade canônica visível

**Resultado**: Usuários entendem melhor, desenvolvem melhor, e criam jogos melhores.

---

**Documentação Técnica**: `FASE10_CANONICAL_GAME_GENOME.md`  
**Guia de Integração**: `FASE10_INTEGRATION_COMPLETE.md`  
**Este Guia**: `FASE10_UI_GUIDE.md`
