# Ordax Code‑First Template — Template Mutation Guide (v1)

Este documento é um **mapa semântico para IA (Code Mutator Agent)**. Ele define **onde** cada tipo de mudança deve acontecer no jogo code‑first e quais **padrões canônicos de mutação** são permitidos.

> Objetivo: a IA gerar `CodeSemanticPatch` **correto, previsível e seguro**, sem espalhar lógica em arquivos errados e sem inventar diretórios.

---

## 0) Regra de ouro: nunca inventar diretórios

Todo patch **só pode criar arquivos** dentro destes diretórios canônicos (abaixo), ou atualizar `codeGame.ts`.

### Diretórios canônicos (permitidos)

Dentro de `/vfs/games/<gameId>/` (ou `src/games/<gameId>/` no repo), **somente**:

- `codeGame.ts` *(obrigatório; ponto de entrada)*
- `systems/` *(sistemas do jogo; integração via setup/collector)*
- `entities/` *(modelos/estruturas de entidades; integração via setup/collector)*
- `ui/` *(HUD e UI React; integração via setup/collector + UISystem)*
- `state/` *(máquina de estados / lifecycle; start → playing → gameover)*
- `input/` *(mapeamento de input/controles)*
- `audio/` *(mapeamento de trilhas/SFX; integra com AudioSystem)*
- `spawn/` *(regras de spawn/waves/spawners)*
- `utils/` *(helpers puros e determinísticos)*
- `_derived/` *(artefatos gerados; pode sobrescrever)*

**Proibido:** criar qualquer outro diretório.

---

## 1) Onde adicionar sistemas novos

### Arquivos
- Criar o sistema em `systems/<Foo>System.ts`.

### Registro (obrigatório)
- Registrar no `setup(ctx)` do `codeGame.ts` via `collector.useSystem("FooSystem")`.

### Padrão canônico (mutação)
1) `create_file /systems/FooSystem.ts`
2) `update_file /codeGame.ts` adicionando `collector.useSystem("FooSystem")`

---

## 2) Onde adicionar entidades novas

### Arquivos
- Criar a entidade em `entities/<Thing>.ts` (tipos/config) ou `entities/<Thing>.tsx` se for UI React (evite).

### Registro (obrigatório)
- Registrar no `setup(ctx)` do `codeGame.ts` via `collector.addEntity({ ... })`.

### Padrão canônico (mutação)
1) `create_file /entities/Thing.ts`
2) `update_file /codeGame.ts` adicionando um `collector.addEntity(...)` correspondente.

---

## 3) Onde adicionar HUD/UI

### Arquivos
- Implementar UI em `ui/HUD.tsx` (ou `ui/<Component>.tsx`).

### Registro (obrigatório)
- Registrar no `setup(ctx)` do `codeGame.ts` (duas opções, escolha uma e seja consistente):
  - **Opção A (recomendada):** registrar uma entidade `type: "ui"` via `collector.addEntity({ type: "ui", ...props })` e o runtime associa `ui/HUD.tsx`.
  - **Opção B:** registrar explicitamente um `collector.addEntity({ id: "ui", type: "ui", props: { component: "HUD" } })`.

### Padrão canônico (mutação)
1) `create_file /ui/HUD.tsx`
2) `update_file /codeGame.ts` registrando a UI na coleta.

---

## 4) Onde adicionar estados de jogo (lifecycle)

### Contrato constitucional (NUNCA violar)
- Estados: `start` → `playing` → `gameover`
- Transições: `start->playing`, `playing->gameover`, `gameover->restart`
- Controles mínimos: `start_game`, `restart_game`

### Arquivos
- Máquina de estados e regras em `state/lifecycle.ts` (ou `state/gameState.ts`).

### Registro (obrigatório)
- `codeGame.ts` **deve** continuar representando o entrypoint e chamar/usar a camada `state/` no runtime (não no extract).

### Padrão canônico (mutação)
1) `create_file /state/lifecycle.ts`
2) `update_file /codeGame.ts` para usar `state/lifecycle.ts`.

---

## 5) Onde adicionar input

### Arquivos
- Mapeamento/normalização de input em `input/input.ts`.

### Registro
- `codeGame.ts` importa e usa `input/` **apenas no runtime** (modo `run`).

### Padrão canônico
1) `create_file /input/input.ts`
2) `update_file /codeGame.ts` para consumir o input.

---

## 6) Onde adicionar áudio

### Arquivos
- Catálogo de sons/músicas em `audio/audio.ts`.

### Registro
- `codeGame.ts` registra `collector.useSystem("AudioSystem")` (se já não existir).
- `collector.setAudio({ ... })` (no extract) apenas descreve o catálogo; tocar sons é runtime.

### Padrão canônico
1) `create_file /audio/audio.ts`
2) `update_file /codeGame.ts` para registrar o áudio e o AudioSystem.

---

## 7) Onde adicionar lógica de spawn

### Arquivos
- Regras de spawn em `spawn/spawn.ts`.

### Registro
- `codeGame.ts` registra `collector.useSystem("SpawnerSystem")` (se aplicável).
- `spawn/` é consumido no runtime; no extract apenas descreva entidades/spawners via `collector.addEntity(...)`.

### Padrão canônico
1) `create_file /spawn/spawn.ts`
2) `update_file /codeGame.ts` para integrar spawn.

---

## 8) Regras de integridade do patch (guard‑rails)

Um `CodeSemanticPatch` válido **DEVE**:

1) Criar/editar apenas em paths permitidos (diretórios canônicos acima)
2) Se criar arquivo em `systems/`, `entities/`, `ui/`, `state/`, `input/`, `audio/` ou `spawn/`, também **DEVE** incluir um `update_file` em `/codeGame.ts` no mesmo patch (registro)
3) Nunca deletar `/codeGame.ts`
4) Nunca mover arquivos entre diretórios (rename somente no mesmo diretório)
