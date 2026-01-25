# FASE 10: CANONICAL GAME GENOME ✅

## Status: IMPLEMENTADO

## Objetivo
Criar uma representação canônica e determinística da identidade de cada jogo.

## O Que É um Game Genome?

Um **Game Genome** é uma representação estrutural e determinística da identidade de um jogo. É como o DNA do jogo - contém toda a informação essencial sobre o que o jogo é, sem os detalhes de implementação.

### Analogia Biológica
```
DNA Biológico → Organismo
Game Genome → RuntimeSpec

Dois organismos com mesmo DNA são idênticos
Dois jogos com mesmo Genome são equivalentes
```

## Estrutura do GameGenome

```typescript
interface GameGenome {
  // Identificação
  genre: string;                    // Ex: 'topdown-shooter'
  
  // Temas visuais/narrativos
  themes: string[];                 // Ex: ['zombie', 'medieval']
  
  // Modificadores de gameplay
  difficulty: 'easy' | 'normal' | 'hard';
  speed: 'slower' | 'normal' | 'faster';
  boss: boolean;
  
  // Progressão
  progression: {
    winCondition: 'score' | 'time' | 'survival' | 'collection';
    winTarget?: number;
    loseCondition: 'health' | 'time' | 'capture';
    loseTarget?: number;
  };
  
  // Tipos de inimigos
  enemyTypes: Array<{
    archetype: 'basic' | 'fast' | 'tank' | 'ranged' | 'boss';
    count: number;
    behavior: 'chase' | 'patrol' | 'ranged' | 'boss';
  }>;
  
  // Mecânicas
  mechanics: string[];              // Ex: ['shooting', 'collection', 'health']
  
  // UI
  ui: {
    hud: string[];                  // Ex: ['health', 'score', 'timer']
    screens: string[];              // Ex: ['game', 'victory', 'gameover']
  };
  
  // Metadata
  version: string;
  timestamp: number;
}
```

## Operações Principais

### 1. extractGenome(runtimeSpec): GameGenome

Extrai o genoma de um RuntimeSpec.

**Características**:
- ✅ Totalmente determinístico
- ✅ Sem heurísticas frágeis
- ✅ Mesmo input → Mesmo output (exceto timestamp)

**Exemplo**:
```typescript
const preset = createSpaceSurvivalPreset();
const genome = extractGenome(preset.runtimeSpec);

// Resultado:
{
  genre: 'topdown-shooter',
  themes: ['space'],
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
  mechanics: ['movement', 'combat', 'collection', 'spawning', 'health', 'score'],
  ui: {
    hud: ['health', 'score', 'timer'],
    screens: ['game', 'victory', 'gameover']
  }
}
```

### 2. applyGenome(runtimeSpec, genome): RuntimeSpec

Aplica um genoma a um RuntimeSpec base.

**Características**:
- ✅ Usa Remix Engine internamente
- ✅ Validate + Autofill sempre rodam
- ✅ Gera patch semântico

**Exemplo**:
```typescript
const base = createSpaceSurvivalPreset();
const targetGenome = {
  genre: 'topdown-shooter',
  themes: ['zombie', 'medieval'],
  difficulty: 'hard',
  speed: 'faster',
  boss: true,
  // ... resto do genoma
};

const result = applyGenome(base.runtimeSpec, targetGenome);
// result é um RuntimeSpec com as características do targetGenome
```

### 3. compareGenomes(from, to): GenomeDiff

Compara dois genomas e retorna as diferenças.

**Exemplo**:
```typescript
const game1 = extractGenome(spaceGame);
const game2 = extractGenome(zombieGame);

const diff = compareGenomes(game1, game2);

// Resultado:
{
  themes: {
    added: ['zombie'],
    removed: ['space']
  },
  difficulty: null,  // Sem mudança
  speed: null,       // Sem mudança
  boss: { from: false, to: true },
  // ... outras diferenças
}
```

## Propriedade Fundamental

### extract(apply(G)) ≈ G

**Significado**: Se você aplicar um genoma e depois extrair, deve obter um genoma equivalente.

**Teste**:
```typescript
const original = extractGenome(game);
const applied = applyGenome(baseGame, original);
const extracted = extractGenome(applied);

// Core properties devem ser iguais
expect(extracted.difficulty).toBe(original.difficulty);
expect(extracted.speed).toBe(original.speed);
expect(extracted.boss).toBe(original.boss);
```

**Status**: ✅ Testado e funcionando

## Casos de Uso

### 1. Comparação Estrutural
```typescript
// Dois jogos podem ser comparados estruturalmente
const genome1 = extractGenome(game1);
const genome2 = extractGenome(game2);

if (genome1.themes === genome2.themes && 
    genome1.difficulty === genome2.difficulty) {
  console.log('Jogos similares!');
}
```

### 2. Recriação de Jogo
```typescript
// Um jogo pode ser recriado a partir do genoma
const savedGenome = extractGenome(originalGame);

// Mais tarde...
const recreated = applyGenome(baseTemplate, savedGenome);
// recreated é equivalente ao originalGame
```

### 3. Remix sem Texto
```typescript
// Remix pode operar sem texto humano
const genome = extractGenome(currentGame);
genome.difficulty = 'hard';
genome.boss = true;

const remixed = applyGenome(currentGame, genome);
// Jogo remixado sem precisar de texto
```

### 4. Versionamento de Jogos
```typescript
// Salvar versões de um jogo
const v1 = extractGenome(game);
// ... fazer mudanças ...
const v2 = extractGenome(game);

const diff = compareGenomes(v1, v2);
console.log('Mudanças:', formatGenomeDiff(diff));
```

## Detecção de Temas

O sistema detecta temas automaticamente por sprites:

```typescript
Zombie: 🧟, 🧟‍♂️, 🧟‍♀️
Space: 🚀, ☄️, 🛸, 👽
Medieval: 🗡️, 👺, 💀, 🏰, 🐉
Ninja: 🥷, 👹, ⚔️
Pirate: 🏴‍☠️, 🦜, ⚓
Robot: 🤖, 👾, 🔧
```

## Detecção de Dificuldade

Baseado em stats de inimigos:

```typescript
Easy: avgHealth < 40 && avgDamage < 12
Normal: valores médios
Hard: avgHealth > 70 && avgDamage > 15
```

## Detecção de Velocidade

Baseado em velocidades médias:

```typescript
Slower: avgSpeed < 90
Normal: 90 <= avgSpeed <= 150
Faster: avgSpeed > 150
```

## Classificação de Inimigos

```typescript
Boss: behavior === 'boss' || health > 300
Fast: speed > 120
Tank: health > 80
Ranged: behavior === 'ranged'
Basic: padrão
```

## UI Components

### GenomeViewer

Componente para visualizar genomas:

```typescript
<GenomeViewer genome={genome} />
<GenomeViewer genome={genome} compact />
```

**Modos**:
- Normal: Card completo com todos os detalhes
- Compact: Badge inline com resumo

## Arquivos Criados

### Core
1. `src/lib/ordax/game-genome/index.ts`
2. `src/lib/ordax/game-genome/extract-genome.ts`
3. `src/lib/ordax/game-genome/apply-genome.ts`
4. `src/lib/ordax/game-genome/compare-genomes.ts`
5. `src/lib/ordax/game-genome/format-genome.ts`
6. `src/lib/ordax/game-genome/genome.test.ts`

### UI
7. `src/components/ordax/GenomeViewer.tsx`

### Documentação
8. `FASE10_CANONICAL_GAME_GENOME.md`

## Testes

### Cobertura
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

10/10 testes passando
```

### Executar
```bash
npm test -- genome
```

## Garantias Cumpridas

### ✅ Nenhum contrato muda
- Usa contratos existentes
- Sem modificações em schemas
- Compatibilidade total

### ✅ Nenhum system muda
- Usa systems existentes
- Apenas extrai/aplica valores
- Sem novos systems

### ✅ Backward compatible
- Funciona com todos os jogos existentes
- Não quebra código antigo
- Adiciona funcionalidade, não remove

### ✅ extract(apply(G)) ≈ G
- Propriedade testada e validada
- Core properties preservadas
- Determinismo garantido

## Critério de Sucesso ✅

### 1. Dois jogos podem ser comparados estruturalmente
```typescript
const diff = compareGenomes(game1, game2);
console.log(hasDifferences(diff)); // true/false
```
✅ Implementado e testado

### 2. Um jogo pode ser recriado a partir do genoma
```typescript
const genome = extractGenome(original);
const recreated = applyGenome(base, genome);
// recreated ≈ original
```
✅ Implementado e testado

### 3. Remix pode operar sem texto humano
```typescript
const genome = extractGenome(game);
genome.difficulty = 'hard';
const remixed = applyGenome(game, genome);
```
✅ Implementado e testado

### 4. Sem prompt adicional
✅ Tudo funciona programaticamente

## Próximos Passos Possíveis

### Expansões
1. **Genome Library**: Biblioteca de genomas salvos
2. **Genome Breeding**: Combinar genomas (crossover genético)
3. **Genome Mutation**: Mutações aleatórias controladas
4. **Genome Evolution**: Evolução de genomas por fitness
5. **Genome Sharing**: Compartilhar genomas entre usuários

### Melhorias
1. **More Archetypes**: Mais tipos de inimigos
2. **More Mechanics**: Detectar mais mecânicas
3. **Genome Compression**: Compactar genomas
4. **Genome Validation**: Validar genomas antes de aplicar
5. **Genome Diff Visualization**: Visualizar diffs graficamente

## Conclusão

**Fase 10 está 100% implementada e funcional.**

### Resultados
- ✅ GameGenome type definido
- ✅ extractGenome determinístico
- ✅ applyGenome com Remix Engine
- ✅ compareGenomes funcional
- ✅ UI components criados
- ✅ 10 testes passando
- ✅ Propriedade extract(apply(G)) ≈ G validada

### Impacto
**Jogos agora têm uma identidade canônica que pode ser extraída, comparada, aplicada e compartilhada.**

---

**Documentação**: `FASE10_CANONICAL_GAME_GENOME.md`  
**Core**: `src/lib/ordax/game-genome/`  
**UI**: `src/components/ordax/GenomeViewer.tsx`  
**Testes**: `npm test -- genome`
