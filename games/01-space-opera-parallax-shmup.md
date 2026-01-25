# 01 — Space Opera Parallax Shmup (Vertical Shoot 'em Up)

## 1) Visão Geral (Produto)

**Gênero:** Shoot 'em up vertical (shmup) com rolagem contínua.

**Fantasia central:** você pilota uma nave em um universo vivo (space opera), atravessando **biomas espaciais** com um **parallax profundo e dinâmico** (o “hero feature”).

**Pilares:**
- Ação intensa + esquiva
- Leitura clara de projéteis (bullet readability)
- Coleta e gasto de recursos em tempo real (upgrades “on-the-fly”)
- Parallax como espetáculo (camadas, eventos, transições)

## 2) Mecânicas Principais

### Controles da nave
- **Movimento 8 direções** (teclado WASD/Setas)
- **Tiro Principal** (contínuo, fraco)
- **Tiro Especial** (poderoso, recarregável)
- **Dash/Boost** (curto, com recarga)
- **Bomba/Super** (limpa projéteis e causa dano massivo; usos limitados)

### Progressão “On-the-fly”
- Inimigos derrubam **Cristais de Energia**.
- HUD no topo traz um **menu de upgrades instantâneos** (sem pausar):
  - Tiro Duplo
  - Escudo
  - Mísseis Guiados
  - Recarga mais rápida
  - etc.
- O jogador gasta cristais durante a fase para se adaptar.

### Inimigos e padrões
- **Leves:** formações + padrões simples.
- **Pesados:** lentos + rajadas em cone / teleguiados.
- **Chefes** (final de cada bioma): multi-estágio, ataques sincronizados com música e **mudanças teatrais no parallax**.

## 3) Parallax Dinâmico (Destaque)

### Camadas mínimas (4–5)
1. Estrelas distantes (muito lento)
2. Nebulosa (lento)
3. Planetas/formações (médio)
4. Destroços/poeira (rápido)
5. “Foreground” opcional (muito rápido, muito sutil)

### Interatividade (parcial)
- Algumas camadas (destroços) **reagem** a explosões/impactos (offset leve, vibração, empurrão).

### Transições de bioma
- Mudança gradual de paleta + troca progressiva de sprites/elementos.

### Eventos de fundo
- Eventos não-interativos, mas memoráveis:
  - Nave colossal ao longe
  - Explosão de supernova
  - Ruínas que “deslizam” lentamente

## 4) Estética & Som

### Visual
- 2D **HD pixel art** ou **vector estilizado**.
- Nebulosas vibrantes com alto contraste para tiros/explosões.
- Partículas abundantes: explosões, faíscas, fumaça, rastro do dash.

### Áudio
- Música synthwave/eletrônica energética.
- SFX satisfatórios: tiro, explosão, dash, coleta.

## 5) MVP (Escopo)

### Conteúdo
- **3 biomas** únicos (2–3 min cada):
  - Nebulosa Colorida
  - Cinturão de Asteroides
  - Território Inimigo Tecnológico
- **1 chefe por bioma** (multi-estágio)
- **1 nave jogável**
- **3 variações de Tiro Especial** selecionáveis

### Sistemas de produto
- Pontuação + ranking
- Game Over + restart rápido

---

# A) Plano Humano (Contrato / Checklist Semântico)

> Este é o **plano que o usuário revisa** e também o **checklist semântico** que a IA deve obedecer (NEW_GAME / ADD_FEATURE / FIX_BUG).

## A1) Título e gênero
- **Título:** Space Opera Parallax Shmup
- **Gênero:** shmup vertical com rolagem contínua

## A2) Loop principal (obrigatório)
- Começar → entrar em fase → derrotar inimigos → coletar cristais → comprar upgrades → enfrentar chefe → transição de bioma → repetir → game over → restart

## A3) Estados do jogo (obrigatório)
- **Start** (instruções + escolher especial)
- **Playing**
- **Game Over** (pontuação + ranking + instrução de restart)
- **Restart** (reset completo)

## A4) Controles (obrigatório)
- Movimento 8 direções
- Tiro principal (segurar)
- Tiro especial (cooldown)
- Dash (cooldown curto)
- Bomba (recursos limitados)

## A5) Inimigos e combate (obrigatório)
- Existência de inimigos leves e pesados
- Padrões de tiro (simples, cone, teleguiado)
- Chefes multi-estágio ao final de cada bioma

## A6) Tiro (obrigatório)
- Tiro principal contínuo
- Tiro especial recarregável
- Projéteis inimigos claros e legíveis

## A7) Colisão (obrigatório)
- Colisão jogador↔projétil, projétil↔inimigo, jogador↔inimigo
- Dano, invulnerabilidade curta após hit (opcional, mas recomendado)

## A8) HUD/Interface (obrigatório)
- HUD exibindo: vida/escudo, cristais, cooldown dash, cooldown especial, bombas, pontuação
- Menu de upgrades no topo (on-the-fly)

## A9) Progressão (obrigatório)
- Cristais dropados por inimigos
- Upgrades aplicados imediatamente
- Alguma forma de aumento de desafio ao longo do bioma

## A10) Visual (obrigatório)
- Parallax profundo com 4–5 camadas
- Transições suaves de bioma
- Eventos visuais de fundo

## A11) Áudio (se existir)
- Música energética + SFX básicos (tiro, explosão, dash, pickup)

## A12) Auto-adicionados pelo sistema
- Se o plano mencionar itens “grandes” (ex.: chefes multi-estágio), o sistema pode auto-adicionar:
  - Spawner/ondas
  - HUD mínimo
  - Condições de game over e restart

## A13) Limitações conhecidas / Engine gaps
- Se algum item não for suportado (ex.: sincronizar ataque do chefe com música, ou física de destroços complexa), isso deve gerar:
  - `ENGINE_GAP`
  - `warning` claro (“como ficará no MVP e por quê”)

---

# B) Prompt de Entrada (Brief que o usuário fornece)

Use este texto como prompt/base de intenção (intentSpec):

"""
Crie um jogo de tiro vertical (shmup) com rolagem contínua, focado em ação intensa, esquiva e coleta de recursos.

O elemento central é um sistema de parallax profundo e dinâmico, com múltiplas camadas (nuvens interestelares, nebulosas, planetas distantes, destroços) em velocidades diferentes.

Tema: Sci-fi/space opera. Biomas: Nebulosa Colorida, Cinturão de Asteroides, Território Inimigo Tecnológico, Ruínas Alienígenas.

Mecânicas: movimento 8 direções; tiro principal contínuo; tiro especial recarregável; dash com recarga curta; bomba limitada por fase.

Progressão on-the-fly: coletar cristais, gastar em upgrades no topo da tela sem pausar.

Inimigos leves/pesados e chefes ao final de cada bioma (multi-estágio) com mudanças no parallax.

Visual: HD pixel art ou vector estilizado, partículas abundantes.
Som: synthwave energético + SFX satisfatórios.

MVP: 3 biomas + 1 chefe por bioma + ranking + game over + restart.
"""

---

# C) Detalhes Técnicos (para geração por IA)

## C1) Engine usada (neste projeto)
- **Engine/Runtime:** Ordax (runtime 2D no navegador, render em canvas)
- **View/Preview:** painel de preview do Studio (canvas)
- **Linguagem:** TypeScript

> Observação: você citou Godot/Unity/GameMaker como sugestão. Aqui, a implementação é via **engine web** do próprio projeto.

## C2) IA usada
- **IA (modelo):** via Lovable AI Gateway (modelo padrão: `google/gemini-3-flash-preview`, salvo configuração diferente)
- **Onde roda:** em função server-side (Edge Function), nunca no client

## C3) Fluxo de geração (alto nível)
1. **IntentSpec**: o brief do usuário (este documento / prompt de entrada).
2. **Planner**: a IA produz `GAME_PLAN` (técnico) + **Human Game Plan** (apresentação/checklist).
3. **Review**: usuário revisa o Human Game Plan no Drawer e aceita.
4. **RuntimeSpec**: a IA gera o `runtimeSpec` obedecendo ao plano aceito.
5. **Validação**: `validateRuntimeAgainstPlan(humanPlan, runtimeSpec)` bloqueia jogos incompletos.
6. **Evolução**: em `ADD_FEATURE` / `FIX_BUG`, IA cria `semanticPatch`, aplica e retorna relatório estruturado.

## C4) Prompt interno (conceitual)

O sistema mantém um **prompt interno** (não exposto ao usuário) com:
- Regras do contrato (ex.: “se plano menciona inimigos/tiro/HUD/colisão, runtimeSpec deve conter isso”)
- Checklist do Human Game Plan como fonte de verdade
- Instruções para sempre retornar:
  - `semanticPatch`
  - `report` (whatWasRequested/Applied/CouldNot/Limitations)
  - ou `COMPILER_ERROR` quando não cumprir

> Se você quiser, eu posso escrever um **prompt interno completo e versionado** (v1) neste arquivo como anexo, pronto para uso pelo pipeline.

## C5) A IA cria arquivos ou edita existentes?
- Na geração/evolução, a IA **edita** o estado do jogo via `runtimeSpec` (estrutura de dados) e, quando necessário, atualiza arquivos de configuração (ex.: JSON no VFS).
- O Studio pode manter um **VFS** (Virtual File System) para simular/criar estrutura de arquivos (ex.: `/config/ordax.json`).
