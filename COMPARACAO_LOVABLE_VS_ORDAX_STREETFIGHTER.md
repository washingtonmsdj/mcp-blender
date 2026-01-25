# Comparação: Lovable vs Ordax Studio (Geração de Jogos)

> **Objetivo deste documento**: comparar **RESULTADOS** e **fluxos** de geração (e iteração) entre **Lovable** e **Ordax Studio**, apontando **por que o Lovable parece “melhor”** e **quais gaps concretos** existem no Ordax.
>
> **Importante (transparência)**: o Lovable não publica o “prompt interno completo” do editor nem detalhes proprietários do pipeline (por motivos óbvios de IP/segurança). Portanto:
> - eu cito **fontes oficiais públicas** quando existem;
> - quando algo não é divulgado, eu explico como **caixa‑preta**, com base em sinais observáveis e textos públicos.

---

## 1) O que cada produto realmente entrega (diferença de resultado)

### Lovable (resultado típico)
**Entrega**: um projeto **full‑stack** editável (React + Vite + Tailwind + backend integrado) com múltiplos arquivos, UI completa e capacidade de crescer para qualquer lógica porque **o output é código**.

Sinais públicos do “por que parece melhor”:
- Loop de iteração muito curto via **cloud dev servers** + mapeamento DOM→JSX (Visual Edits), permitindo polimento fino sem “quebrar tudo” na mão.
  - Fonte: Blog oficial “Visual Edits” (Lovable) — https://lovable.dev/blog/visual-edits
- Plataforma documentada como **AI-powered full-stack app builder** (não apenas gerador de config).
  - Fonte: Docs (visão geral) — https://docs.lovable.dev/

### Ordax Studio (resultado típico)
**Entrega**: uma **especificação** (`OrdaxSpec`) interpretada por um runtime (canvas) com módulos (systems) fixos.

Na prática, isso tende a gerar:
- jogo “rodando” com defaults,
- mas com limites fortes de gênero (ex.: fighting game)
- e com visual/UX dependentes do que o runtime já sabe renderizar.

Evidência no código:
- `OrdaxSpec` é uma estrutura fechada: `gameType`, `systems`, `visual`, `scene.entities`.
  - Fonte (repo): `src/lib/ordax/types.ts`
- O prompt da geração instrui a IA a devolver **APENAS JSON** e lista uma **whitelist** de módulos permitidos.
  - Fonte (repo): `supabase/functions/game-ai-chat/index.ts` (função `systemPrompt()`)

**Resumo brutal**:
- Lovable: “quero um Street Fighter” → você pode acabar com um mini-engine de luta escrita em TS/React.
- Ordax: “quero um Street Fighter” → você acaba com *um jogo que tenta imitar luta usando entidades e sistemas genéricos*, porque o runtime não possui, hoje, primitivas de fighting game.

---

## 2) Diferença arquitetural que causa a diferença de resultado

### Lovable = Code‑First (gera e edita código)
**O que isso habilita**:
- Criar qualquer mecânica nova, desde que seja programável.
- Refatorar, adicionar libs, mudar arquitetura, criar múltiplos arquivos, testes, etc.
- Melhorar o “viewer” porque o viewer é uma app web real: dá para implementar overlay, debug HUD, performance, editor visual, etc.

Evidência pública de pipeline/infra de iteração:
- O post de “Visual Edits” descreve:
  - cloud dev servers instantâneos
  - tagging estável de JSX
  - mapeamento visual → código com AST
  - Fonte: https://lovable.dev/blog/visual-edits

### Ordax = Spec‑First (gera um JSON, runtime interpreta)
**O que isso habilita**:
- Menos risco de “quebrar build” porque não é código arbitrário.
- Mais previsibilidade do runtime (idealmente) e facilidade de “política” do que o modelo pode fazer.

**O custo**:
- Tudo que não estiver representado no schema ou nos modules do runtime vira gambiarra.
- O “nível AAA” depende de **quantidade e qualidade** de módulos e de um runtime rico.

Evidência no código:
- Prompt do Ordax impõe:
  - lista fixa de `gameType` (`platformer|topdown|shooter|puzzle|racing|sports|unknown`)
  - lista fixa de systems (PhysicsSystem, CollisionSystem, ParticleSystem, AnimationSystem, AudioSystem, CameraSystem, AISystem, ScoreSystem, UISystem, TimerSystem, DialogueSystem, InventorySystem, SaveSystem, SpawnerSystem)
  - Fonte (repo): `supabase/functions/game-ai-chat/index.ts`

---

## 3) Como a IA “pensa” em cada um (o que dá para afirmar publicamente)

### Lovable (o que é público)
- O Lovable provê integrações e infraestrutura para IA e projetos na nuvem.
  - Lovable AI (integração): https://docs.lovable.dev/integrations/ai.md
  - Lovable Cloud: https://docs.lovable.dev/integrations/cloud.md

**O que não é divulgado** (e eu não vou inventar):
- prompt interno completo do editor
- heurísticas de seleção de arquivos/patches
- políticas internas de estilo/arquitetura e o conjunto completo de ferramentas do agente

**Inferência segura (caixa‑preta)**:
- O “modo agente” do Lovable opera como editor multi‑arquivo: planeja mudanças e aplica patches (você vê isso na UX e em textos públicos/terceiros).
- O diferencial é o ciclo “gerar → visualizar → editar visualmente → aplicar diffs”.

### Ordax (o que é explícito no repo)
- A IA é instruída via prompt a retornar JSON, com regras de background/tema e whitelist de módulos.
  - `systemPrompt()` em `supabase/functions/game-ai-chat/index.ts`
- Existe o modo “editar”: se `currentSpec` existir, o prompt manda “mantenha o máximo e altere apenas o necessário”.
  - `editHint` em `supabase/functions/game-ai-chat/index.ts`
- O runtime assume um mundo de referência (`WORLD` 800x600 no canvas) e faz fallback procedural.
  - `src/components/ordax/OrdaxCanvas.tsx`

---

## 4) Estudo de caso: “Crie um jogo de Street Fighter”

### 4.1) No Lovable (fluxo típico, baseado em comportamento + fontes públicas)

**Entrada do usuário**: “Crie um jogo de Street Fighter”.

**O que tende a acontecer**:
1. A IA interpreta a intenção como “fighting game 2D” + menu + gameplay loop.
2. Gera **código e UI** (páginas/componentes) e provavelmente:
   - tela inicial (New Game)
   - seleção de personagens
   - HUD (vidas, round, timer)
   - loop do jogo
3. Para o “fighting”: como não há engine fixa, o Lovable pode “inventar” um mini-engine:
   - state machine (idle, walk, jump, crouch, hitstun, block)
   - hitboxes/hurtboxes por frame
   - colisão e resolução
4. Iteração: você pede “melhore animações”, “adicione combos”, “balanceie hitstun”. Como é código, o sistema pode refatorar e aprofundar.

**Por que consegue “qualquer jogo”**:
- porque o output é **código arbitrário**, então a limitação vira “tempo/complexidade” (e bugs), não “schema não suporta”.

**Onde ele é melhor**:
- Loop de polimento (Visual Edits + dev server) descrito publicamente.
  - Fonte: https://lovable.dev/blog/visual-edits

### 4.2) No Ordax Studio (fluxo real, baseado no código do repo)

**Entrada do usuário**: “Crie um jogo de Street Fighter”.

**Pipeline atual**:
1. Frontend manda `messages` (chat) para backend (`game-ai-chat` ou `game-ai-chat-stream`).
2. Backend injeta o prompt `systemPrompt()`:
   - exige JSON
   - define schema
   - restringe `gameType` e `systems` suportados
   - Fonte (repo): `supabase/functions/game-ai-chat/index.ts`
3. Frontend normaliza (`normalizeOrdaxSpec`) para garantir invariantes:
   - cria player se faltar
   - injeta alguns sistemas “úteis”
   - aplica defaults de background
   - Fonte (repo): `src/lib/ordax/normalize.ts`
4. Runtime (`OrdaxCanvas`) renderiza:
   - um mundo 800x600
   - entidades retangulares/fallback procedural
   - spawns simples, colisão simples, HUD simples
   - Fonte (repo): `src/components/ordax/OrdaxCanvas.tsx`

**Resultado provável hoje**:
- o modelo tentará mapear “Street Fighter” para `platformer` ou `topdown` (porque não existe `fighting`).
- vai criar 2 entidades (`player`, `enemy`) e talvez `CollisionSystem`.
- não existe no schema uma noção de:
  - rounds
  - moveset
  - hitbox por frame
  - cancel windows
  - input buffering
  - KO/round end

Ou seja: o resultado tende a ficar “genérico”, mesmo que o texto de descrição esteja bonito.

---

## 5) O que o Lovable tem (ou tende a ter) que o Ordax ainda não tem

### (A) Ferramentas de edição e confiabilidade de mudança
- **Visual Edits**: editar o UI direto no preview e aplicar de volta ao código.
  - Fonte: https://lovable.dev/blog/visual-edits
- Experiência “agente” multi‑arquivo (planejar + aplicar diffs) é parte do produto (observável). (Detalhes internos não são públicos.)

### (B) Output livre (código) vs schema limitado
- Lovable: se falta um módulo, ele **cria o módulo** (código).
- Ordax: se falta um módulo, a IA só consegue:
  - improvisar com props/entidades
  - ou pedir para você “adicionar módulo” (que ainda não existe)

### (C) Asset pipeline e produção
- Lovable: pode baixar assets, gerar imagens, criar componentes, etc. (na prática, mais liberdade por ser app web).
- Ordax: hoje a renderização é focada em canvas e fallback procedural.

---

## 6) O que falta no Ordax (gaps práticos e acionáveis)

### 6.1 Gaps de engine/runtime (para “AAA viewer”)
1. **Game flow como primeiro‑classe**: estados padronizados (New Game / Playing / Pause / Game Over) no runtime.
2. **Validação + Auto‑fix**: detecção de spec incompleto (0 entidades, ids duplicados, systems inválidos) + correção guiada.
3. **Sistema de câmera** consistente: zoom, bounds, shake, follow e “safe area”.
4. **Asset strategy**: spritesheet support real (com fallback), pipeline de audio e particles.

### 6.2 Gaps do schema (para jogos de luta)
Para “Street Fighter” ficar minimamente fiel, faltam primitivas no `OrdaxSpec` como:
- `fighters`: stats, moveset, hurtboxes/hitboxes
- `rounds`: best-of, KO, timeouts
- `input`: buffering, comandos (quarter-circle), prioridade
- `animation`: frames e eventos por frame

Sem isso, a IA sempre “alucina” ou simplifica demais.

### 6.3 Gaps do prompt (controlabilidade)
- O prompt atual tem whitelist de systems, mas o runtime também tem comportamentos fora da whitelist (ex.: specs podem trazer `MovementSystem`, `InputSystem`, `RenderSystem`, etc.).
  - Isso cria inconsistência entre “o que o modelo acha permitido” e “o que o runtime realmente usa”.
- O streaming prompt é bem mais curto do que o não-streaming (menos regras → mais specs pobres).
  - Fonte (repo): `supabase/functions/game-ai-chat-stream/index.ts` vs `game-ai-chat/index.ts`

---

## 7) Por que o Lovable “gera qualquer coisa” e o Ordax parece limitado

### Lovable: generalidade via código
Mesmo quando o pedido exige mecânicas inéditas, o sistema pode:
- criar novos componentes
- criar novas classes
- inventar formatos de dados
- refatorar e evoluir

O limite é mais “complexidade/tempo” do que “não existe no schema”.

### Ordax: generalidade limitada ao que o runtime interpreta
Hoje a generalidade é limitada por:
- game types fixos
- systems permitidos fixos
- desenho procedural/fallback
- ausência de primitivas de alto nível para gêneros específicos

---

## 8) Roadmap recomendado (gaps → ações)

### Curto prazo (melhora de resultado imediato)
1. **Unificar prompt streaming vs não-streaming** (mesmas regras, mesmo schema, mesma whitelist).
2. **Validador + Auto‑fix** no preview (ids duplicados, systems desconhecidos, entidades fora de bounds, etc.).
3. **Pacotes visuais por gameType** (racing/platformer/shooter) com parallax real e VFX (particles + camera shake + UI).

### Médio prazo (habilitar “Street Fighter‑like”)
1. Expandir `OrdaxSpec` com um bloco `combat` (hitboxes, moves, rounds).
2. Criar `CombatSystem` e `InputCommandSystem`.
3. Editor/inspector para hitboxes e timeline (mesmo simples).

### Longo prazo (nível editor “Lovable-like”)
1. “Visual edits” do canvas (selecionar entidade → editar no painel → persistir na spec).
2. Ferramentas de refactor e diff explicável (aplicar mudanças incrementais com segurança).

---

## Referências (citações)

### Lovable (oficial)
- Docs (geral): https://docs.lovable.dev/
- Lovable AI: https://docs.lovable.dev/integrations/ai.md
- Lovable Cloud: https://docs.lovable.dev/integrations/cloud.md
- Planos e créditos: https://docs.lovable.dev/introduction/plans-and-credits.md
- Visual Edits (engenharia): https://lovable.dev/blog/visual-edits

### Ordax (este repositório)
- Prompt/spec: `supabase/functions/game-ai-chat/index.ts`
- Streaming prompt: `supabase/functions/game-ai-chat-stream/index.ts`
- Schema e normalização: `src/lib/ordax/types.ts`, `src/lib/ordax/normalize.ts`
- Runtime: `src/components/ordax/OrdaxCanvas.tsx`
