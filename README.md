# ORDAX Studio

> **Nome histÃ³rico do repositÃ³rio:** `mcp-blender`. O repositÃ³rio continua com esse nome por compatibilidade, mas o produto, o runtime e o MCP principal sÃ£o **ORDAX Studio**. Blender Ã© uma capability do Studio, nÃ£o um produto separado.

O ORDAX Studio Ã© um ambiente agentic persistente para trabalhar diretamente em repositÃ³rios e ferramentas locais. Ele unifica projeto ativo, memÃ³ria, arquivos, Git, preview, Blender, Unity, Unreal e adapters futuros sobre um Ãºnico `ActionRegistry` tipado.

A arquitetura possui duas superfÃ­cies do mesmo produto: `ordax-studio-mcp`/`mcp-blender` para clientes MCP locais e `ordax-product-mcp` para acesso remoto autenticado ao dispositivo. Ambas reutilizam os mesmos contratos de projeto; nÃ£o existe um â€œStudio soltoâ€ ao lado do antigo MCP.

## Conectar ou recuperar um PC Windows

Execute `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows\ordax-device-agent-setup.ps1`.
O setup atualiza a instalaÃ§Ã£o gerenciada, autentica o usuÃ¡rio quando necessÃ¡rio,
recupera a credencial Cloudflare da prÃ³pria mÃ¡quina e instala o supervisor externo.
Cloudflare v3 Ã© o provider remoto de produÃ§Ã£o e usa login GitHub/binding seguro,
sem copiar credenciais manualmente.
GitHub Runner nÃ£o Ã© requisito. Veja [fluxo, requisitos e diagnÃ³stico](docs/DEVICE_AGENT_SETUP.md).

## ORDAX Studio â€” direÃ§Ã£o atual

O Device Agent Ã© a camada de execuÃ§Ã£o do **ORDAX Studio**. O `ORDAX Local AI` existente permanece preservado e seu banco SQLite pode ser reutilizado automaticamente pelo `ordax_core`.

A integraÃ§Ã£o com `prototipo-ordax-os` Ã© uma fase posterior e nÃ£o faz parte do gate atual. Primeiro o Studio deve ficar funcional e testado no Windows. Veja [docs/ORDAX_STUDIO_FOUNDATION.md](docs/ORDAX_STUDIO_FOUNDATION.md).

O Studio possui duas shells durante a migraÃ§Ã£o: `ordax-studio-desktop` (Tk, fallback estÃ¡vel) e `ordax-studio-web` (WebView2). A shell WebView2 usa um fluxo **repositÃ³rio primeiro**: a home mostra projetos Git canÃ´nicos; ao abrir um repositÃ³rio, o workspace combina arquivos/editor com preview lateral interativo para projetos web e evidÃªncia visual para Blender/Unity, preservando os mesmos contratos MCP e de memÃ³ria.

## OrdaX multi-projeto (0.3.0)

O Device Agent aceita projetos locais cadastrados, companion Unity genÃ©rico, auditoria
espacial de cenas, inspeÃ§Ã£o/preview Blender e sequÃªncias de capturas com snapshots
e imagens entregues ao modelo por MCP. Cloudflare v3 Ã© o Control Plane remoto de produÃ§Ã£o do Device Agent, com WebSocket persistente, D1 e R2.

Versionamento Ã© por componente, nÃ£o global: bridge/distribuiÃ§Ã£o `0.3.0`, Dev
Agent `1.30.0`, protocolo Blender Live `9`, bundle do companion `1` e
Reference Contract `1`. O inventÃ¡rio completo e as regras de compatibilidade
estÃ£o em [docs/VERSIONING.md](docs/VERSIONING.md) e tambÃ©m aparecem em
`agent.status.versions`.
`agent.status.capability_contracts` expÃµe tambÃ©m o estado de promoÃ§Ã£o das operaÃ§Ãµes tipadas, aÃ§Ãµes concretas disponÃ­veis e runtime guards relevantes; isso permite distinguir capacidade compilada de simples versÃ£o instalada.
Veja [configuraÃ§Ã£o e limites](docs/MULTI_PROJECT_AGENT.md) e
[exemplo de projetos](config/projects.example.json).
O diagnÃ³stico do catÃ¡logo Blender e as prioridades de modelagem baseadas em
pesquisa estÃ£o em [docs/BLENDER_MODELING_ROADMAP.md](docs/BLENDER_MODELING_ROADMAP.md).

Agente local tipado do OrdaX para projetos e ferramentas. **Blender**, **Unity** e **Git** sÃ£o capabilities/adapters do mesmo agente; novos adapters poderÃ£o ser adicionados sem criar outro sistema. O agente tambÃ©m mantÃ©m o caminho MCP local e validaÃ§Ãµes pelo GitHub em self-hosted runner.

ImplementaÃ§Ãµes histÃ³ricas removidas da linha ativa sÃ£o preservadas sob
`archive/*` quando ainda tÃªm valor de diagnÃ³stico/projeto. O Ã­ndice e a polÃ­tica
de reutilizaÃ§Ã£o seletiva estÃ£o em [docs/ARCHIVES.md](docs/ARCHIVES.md).

Veja [o plano de evoluÃ§Ã£o do OrdaX Device Agent](docs/ORDAX_DEVICE_AGENT_EVOLUTION.md) para GitHub, Product MCP, app Projetos, controle Web e atualizaÃ§Ã£o contÃ­nua. A polÃ­tica de [atualizaÃ§Ã£o por componentes](docs/COMPONENT-UPDATES.md) separa core, MCP e adapters para evitar reinstalaÃ§Ã£o/reboot do sistema por mudanÃ§as comuns.

Novos aliases compatÃ­veis:

```powershell
ordax-device-agent
ordax-device-mcp
```

Os aliases antigos continuam vÃ¡lidos enquanto bootstrap, recovery e estaÃ§Ãµes sÃ£o migrados com prova de compatibilidade.

## Arquitetura

```text
ChatGPT / cliente MCP
        |
        +--> ORDAX Studio MCP local
        |       aliases: ordax-studio-mcp, ordax-mcp, mcp-blender
        |
        +--> ORDAX Studio Remote MCP
                autenticado por dispositivo / Space / grant
                        |
                        v
                Cloudflare Control Plane
                        |
                        v
                 Device Agent local
                        |
                        +-----------------------------+
                        | ActionRegistry tipado       |
                        +-----------------------------+
                        | Projetos / arquivos / Git   |
                        | Preview / memÃ³ria / sessÃµes |
                        | Blender / Unity / Unreal    |
                        | Assets / observaÃ§Ãµes        |
                        +-----------------------------+

mcp-blender-unity --> bridge histÃ³rica de baixo nÃ­vel, mantida para compatibilidade e diagnÃ³stico
```

A UI do ORDAX Studio, o MCP local, o Device Agent e o MCP remoto nÃ£o sÃ£o sistemas paralelos: todos convergem para os mesmos projetos e contratos tipados. Veja [o contrato de arquitetura do MCP](docs/ORDAX_STUDIO_MCP_ARCHITECTURE.md).

Para projetos Blender, a shell WebView2 carrega `blender.live_modeling_schema` no
bootstrap e mostra essas operaÃ§Ãµes na visÃ£o **MCP / Capacidades**. Assim, ARRAY,
surface scatter e o workflow Boolean `preview â†’ commit â†’ cancel` ficam visÃ­veis
no Studio com o mesmo status e as mesmas aÃ§Ãµes usados pelos clientes MCP, sem
manter uma lista paralela na interface.

A `main` Ã© a Ãºnica linha ativa de integraÃ§Ã£o. ImplementaÃ§Ãµes histÃ³ricas ficam
sob `archive/*` e nÃ£o participam de updates, recovery ou deploy normal.
O HORDAX permanece no repositÃ³rio `washingtonmsdj/HORDAX-game`.

## Estrutura

```text
ordax_core/
  memory.py

mcp_blender_unity/
  config.py
  process.py
  server.py

ordax_dev_agent/
  actions.py
  blender_actions.py
  unity_actions.py
  agent_actions.py
  artifact_actions.py
  git_actions.py
  references.py
  observations.py
  versioning.py
  blender_live_bridge.py
  assets/
    blender_live_companion.py
    blender_companion_bundle.json
    blender_uv_math.py
    blender_spatial_math.py
    blender_quality_rules.py
    blender_modeling_contracts.py

control-plane/cloudflare/
  Worker + Durable Object + D1 + R2 do protocolo v3

scripts/
  blender_benchmark.py
  verify_visual_agent.py
  verify_packaged_companion_bundle.py
  windows/

.github/workflows/
  bridge-ci.yml
  ordax-agent-recovery.yml
  merged-branch-hygiene.yml
  hordax-autopilot.yml
  toolchain-smoke.yml
  unity-hordax-validate.yml

docs/
  VERSIONING.md
  ARCHIVES.md
  SELF_HOSTED_RUNNER.md
  BLENDERBENCH.md
  BLENDER_MODELING_CONTRACTS.md
  REFERENCE_CONTRACT.md
```

## Instala??o do ORDAX Studio no Windows

Para uso normal do produto, instale uma vez o app e o runtime persistente:

```powershell
.\scripts\windows\ordax-studio-install.ps1
```

Isso cria **ORDAX Studio** no Menu Iniciar sobre o runtime gerenciado e mant?m o Device Agent como servi?o de usu?rio via Scheduled Task. `mcp-start.ps1` permanece ferramenta de desenvolvimento/smoke; n?o ? necess?rio por sess?o.

O Product Remote v2 usa grants e auditoria para expor somente opera??es tipadas de projeto e Blender. N?o existe shell remoto nem `action_execute` nessa superf?cie. Veja `docs/PRODUCT_MCP_CONNECT.md`.

## Plugin ORDAX Studio para ChatGPT

O pacote oficial do plugin está versionado em `plugins/ordax-studio/` e conecta o ChatGPT ao endpoint MCP HTTPS de produção (`/mcp`) com autenticação Product/OAuth. O uso remoto normal não exige `mcp-start.ps1`, túnel local ou terminal aberto. O Device Agent instalado no Windows permanece ativo por Scheduled Task e atende o Control Plane por conexão de saída.

Veja `docs/ORDAX_STUDIO_PRODUCT.md` e `docs/PRODUCT_MCP_CONNECT.md`.
## MCP local

Requer Python 3.11+.

```powershell
.\scripts\windows\mcp-start.ps1
```

Na primeira execuÃ§Ã£o o script cria `.venv` e instala o pacote em modo editÃ¡vel.

InstalaÃ§Ã£o manual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
python -m ordax_studio.mcp_server
```

Depois da instalaÃ§Ã£o, `ordax-studio-mcp`, `ordax-mcp` e o alias histÃ³rico `mcp-blender` iniciam esse mesmo servidor. `mcp-blender-unity` permanece disponÃ­vel apenas para a bridge de baixo nÃ­vel usada por testes/diagnÃ³stico especÃ­ficos de Blender/Unity.

VariÃ¡veis opcionais:

- `BLENDER_EXE`
- `UNITY_EXE`
- `UNITY_EDITOR_ROOTS` (optional, `;`-separated extra Unity Hub roots on Windows)
- `DEFAULT_UNITY_PROJECT`

Unity discovery enumerates all Hub directories matching the project's required
version, including official suffix variants such as `-x86_64`, and validates
the Editor, API reference assemblies, and UPM before selecting one. Healthy
installations are preferred; `UNITY_EXE` remains an explicit override and is
reported as invalid instead of silently falling back when its installation is incomplete.

For broken Editor startup, the typed recovery path can install an exact patch and
launch that exact Hub executable instead of resolving the project's older Editor.
`unity.recover_resume` is constrained to the project's current release stream
(for example `6000.6.x -> 6000.6.x`) and runs fail-closed through recovery,
companion upgrade, compile, scene/physics/spatial inspection, Play Mode and capture.

If Unity Hub downloads an Editor but repeatedly times out while validating the
installation, `unity.direct_install_editor` provides a separate bounded fallback.
It resolves the exact version + changeset through Unity's official Releases API,
requires the API's Windows x86_64 download URL and published integrity digest
(including legacy MD5 when that is what Unity supplies) to match, downloads
resumably from `download.unity3d.com`, verifies the cached/downloaded installer
hash locally, installs silently into the user-local Unity Editor root,
and verifies that the expected `Unity.exe` exists. Callers cannot supply an
arbitrary URL, hash, or install directory, and the verification path does not
depend on PowerShell certificate services.

## Tools MCP

A superfÃ­cie recomendada Ã© o **ORDAX Studio MCP**, nÃ£o a bridge histÃ³rica. Entre as ferramentas de primeira classe estÃ£o:

- `studio_status`, `repository_catalog`, `agent_capabilities` e `agent_briefing`;
- `project_inventory`, `project_search`, `project_read` e `project_read_batch`;
- `project_write` e `project_patch`, com precondiÃ§Ã£o SHA-256 para evitar sobrescrita stale;
- `git_status` e `git_diff`;
- `project_preview_status`, `project_preview_start`, `project_preview_stop` e `project_preview_image`;
- `install_blender_adoption`, `blender_instances` e `adopt_blender` para reutilizar uma janela Blender jÃ¡ aberta sem criar uma segunda instÃ¢ncia;
- `get_blender_status`, `get_scene_info`, `get_object_info`, `get_viewport_screenshot`, `add_primitive`, `modify_object`, `scatter_on_surface`, `preview_boolean_cut`, `commit_boolean_cut`, `cancel_boolean_cut`, `cleanup_mesh`, `preview_degenerate_repair`, `commit_degenerate_repair`, `cancel_degenerate_repair`, `preview_merge_by_distance`, `commit_merge_by_distance`, `cancel_merge_by_distance`, `preview_boundary_hole_fill`, `commit_boundary_hole_fill`, `cancel_boundary_hole_fill`, `delete_object`, `set_material`, `batch_edit` e `save_blender`;
- `session_context`, `session_resume`, `session_finish`, `memory_remember` e `session_checkpoint`;
- `action_execute` para capabilities tipadas registradas, incluindo Blender, Unity, Unreal e pipelines de assets.

A bridge `mcp-blender-unity` conserva ferramentas de baixo nÃ­vel como `blender_version` e rotinas CLI de Unity para compatibilidade, mas novos clientes devem descobrir e usar o MCP do Studio.

`unity_compile_project` abre/importa o projeto em batch mode e inspeciona o log por erros de compilaÃ§Ã£o.

`unity_validate_project` tambÃ©m executa, por padrÃ£o:

`HORDAX.EditorTools.CiValidation.Run`

`unity_capture_project` abre o HORDAX em Play Mode por automaÃ§Ã£o, espera alguns
frames para a cena se estabilizar e renderiza uma captura PNG da cÃ¢mera do jogo.
Isso permite validar visualmente cÃ¢mera, HUD, hordas e composiÃ§Ã£o sem depender de
uma captura manual feita no Editor.

Para validar o MCP completo e, opcionalmente, um projeto jÃ¡ registrado no ORDAX:

```powershell
.\scripts\windows\mcp-test.ps1
.\scripts\windows\mcp-test.ps1 -Project "ordax-games"
```

O alias de parÃ¢metro `-ProjectPath` foi preservado por compatibilidade do script, mas o valor agora deve ser o **slug registrado do projeto**, nÃ£o um caminho arbitrÃ¡rio do computador.

## CLI direto

Unity:

```powershell
.\scripts\windows\unity-run.ps1 `
  -ProjectPath "C:\dev\HORDAX-game" `
  -ExecuteMethod "HORDAX.EditorTools.CiValidation.Run"
```

Somente compilaÃ§Ã£o/import:

```powershell
.\scripts\windows\unity-run.ps1 -ProjectPath "C:\dev\HORDAX-game"
```

Blender:

```powershell
.\scripts\windows\blender-run.ps1 -PythonScript "C:\dev\scripts\generate_asset.py"
```

## HORDAX Unity Autopilot

A branch de desenvolvimento do HORDAX pode ser observada automaticamente pelo
workflow `HORDAX Unity Autopilot`. Em um runner Windows self-hosted ele:

1. detecta quando o commit alvo mudou;
2. escolhe uma instalaÃ§Ã£o Unity saudÃ¡vel;
3. compila o projeto;
4. executa `HORDAX.EditorTools.CiValidation.Run`;
5. abre o protÃ³tipo em Play Mode por automaÃ§Ã£o;
6. gera `prototype.png` em 1280x720;
7. publica screenshot, logs e `report.json` como artifact do workflow.

O alvo Ã© controlado por `config/hordax-autopilot.json`, portanto pode ser
alterado remotamente sem editar scripts no computador do runner. O Ãºltimo SHA
validado fica apenas na mÃ¡quina do runner, em `LOCALAPPDATA\HORDAX-Autopilot`,
para evitar executar Unity novamente quando nÃ£o houve mudanÃ§a de cÃ³digo.

## GitHub workflows e self-hosted runner

Veja `docs/SELF_HOSTED_RUNNER.md`.

- **Bridge CI** â€” automÃ¡tico em PRs e pushes para `main`; roda unit tests em
  Ubuntu/Windows, valida PowerShell, package metadata e o wheel real do companion.
- **Merged Branch Hygiene** â€” automÃ¡tico apÃ³s avanÃ§o da `main`, PR mesclado e
  tambÃ©m por agenda; remove apenas branches transitÃ³rias com PR mesclado, sem PR
  aberto e totalmente contidas na `main`.
- **OrdaX Agent Recovery** â€” automÃ¡tico em pushes relevantes da `main` e manual;
  usa runner Windows self-hosted para compile/smokes/recovery somente quando o
  commit ainda Ã© o head atual.
- **HORDAX Unity Autopilot** â€” agendado e manual; observa o commit configurado do
  HORDAX e sÃ³ executa Unity quando houver SHA novo.
- **Toolchain smoke** â€” manual; verifica Blender/Unity instalados no runner.
- **Validate HORDAX in Unity** â€” manual; valida um ref escolhido do HORDAX e
  publica o log como artifact.

O Scheduled Task do Dev Agent usa um bootstrap estÃ¡vel copiado para
`%LOCALAPPDATA%\OrdaX\DevAgent\bootstrap`, fora do checkout gerenciado. Esse
bootstrap faz preflight, fetch com refspec explÃ­cito, fast-forward, refresh
semÃ¢ntico de dependÃªncias, compile gate e rollback antes de carregar o agente.
Assim uma versÃ£o antiga do prÃ³prio agente nÃ£o precisa estar saudÃ¡vel para
atualizar o checkout numa prÃ³xima reinicializaÃ§Ã£o controlada.

O runner self-hosted Ã© necessÃ¡rio apenas para operaÃ§Ãµes que realmente dependem
do Blender/Unity instalado na estaÃ§Ã£o. CI hospedado continua validando cÃ³digo,
contratos, packaging e scripts mesmo quando a estaÃ§Ã£o local estÃ¡ offline.

## Action domain architecture

The central `ActionRegistry` remains the only allow-list surface, but domain
implementations are composed as mixins rather than accumulating in one module:

- `actions.py` â€” composition root, explicit allow-list, locking and project resolution;
- `blender_actions.py` â€” Blender/Blender Live typed actions;
- `blender_adoption.py` â€” discovery, PID matching e adoÃ§Ã£o segura de janelas Blender jÃ¡ abertas;
- `unity_actions.py` â€” Unity CLI/editor/play/capture typed actions;
- `agent_actions.py` â€” agent status, self-test and managed self-update;
- `artifact_actions.py` â€” bounded project artifact preview;
- `git_actions.py` â€” safe Git status/diff/fast-forward synchronization;
- `references.py` â€” Reference Contract and reference-guided generation;
- `observations.py` â€” project-scoped visual evidence;
- `process_runner.py` â€” shared bounded subprocess execution.
- `assets/ordax_studio_blender_addon.py` â€” add-on mÃ­nimo persistente para discovery/adoption; nÃ£o expÃµe modelagem arbitrÃ¡ria.
- `assets/blender_companion_bundle.json` â€” explicit fingerprinted runtime bundle for the Blender companion and its helper modules; changes to any listed helper invalidate the loaded companion.
- `assets/blender_uv_math.py` â€” pure deterministic UV/triangle math extracted from the Blender runtime for ordinary unit testing, including overlap area and normalized 3Dâ†’UV shape distortion.
- `assets/blender_spatial_math.py` â€” pure deterministic AABB overlap/containment math used by contact auditing, independently unit-tested outside Blender.
- `assets/blender_quality_rules.py` â€” pure axis/tolerance validation shared by deterministic quality gates and unit-tested without Blender.
- `assets/blender_modeling_contracts.py` â€” shared typed modeling schemas, closed-world plan normalization and transform validation; no `bpy` dependency, packaged with the companion bundle.

Moving a method into a domain module does not add an action. An operation becomes
remotely callable only when `ActionRegistry._actions` explicitly registers it.

## PolÃ­tica de uma Ãºnica janela Blender

O ORDAX Studio instala o add-on mÃ­nimo `ordax_studio_bridge` nas preferÃªncias do Blender. Ele publica somente presenÃ§a local e recebe pedidos tipados de adoÃ§Ã£o; toda inspeÃ§Ã£o e mutaÃ§Ã£o continuam no companion Blender Live validado por fingerprint.

Ao selecionar um projeto Blender, o Studio tenta reutilizar a janela existente. `start_blender` segue a mesma regra: **adota primeiro e sÃ³ cria um novo processo quando nÃ£o existe nenhuma janela correspondente**. Se mais de uma janela fÃ­sica apontar para o mesmo projeto, o ORDAX nÃ£o escolhe aleatoriamente: `blender_instances` retorna os PIDs e `adopt_blender` exige uma seleÃ§Ã£o explÃ­cita. A presenÃ§a do companion inclui PID, root do projeto, protocolo e fingerprint para impedir reaproveitamento de uma sessÃ£o stale ou errada.

O add-on legado `blendmcp_addon.py` de terceiros nÃ£o faz parte desse fluxo canÃ´nico. Ele pode permanecer instalado para diagnÃ³stico/compatibilidade, mas o cliente `blendmcp` do Codex aponta para o ORDAX Studio MCP.

## Blender Live 1.7.0

The visible Blender companion now exposes a richer typed perception loop:

- `blender_live_view` â€” MCP-native one-call visual loop: captures the currently visible Blender 3D viewport and returns the actual PNG/JPEG pixels as `ImageContent`, so capable MCP clients can inspect the scene without a second artifact-fetch call.
- `blender_live_multiview` â€” MCP-native deterministic visual review: captures up to six bounded orthographic views and returns every rendered view as `ImageContent` in one call, with bounds, object scope, hashes and manifest metadata.

- \`blender.live_scene_snapshot\` â€” world-space bounds, dimensions, relations,
  materials, modifiers, constraints, mesh counts and semantic OrdaX properties.
- \`blender.live_object_inspect\` â€” full inspection for one stable object name.
- \`blender.live_object_fingerprints\` â€” deterministic transform/base-mesh or evaluated-mesh hashes for approved-component revision guards.
- \`blender.live_multiview_capture\` â€” deterministic orthographic front/back/left/right/top/3â„4 evidence with automatic framing, hashes and a manifest; explicit object lists are isolated during capture.
  Supports `mode=material` and deterministic `mode=silhouette`. Material mode uses Eevee with temporary deterministic studio lights so Principled BSDF transparency/transmission and surface materials are visible; silhouette remains Workbench-only and does not silently fall back to a material render.
- `blender.multiview_compare` â€” compare two OrdaX multiview manifests with normalized MAE/RMS, changed-pixel ratio, bounds deltas, optional diff images and explicit thresholds.
  Silhouette manifests additionally expose IoU and may gate with `min_silhouette_iou`.
- \`blender.live_contact_audit\` â€” evaluated mesh BVH intersection checks for
  protected object pairs.
- \`blender.live_quality_gate\` â€” deterministic dimensions, symmetry, proportion,
  containment, mesh-quality and UV-quality checks. UV quality measures collapsed
  faces/triangles, out-of-tile loops, scale-invariant shape distortion and
  optional exact triangle-overlap evidence under a bounded analysis budget. Mesh quality also emits bounded repair hints; only safe, revision-guarded fixes are marked automatic.
- `blender.live_modeling_schema` â€” read-only typed modeling contracts. The
  validated mutations are `blender.live_object_transform`,
  `blender.live_create_primitive`, `blender.live_add_modifier`, `blender.live_surface_scatter`, `blender.live_boolean_cut_preview`, `blender.live_mesh_cleanup`, `blender.live_degenerate_repair_preview`, `blender.live_merge_by_distance_preview` and `blender.live_boundary_hole_fill_preview`. They share
  closed-world planning, runtime guards and Blender-side validation. Surface scatter was promoted after a successful real Blender 5.2.2 BlenderBench on
  September 28, 2026. The same BlenderBench run promoted non-destructive Boolean cutter preview/commit/cancel across box, circle, slot, convex polygon and vent profiles. Later Blender 5.2.2 runs promoted revision-guarded `mesh_cleanup` for isolated loose vertices and the explicit `degenerate_repair_preview â†’ commit/cancel` workflow for zero-length edges and zero-area faces, driven by repair hints from `mesh_quality`.
- `blender.live_modeling_plan` â€” read-only closed-world planner that validates
  one modeling intent, rejects unknown/inapplicable fields and returns normalized
  defaults/arguments plus the concrete action when execution is available. Use
  `schema â†’ plan â†’ execute`.
  Modifier plans publish runtime guard limits (8 modifiers, 200k evaluated
  faces, 500k projected SUBSURF faces); the visible Blender companion verifies
  those limits from live scene metrics, never user-claimed counts.
  Create/modifier plans also carry runtime preconditions and rollback guarantees
  (Object Mode/no render, uniqueness/local-target requirements and
  cleanup-on-failure). Surface scatter adds a 5,000-instance hard cap, 2M
  projected-face budget, deterministic seed/scale controls and modifier/node-group
  rollback while preserving non-realized instances. Degenerate repair previews cap
  target meshes at 200k faces, the dissolve threshold at 0.001 and diagnosed
  degenerate elements at 10,000; the candidate stays reversible until explicit
  commit, while cancel verifies and restores the exact original geometry SHA-256.
- \`blender.asset_search\` â€” typed external asset discovery (Poly Haven first).
- \`blender.asset_manifest\` â€” provider file manifest/provenance lookup.

The companion advertises a protocol version and capabilities, polls commands at
low latency, and refuses silent use of an outdated companion. Clean outdated
sessions may restart automatically; unsaved Blender work is preserved.

- `blender.live_object_metadata` â€” stable semantic IDs and provenance.
- `blender.live_checkpoint_create/list/restore` â€” managed rollback points.
- `blender.live_trajectory` â€” durable before/after operation journal.
- `blender.live_generation_pass` â€” checkpoint â†’ fingerprint protected approved objects â†’ generate â†’ verify locks â†’ inspect â†’ contact audit â†’ deterministic quality gate â†’ optional deterministic multiview â†’ optional baseline comparison â†’ capture â†’ save, with rollback on failure.
- `blender.live_export` â€” export through the visible companion when the UI session must be used.
- `blender.export_headless` â€” export a saved `.blend` in an isolated Blender background process with a hard process timeout; intended for final GLB/FBX delivery so exporter stalls cannot block the visible companion.

On Windows, the Dev Agent also launches an independent local watchdog process. The watchdog probes the local status endpoint, tracks the active job independently of the Python worker, and terminates only the Dev Agent process after repeated health failures or a single unchanged busy job exceeding the bounded 15-minute safety window. It deliberately keeps the watchdog process alive long enough to request a restart of the dedicated Scheduled Task; it does not kill the Agent process tree. The existing launcher/Scheduled Task then restarts the agent and performs the normal safe fast-forward update.

The Windows Scheduled Task also carries two non-overlapping triggers: an interactive logon trigger and a one-minute maintenance trigger. Because the task uses `MultipleInstances=IgnoreNew`, the maintenance trigger is a no-op while the Agent is already running; if both the Agent and its child watchdog have disappeared, Task Scheduler can re-enter the normal Agent entrypoint without depending on GitHub Actions.

The typed `agent.resilience_repair` action reapplies the external bootstrap/task contract and verifies both recovery triggers before returning success. Its diagnostics intentionally avoid Win32 CIM/WMI process enumeration, which has been unreliable on the Salvador workstation.

See \`docs/BLENDER_MCP_REFERENCE_REVIEW.md\` for the design review that informed
this layer and the capabilities intentionally not copied.

`python scripts/verify_visual_agent.py` now runs both the existing isolated render smoke and the real companion deterministic silhouette-multiview path. On the Windows self-hosted recovery runner this candidate smoke runs before the managed agent is touched.

`python scripts/blender_benchmark.py` adds an end-to-end regression: exact baseline self-comparison must pass, while a controlled geometry mutation must fail silhouette IoU and expose the expected bounds delta. See `docs/BLENDERBENCH.md`. The benchmark also contains valid/invalid UV fixtures and a real companion-dispatch modeling fixture covering transform, primitive creation, BEVEL/ARRAY modifiers, Geometry Nodes surface scatter, the typed Boolean cutter preview/commit/cancel workflow, revision-guarded mesh cleanup, reversible degenerate-geometry repair, explicit-selection Merge by Distance and localized boundary-hole fill. It verifies cutter families/overflow, exact rollback fingerprints, isolated-vertex repair hints, zero-length/zero-area repair, selected-vertex identity preservation, closed-loop-only hole filling, stale guards, runtime budgets, durable trajectory evidence and byte-for-byte source `.blend` integrity.

`blender.benchmark` exposes that same benchmark through the typed Dev Agent. It is a fixed diagnostic action: only `project` and bounded `timeout_seconds` are accepted; callers cannot supply a script, shell command or arbitrary output path. The structured report is written under the agent state directory and returned as an artifact.

### Reference Contract

- `project.references` validates a versioned project-local visual brief without copying images.
- `project.reference_images` materializes selected PNG/JPEG references into the managed artifact root with manifest/image hashes.
- `blender.reference_review` pairs those references with deterministic Blender multiview captures for explicit object names.
- `blender.reference_generation_pass` preflights reference integrity, runs the recoverable generation pass, checks declared physical dimensions and creates a fingerprint-locked `reference-pass.json`; it **does not save the final `.blend` while visual review is pending**.
- `blender.reference_decision` closes that pass explicitly: `accept` rechecks geometry/transform fingerprints and recaptures deterministic multiview evidence before saving. Reviewed files keep their byte-level SHA-256 integrity check, while candidate equality is decided from **decoded RGBA pixel digests**, so harmless PNG metadata/compression changes do not cause false rejection. Real geometry/material/lighting/UV/rendered-pixel changes still force a new review.
- Blender Live protocol v9 reports declared scene unit metadata so physical dimensions are checked only when the scene actually defines a usable scale.
- Arbitrary source/reference images do **not** receive a fabricated similarity score; camera/lens/crop/pose correspondence remains explicit evidence that must be reviewed.

See `docs/REFERENCE_CONTRACT.md` and `config/references.example.json`.



## SeguranÃ§a

NÃ£o versione tokens, segredos ou dados de licenÃ§a. Use variÃ¡veis de ambiente locais e GitHub Secrets quando necessÃ¡rio.


### Product MCP (read-only)

The authenticated Product MCP host is available as:

`ordax-product-mcp`

It uses `ORDAX_PRODUCT_ACCESS_TOKEN` plus the Cloudflare v3 Product API and
exposes only the read-only Product surface. It does not provide a generic shell
or mutation endpoint.
