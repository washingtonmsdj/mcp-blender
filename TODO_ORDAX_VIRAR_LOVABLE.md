# TODO / SPEC / TASKS — Transformar o Ordax em um “Lovable de Jogos”

**Objetivo**: elevar o Ordax Studio do nível “spec + retângulos” para um **gerador de jogos com qualidade perceptível (AAA no viewer)**, com **geração consistente**, **auto‑correção**, **suporte real a gêneros**, e um fluxo de iteração próximo do que torna o Lovable forte.

> **Escopo escolhido (conforme você respondeu)**
> - Prioridade: **Equilíbrio por fases** (runtime + IA em paralelo)
> - “Aprender a cada geração”: **Validação + auto‑correção** (pipeline de qualidade antes do preview)
> - Gêneros alvo primeiro: **Platformer**, **Shooter arcade**, **Puzzle**
> - Assets: **URLs + fallback procedural**

---

## 0) Definições rápidas (para não confundir)

### O que o Lovable faz “melhor” (em termos de resultado)
1. **Output é código** → consegue criar mecânicas novas ao invés de forçar um schema.
2. **Loop de iteração/polimento muito curto** (ex.: Visual Edits + diffs) → melhora incremental sem quebrar tudo.
3. **Geração multi‑arquivo e refactors** → converte pedidos em mudanças estruturais reais.

### O que o Ordax precisa alcançar
1. **Specs ricas e válidas sempre** (sem “jogo pobre”).
2. **Runtime que “carrega o jogo” com estética forte e feedback** (mesmo sem assets).
3. **Templates canônicos por gênero + validação/autofix** para consistência.
4. **Ferramentas de edição no viewer** (seleção/inspector), aproximando do “visual edit”.

Referência comparativa: `COMPARACAO_LOVABLE_VS_ORDAX_STREETFIGHTER.md`.

---

## 1) North Star (produto)

### 1.1 Experiência alvo
Quando o usuário pede “Crie um jogo de X”:
- o Ordax gera uma spec **com gameplay loop completo** (objetivo → desafio → progressão → game over/new game),
- com **visual e áudio mínimos** prontos,
- com **inimigos/NPCs/obstáculos** (quando fizer sentido),
- com **UI de HUD** e feedback,
- e se a spec vier incompleta, o sistema **auto‑corrige** antes do preview.

### 1.2 Critérios de sucesso (mensuráveis)
**Qualidade de geração**
- (GQ1) 90%+ das gerações resultam em jogo **jogável** (sem travar / sem entidade fora do mundo / sem ids duplicados).
- (GQ2) 80%+ das gerações incluem pelo menos: **HUD + objetivo + progressão**.

**Qualidade de runtime/viewer**
- (RQ1) 60 FPS estável em desktop; 45+ em mobile.
- (RQ2) Mundo com **recorte/letterbox** perfeito (nada aparece fora).
- (RQ3) Visual não‑placeholder: background + parallax + VFX básicos + player com silhueta rica.

**Confiabilidade**
- (CQ1) Toda spec passa por **lint/validação** e por um **autofix determinístico**.
- (CQ2) Logs claros no debug (o que foi corrigido e por quê).

---

## 2) Problemas atuais (gaps concretos)

### 2.1 Geração “pobre” / inconsistência
- Prompt do streaming é mais curto e tende a produzir specs piores.
- Falta um **pipeline de validação + auto‑fix** antes de renderizar.

### 2.2 Runtime limitado por gênero
- Platformer/shooter/racing têm fallback procedural, mas:
  - faltam **pacotes de gameplay** por gênero (spawner padrão, inimigos padrões, objetivo/pacing).
  - falta **sistema de tiles/solids** (platformer) e **wave spawner** (shooter).

### 2.3 Assets
- Suporte de sprite existe no tipo, mas precisa virar **pipeline de asset real**:
  - preload, fallback, erro visível, spritesheet/anim
  - áudio consistente (music + sfx)

---

## 3) Arquitetura alvo (alto nível)

### 3.1 Pipeline de geração (novo)
1. **Entrada** (mensagens + currentSpec)
2. **Geração IA** (streaming ou não)
3. **Spec Lint** (validador)
4. **Auto‑Fix** (corrige e registra diffs)
5. **Normalize** (defaults e compat)
6. **Runtime Preview** (viewer)
7. **Telemetria local** (resultado do lint/autofix + “jogável?”)

> “Aprender por geração” aqui significa: o Ordax melhora a consistência **pela camada determinística** (lint/autofix/templates), não por “treinar o modelo”.

### 3.2 Templates canônicos por gênero (fonte de verdade)
Criar specs-base **curadas manualmente** para:
- platformer
- shooter
- puzzle

O modelo **edita em cima** do template (em vez de inventar do zero), e o autofix garante invariantes.

---

## 4) Backlog por Fases (com critérios de aceite)

> Convenção: **P0**=essencial, **P1**=alto valor, **P2**=melhoria.

### Fase A — Qualidade de geração (P0)

#### A1) Unificar prompts (streaming vs não-streaming) (P0)
**Objetivo**: mesma qualidade de regra/whitelist/saída em ambos.

**Tasks**
- [ ] Extrair um “prompt-base” compartilhado para `game-ai-chat` e `game-ai-chat-stream`.
- [ ] Garantir que ambos exigem: `visual.theme` (HSL), `visual.background.layers`, `scene.entities`, `systems`.
- [ ] Garantir que o streaming não “relaxa” as regras.

**Aceite**
- Prompt streaming e não-streaming produzem `OrdaxSpec` com mesmas invariantes em 10 prompts de teste.

#### A2) Spec Linter + Auto‑Fix determinístico (P0)
**Objetivo**: “sempre renderizável” + sem bugs comuns.

**Auto-fix mínimo (P0)**
- IDs duplicados → renomear
- `systems` inválidos → mapear para os suportados (ou remover)
- `entities` vazias → injetar player + 1 objetivo/obstáculo
- entidades fora do mundo → clamp
- sprites inválidos → fallback procedural

**Tasks**
- [ ] Criar `src/lib/ordax/spec-lint/` com:
  - `lintOrdaxSpec(spec) -> issues[]`
  - `autoFixOrdaxSpec(spec, issues) -> { spec, fixes[] }`
- [ ] Mostrar no “AI Debug” um resumo: `issues` + `fixes`.

**Aceite**
- Em 20 gerações (10 streaming/10 fallback), 0 crashes; 0 entidades fora do mundo; 0 ids duplicados.

#### A3) Templates canônicos por gênero (P0)
**Objetivo**: base curada impede “jogo pobre”.

**Tasks**
- [ ] Criar `src/lib/ordax/templates/` com 3 templates (platformer/shooter/puzzle).
- [ ] Seleção de template:
  - por `gameType` inferido
  - fallback por prompt (keywords)
- [ ] Prompt instrui: “edite o template, não crie do zero”.

**Aceite**
- “Crie um platformer”, “Crie um shooter”, “Crie um puzzle” geram jogo com loop mínimo (objetivo+HUD+progressão).

---

### Fase B — Runtime/Viewer AAA (P0/P1)

#### B1) Viewer: recorte/letterbox + bounds consistentes (P0)
**Objetivo**: nada fora da área de jogo, sem bugs visuais.

**Tasks**
- [ ] Garantir `ctx.clip` no mundo e letterbox consistente (já iniciado — manter como invariável).
- [ ] Criar um “WorldSpace” helper para clamp e conversões.

**Aceite**
- Nenhuma entidade/sprite/UI do mundo é desenhada fora do frame.

#### B2) Pacotes visuais por gênero (P0)
**Objetivo**: visual imediatamente “não protótipo” em platformer/shooter/puzzle.

**Tasks (Platformer)**
- [ ] Fundo com parallax e camada “ground”.
- [ ] Tiles simples (mesmo procedural) e colisões sólidas básicas.

**Tasks (Shooter)**
- [ ] Starfield/parallax + efeitos de tiro (particles) + impacto.
- [ ] Explosão procedural + screen shake.

**Tasks (Puzzle)**
- [ ] Grade (grid) + highlight + feedback (animações leves e som).

**Aceite**
- Cada gênero tem “assinatura visual” distinta e efeitos mínimos.

#### B3) Gameplay packs por gênero (P0/P1)
**Objetivo**: gerar “jogo” e não “cena”.

**Platformer pack (P0)**
- [ ] moedas + score + condição de vitória
- [ ] inimigo simples (patrol) opcional

**Shooter pack (P0)**
- [ ] wave spawner + dificuldade progressiva
- [ ] powerup simples

**Puzzle pack (P1)**
- [ ] 2-3 mecânicas base (ex.: match, sokoban-lite, memory)

**Aceite**
- Em cada template, existe objetivo + progressão + game over/vitória.

---

### Fase C — Assets (URLs + fallback) (P0/P1)

#### C1) Pipeline de assets robusto (P0)
**Objetivo**: sprites e áudio via URL funcionarem sempre (ou caírem em fallback com erro claro).

**Tasks**
- [ ] Loader de imagem com cache + timeout + fallback.
- [ ] Suporte a spritesheet + animações mínimas por entidade.
- [ ] Loader de áudio com volumes e falhas silenciosas (sem travar).

**Aceite**
- URLs quebradas não quebram o jogo; apenas caem no procedural e logam motivo.

#### C2) Biblioteca de presets (P1)
**Objetivo**: facilitar assets sem obrigar upload.

**Tasks**
- [ ] Presets: “8-bit pack”, “sci-fi pack”, “neon pack” → apenas URLs.

---

### Fase D — Editor/UX tipo “Lovable-like” (P1/P2)

#### D1) Inspector visual no canvas (P1)
**Objetivo**: selecionar entidade e editar propriedades sem abrir JSON.

**Tasks**
- [ ] Click-to-select no canvas + outline.
- [ ] Painel: position/size/type/props + apply.
- [ ] Undo (1 nível) de edição.

**Aceite**
- Usuário consegue ajustar rapidamente player/enemy/objetos e ver no runtime.

#### D2) Diff explicável + “aplicar mudanças com segurança” (P2)
**Objetivo**: tornar edição incremental previsível.

**Tasks**
- [ ] Mostrar “o que mudou na spec” após IA (diff resumido).
- [ ] Botão: “reverter última geração”.

---

## 5) Tarefas transversais (qualidade, testes, observabilidade)

### T1) Suite de testes para spec pipeline (P0)
- [ ] Testes unitários para linter/autofix/normalize.
- [ ] Fixtures de prompts e snapshots de spec.

### T2) Diagnóstico de runtime (P0)
- [ ] Debug HUD sempre mostrar: systems ativos, entities count, FPS, e “fixes aplicados”.

### T3) Telemetria local (P1)
- [ ] Registrar (local/DB) métricas: issues por geração, fixes aplicados, “jogável”.

---

## 6) Ordem recomendada de implementação (para máximo impacto)
1. **A1 Unificar prompts**
2. **A2 Linter + Auto-fix**
3. **A3 Templates por gênero**
4. **B2/B3 Packs de gênero (platformer/shooter primeiro)**
5. **C1 Pipeline de assets**
6. **D1 Inspector visual**

---

## 7) Definição de pronto (“Ordax = mínimo do Lovable”) — checklist
- [ ] Gera platformer/shooter/puzzle com loop completo
- [ ] Visual forte + parallax + VFX (sem assets) e suporte a URLs com fallback
- [ ] Validação/autofix impede specs inválidas
- [ ] Debug explica correções e performance
- [ ] Ferramenta de edição visual mínima (inspector)
