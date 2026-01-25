# 🧬 LEIA PRIMEIRO - FASE 10: CANONICAL GAME GENOME

## O Que É Isso?

**Fase 10 dá a cada jogo uma identidade canônica - um "DNA" que pode ser extraído, comparado e aplicado.**

Pense nisso como o **genoma de um jogo**: uma representação estrutural e determinística de tudo que define sua identidade.

## Por Que Isso Importa?

### Antes da Fase 10
```
Jogo = Caixa Preta
❓ Não dá pra saber o que tem dentro
❓ Não dá pra comparar dois jogos
❓ Não dá pra recriar um jogo
❓ Não dá pra versionar mudanças
```

### Depois da Fase 10
```
Jogo = Genoma Visível
✅ Você vê exatamente o que o jogo é
✅ Você compara jogos estruturalmente
✅ Você recria jogos a partir do genoma
✅ Você versiona e compartilha genomas
```

## Quick Start

### 1. Ver Genoma de um Jogo

No Studio, quando você tem um jogo rodando:

```
1. Clique na aba "Genome" (ao lado de Preview)
2. Veja a estrutura completa do jogo
```

Você verá:
- 🎮 Genre (topdown-shooter)
- 🎨 Themes (space, zombie, medieval...)
- ⚡ Difficulty (easy, normal, hard)
- 🏃 Speed (slower, normal, faster)
- 👑 Boss (yes/no)
- 🎯 Progression (como ganhar/perder)
- 👾 Enemy Types (tipos e comportamentos)
- 🔧 Mechanics (lista completa)
- 📊 UI Elements (HUD e screens)

### 2. Comparar Genomas no Remix

Quando você faz remix de um jogo:

```
1. Clique "Remixar este jogo"
2. Digite mudanças: "zombie medieval hard boss"
3. Clique "Gerar Remix"
4. Veja comparação lado a lado:
   - Jogo Original (esquerda)
   - Jogo Remixado (direita)
5. Aceite ou volte
```

Agora você **vê exatamente** o que vai mudar antes de aceitar!

### 3. Usar Programaticamente

```typescript
import { extractGenome, applyGenome, compareGenomes } from '@/lib/ordax/game-genome';

// Extrair genoma
const genome = extractGenome(runtimeSpec);

// Aplicar genoma
const newGame = applyGenome(baseSpec, targetGenome);

// Comparar genomas
const diff = compareGenomes(genome1, genome2);
```

## Documentação

### 📚 Leia Nesta Ordem

1. **LEIA_PRIMEIRO_FASE10.md** ← Você está aqui
   - Overview rápido
   - Quick start
   - Conceitos básicos

2. **FASE10_CANONICAL_GAME_GENOME.md**
   - Documentação técnica completa
   - Estrutura do GameGenome
   - APIs e exemplos
   - Testes

3. **FASE10_UI_GUIDE.md**
   - Como usar a UI
   - Screenshots e exemplos visuais
   - Casos de uso
   - Interpretação dos campos

4. **FASE10_INTEGRATION_COMPLETE.md**
   - Como foi integrado
   - Arquivos modificados
   - Fluxo completo
   - Benefícios

5. **FASE10_FINAL_STATUS.md**
   - Status final
   - Testes e build
   - Garantias cumpridas
   - Próximos passos

## Conceitos Principais

### GameGenome

É a representação canônica de um jogo. Contém:

```typescript
{
  genre: 'topdown-shooter',
  themes: ['space', 'survival'],
  difficulty: 'normal',
  speed: 'normal',
  boss: false,
  progression: {
    winCondition: 'score',
    winTarget: 1000,
    loseCondition: 'health',
    loseTarget: 0
  },
  enemyTypes: [
    { archetype: 'basic', count: 1, behavior: 'chase' }
  ],
  mechanics: ['movement', 'combat', 'collection'],
  ui: {
    hud: ['health', 'score', 'timer'],
    screens: ['game', 'victory', 'gameover']
  }
}
```

### Operações

#### extractGenome(runtimeSpec)
Extrai o genoma de um RuntimeSpec.
- ✅ Determinístico (mesmo input → mesmo output)
- ✅ Sem heurísticas frágeis
- ✅ Detecta temas, dificuldade, velocidade automaticamente

#### applyGenome(baseSpec, genome)
Aplica um genoma a um RuntimeSpec base.
- ✅ Usa Remix Engine internamente
- ✅ Validate + Autofill sempre rodam
- ✅ Gera patch semântico

#### compareGenomes(from, to)
Compara dois genomas e retorna diferenças.
- ✅ Comparação estrutural
- ✅ Detecta mudanças em todos os campos
- ✅ Útil para versionamento

### Propriedade Fundamental

```typescript
extract(apply(G)) ≈ G
```

**Significado**: Se você aplicar um genoma e depois extrair, deve obter um genoma equivalente.

**Status**: ✅ Testado e validado

## Casos de Uso Reais

### 1. Explorar Presets
```
Você → Clica "Space Survival"
    → Jogo carrega
    → Clica aba "Genome"
    → Vê: space theme, normal difficulty, no boss
    → Entende o jogo antes de jogar
```

### 2. Remix Informado
```
Você → Tem jogo Space Survival rodando
    → Clica "Remixar"
    → Digita "zombie hard boss"
    → Vê comparação:
       Original: space, normal, no boss
       Remixado: zombie, hard, boss
    → Aceita porque sabe exatamente o que vai mudar
```

### 3. Debug
```
Dev → Jogo não está como esperado
    → Abre aba "Genome"
    → Vê: difficulty = easy (deveria ser normal)
    → Identifica problema
    → Corrige
```

### 4. Versionamento
```
Dev → Salva genome v1
    → Faz mudanças
    → Salva genome v2
    → Compara: diff = compareGenomes(v1, v2)
    → Vê exatamente o que mudou
```

### 5. Compartilhamento
```
Usuário A → Cria jogo incrível
          → Extrai genome
          → Compartilha JSON

Usuário B → Recebe genome
          → Aplica ao seu jogo base
          → Recria jogo similar
```

## Testes

### Rodar Testes
```bash
npm test -- genome
```

### Resultado Esperado
```
✓ extractGenome from Space Survival
✓ extractGenome from Zombie Arena
✓ Determinismo
✓ applyGenome to base spec
✓ extract(apply(G)) ≈ G
✓ compareGenomes - no differences
✓ compareGenomes - theme differences
✓ compareGenomes - difficulty differences
✓ Structural comparison
✓ Recreation from genome

10/10 testes passando ✅
```

## UI Features

### Aba Genome no Studio
- Localização: `[Preview] [Visual Editor] [Genome]`
- Mostra: Genoma completo do jogo atual
- Útil para: Exploração, debug, aprendizado

### Comparação no Remix
- Localização: Remix Dialog → Preview
- Mostra: Original vs Remixado lado a lado
- Útil para: Decisão informada antes de aceitar

### Modo Compact
- Uso: `<GenomeViewer genome={genome} compact />`
- Mostra: `🧬 zombie+medieval hard boss 3 enemies`
- Útil para: Listas, cards, histórico

## Detecção Automática

### Temas
O sistema detecta temas por sprites:
- 🧟 = zombie
- 🚀 = space
- 🗡️ = medieval
- 🥷 = ninja
- 🏴‍☠️ = pirate
- 🤖 = robot

### Dificuldade
Baseado em stats de inimigos:
- Easy: inimigos fracos (health < 40, damage < 12)
- Normal: balanceado
- Hard: inimigos fortes (health > 70, damage > 15)

### Velocidade
Baseado em velocidades médias:
- Slower: avgSpeed < 90
- Normal: 90-150
- Faster: avgSpeed > 150

### Arquétipos
Classificação automática de inimigos:
- Boss: health > 300 ou behavior = 'boss'
- Fast: speed > 120
- Tank: health > 80
- Ranged: behavior = 'ranged'
- Basic: padrão

## Garantias

### ✅ Nenhum Contrato Mudou
Todos os contratos existentes permanecem inalterados.

### ✅ Nenhum System Mudou
Todos os 18 systems permanecem inalterados.

### ✅ Backward Compatible
Código antigo funciona sem mudanças.

### ✅ Todos os Testes Passando
69/69 testes passando (10 novos + 59 existentes).

### ✅ Build Sem Erros
Build de produção funciona perfeitamente.

## Próximos Passos Possíveis

### Expansões Futuras
1. **Genome Library**: Biblioteca de genomas salvos
2. **Genome Breeding**: Combinar dois genomas
3. **Genome Mutation**: Mutações aleatórias
4. **Genome Evolution**: Evolução por fitness
5. **Genome Sharing**: Compartilhar entre usuários
6. **Genome Search**: Buscar jogos por genoma
7. **Genome Analytics**: Análise de popularidade

### Melhorias Incrementais
1. Mais arquétipos de inimigos
2. Mais mecânicas detectáveis
3. Compressão de genomas
4. Validação de genomas
5. Histórico de genomas
6. Undo/Redo de genomas

## FAQ

### P: O que é um genoma?
**R**: É a representação canônica da identidade de um jogo. Como o DNA do jogo.

### P: Por que "canônico"?
**R**: Porque é determinístico e único. Mesmo jogo → mesmo genoma.

### P: Posso editar o genoma diretamente?
**R**: Sim! Você pode modificar o objeto GameGenome e aplicar com `applyGenome()`.

### P: O genoma substitui o RuntimeSpec?
**R**: Não! O genoma é uma **representação** do RuntimeSpec, não um substituto.

### P: Posso compartilhar genomas?
**R**: Sim! Genomas são JSON simples que podem ser salvos e compartilhados.

### P: O genoma funciona com jogos antigos?
**R**: Sim! É 100% backward compatible. Funciona com todos os jogos.

### P: Preciso mudar meu código?
**R**: Não! É opt-in. Use apenas se quiser.

## Comandos Úteis

```bash
# Rodar todos os testes
npm test

# Rodar apenas testes de genome
npm test -- genome

# Build de produção
npm run build

# Servidor de desenvolvimento
npm run dev
```

## Arquivos Importantes

### Core
- `src/lib/ordax/game-genome/index.ts` - Exports principais
- `src/lib/ordax/game-genome/extract-genome.ts` - Extração
- `src/lib/ordax/game-genome/apply-genome.ts` - Aplicação
- `src/lib/ordax/game-genome/compare-genomes.ts` - Comparação

### UI
- `src/components/ordax/GenomeViewer.tsx` - Componente de visualização
- `src/components/ordax/RemixDialog.tsx` - Integração no remix
- `src/components/ordax/StudioPreviewPanel.tsx` - Aba genome

### Testes
- `src/lib/ordax/game-genome/genome.test.ts` - 10 testes

### Docs
- `LEIA_PRIMEIRO_FASE10.md` - Este arquivo
- `FASE10_CANONICAL_GAME_GENOME.md` - Docs técnicas
- `FASE10_UI_GUIDE.md` - Guia de UI
- `FASE10_INTEGRATION_COMPLETE.md` - Integração
- `FASE10_FINAL_STATUS.md` - Status final

## Conclusão

**Fase 10 está completa e pronta para uso.**

### O Que Você Ganha
- ✅ Visibilidade da estrutura de jogos
- ✅ Comparação antes de aceitar mudanças
- ✅ Versionamento de jogos
- ✅ Compartilhamento de designs
- ✅ Debug mais fácil
- ✅ Aprendizado mais rápido

### Como Começar
1. Abra um jogo no Studio
2. Clique na aba "Genome"
3. Explore a estrutura
4. Faça um remix e veja a comparação
5. Experimente!

---

**Status**: ✅ 100% COMPLETO  
**Testes**: ✅ 69/69 PASSANDO  
**Build**: ✅ SEM ERROS  
**Docs**: ✅ COMPLETA  

**Próximo Passo**: Use e explore! 🚀

---

**Documentação Completa**:
- 📖 `FASE10_CANONICAL_GAME_GENOME.md` - Técnica
- 🎨 `FASE10_UI_GUIDE.md` - UI
- 🔧 `FASE10_INTEGRATION_COMPLETE.md` - Integração
- 📊 `FASE10_FINAL_STATUS.md` - Status
