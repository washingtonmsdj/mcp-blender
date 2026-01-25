# Ordax Code‑First Template — Canonical Contract (v1)

Este documento **congela** o contrato mínimo e estável do template code‑first em `src/games/_template/`.

> Objetivo: jogos “nível Stellar Vanguard” terem **código TypeScript/Canvas como fonte de verdade**. O `runtimeSpec` (OrdaxSpec) é **artefato derivado**.

---

## 1) Estrutura do template

### 1.1 Arquivos obrigatórios (protegidos)

**Diretório:** `src/games/_template/`

- `src/games/_template/index.ts`
- `src/games/_template/runtime/types.ts`
- `src/games/_template/runtime/defineGame.ts`
- `src/games/_template/runtime/extractRuntimeSpecFromGameCode.ts`
- `src/games/_template/CONTRACT.md` (este arquivo)

**Regra:** nenhum jogo pode depender de arquivos fora desses como “API do template”.

### 1.2 Diretórios reservados

Reservados (semântica fixa):

- `src/games/_template/` — **API canônica** do template (protegido)
- `src/games/_template/runtime/` — runtime helpers canônicos (protegido)

Para jogos (por convenção do projeto):

- `src/games/<gameId>/` — implementação de um jogo code‑first no repo (mutável via humano; mutável via code‑mutator **apenas** dentro de regras abaixo)
- `games/*.md` — benchmarks/documentação humana (não é API)

### 1.3 Diretórios/arquivos que o code‑mutator pode criar

Permitido criar/editar **somente**:

- `src/games/<gameId>/**` (com `<gameId>` sendo `kebab-case`)

Proibido criar/editar (reservado/fora do escopo do template):

- `src/games/_template/**`
- `src/lib/**`, `src/components/**`, `supabase/**`, `src/pages/**` *(a menos que uma tarefa explícita libere)*

---

## 2) Política de arquivos: protegidos vs mutáveis vs gerados

### 2.1 Protegidos (NUNCA mutáveis pelo chat)

- Tudo em `src/games/_template/**`
- Este contrato

### 2.2 Mutáveis (podem ser alterados por code‑mutator)

- `src/games/<gameId>/**` **exceto** arquivos marcados como “gerados”

### 2.3 Gerados (o chat pode sobrescrever, mas deve tratar como output)

- Artefatos derivados de projeção (convenção):
  - `src/games/<gameId>/_derived/runtimeSpec.ordax.json` *(se/ quando existir)*
  - arquivos dentro de `src/games/<gameId>/_derived/**`

**Regra:** código fonte humano deve ficar fora de `_derived/`.

---

## 3) API pública canônica (todo jogo deve exportar)

### 3.1 Ponto de entrada

Cada jogo code‑first deve exportar **um módulo canônico** (nome livre, mas padrão recomendado: `codeGame.ts`) que exporta um `CodeGameModule` via `defineGame()`:

```ts
import { defineGame } from "@/games/_template";

export const myGame = defineGame({
  meta: { id: "my-game", title: "My Game", description: "...", gameType: "shooter" },
  setup: (ctx) => { /* ... */ },
});
```

### 3.2 `defineGame(module)`

- **Propósito:** congelar a forma do export e habilitar validações estáticas.
- **Comportamento:** identidade (retorna o mesmo objeto). Não deve ter side‑effects.

### 3.3 `CodeGameModule`

Obrigatório:

- `meta`: `{ id, title, description, gameType }`
- `setup(ctx)`

Opcional (reservado para evolução sem quebrar o contrato):

- `hooks?: { onMount?, onUnmount? }` *(ainda não utilizado pelo runtime do Studio; apenas contrato)*

---

## 4) Contrato do “modo extract”

### 4.1 O que **pode** rodar em `extract`

- Definições determinísticas: tabelas de constantes, configs, listas de entidades/sistemas
- Chamadas a `collector.*` para registrar:
  - `useSystem(name)`
  - `addEntity(entity)`
  - `setVisual(visual)`
  - `setAudio(audio)`
  - `setGravity(gravity)`

### 4.2 O que **NÃO pode** rodar em `extract` (efeitos colaterais proibidos)

- `requestAnimationFrame` / loops / timers (`setInterval`, `setTimeout`)
- listeners globais (`window.addEventListener`, `document.addEventListener`)
- áudio (`AudioContext`, tocar sons)
- network (`fetch`, websockets)
- mutação de estado global do app (localStorage, indexedDB, etc.)

### 4.3 Falha/penalidade

Se `setup({ mode: "extract" })` tentar rodar efeitos colaterais, o contrato considera isso **bug do jogo**.

---

## 5) Contrato do extrator `extractRuntimeSpecFromGameCode(game)`

### 5.1 O que deve coletar (mínimo)

- `meta.gameType/title/description`
- `systems`: nomes canônicos de systems
- `scene.entities`: lista de `OrdaxEntity` (id, type, x, y, w, h, props?)
- `scene.gravity`
- `visual` e `audio` (opcionais)

### 5.2 Como distingue setup vs runtime

- O extrator **não executa runtime**.
- Ele chama apenas `game.setup({ mode: "extract", collector })`.
- Qualquer lógica de loop/render/input deve ser **guardada** atrás de `ctx.mode === "run"`.

### 5.3 Como projeta `systems/entities/UI/lifecycle`

- `systems`: vem exclusivamente de `collector.useSystem()`
- `entities`: vem exclusivamente de `collector.addEntity()`
- `UI`: por enquanto é projetada como entidades `type: "ui"` (se o jogo registrar)
- `lifecycle`: **não é representado no `OrdaxSpec` atual**; o contrato exige apenas que o jogo possua `start/play/gameover` internamente (no seu runtime), mas o extrator não prova isso.

---

## 6) Invariantes

- **Fonte de verdade:** TypeScript do jogo.
- `runtimeSpec` é derivado e pode ser regenerado.
- `setup(extract)` deve ser *puro* e determinístico.
- O template `_template` é API pública e **não deve quebrar compatibilidade** sem bump de versão do contrato.
