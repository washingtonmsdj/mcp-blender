# ORDAX Studio

> **Nome histórico do repositório:** `mcp-blender`. O repositório continua com esse nome por compatibilidade, mas o produto, o runtime e o MCP principal são **ORDAX Studio**. Blender é uma capability do Studio, não um produto separado.

O ORDAX Studio é um ambiente agentic persistente para trabalhar diretamente em repositórios e ferramentas locais. Ele unifica projeto ativo, memória, arquivos, Git, preview, Blender, Unity, Unreal e adapters futuros sobre um único `ActionRegistry` tipado.

A arquitetura possui duas superfícies do mesmo produto: `ordax-studio-mcp`/`mcp-blender` para clientes MCP locais e `ordax-product-mcp` para acesso remoto autenticado ao dispositivo. Ambas reutilizam os mesmos contratos de projeto; não existe um “Studio solto” ao lado do antigo MCP.

## Conectar ou recuperar um PC Windows

Execute `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows\ordax-device-agent-setup.ps1`.
O setup atualiza a instalação gerenciada, autentica o usuário quando necessário,
recupera a credencial Cloudflare da própria máquina e instala o supervisor externo.
Cloudflare v3 é o provider remoto de produção e usa login GitHub/binding seguro,
sem copiar credenciais manualmente.
GitHub Runner não é requisito. Veja [fluxo, requisitos e diagnóstico](docs/DEVICE_AGENT_SETUP.md).

## ORDAX Studio — direção atual

O Device Agent é a camada de execução do **ORDAX Studio**. O `ORDAX Local AI` existente permanece preservado e seu banco SQLite pode ser reutilizado automaticamente pelo `ordax_core`.

A integração com `prototipo-ordax-os` é uma fase posterior e não faz parte do gate atual. Primeiro o Studio deve ficar funcional e testado no Windows. Veja [docs/ORDAX_STUDIO_FOUNDATION.md](docs/ORDAX_STUDIO_FOUNDATION.md).

O Studio possui duas shells durante a migração: `ordax-studio-desktop` (Tk, fallback estável) e `ordax-studio-web` (WebView2). A shell WebView2 usa um fluxo **repositório primeiro**: a home mostra projetos Git canônicos; ao abrir um repositório, o workspace combina arquivos/editor com preview lateral interativo para projetos web e evidência visual para Blender/Unity, preservando os mesmos contratos MCP e de memória.

## OrdaX multi-projeto (0.3.0)

O Device Agent aceita projetos locais cadastrados, companion Unity genérico, auditoria
espacial de cenas, inspeção/preview Blender e sequências de capturas com snapshots
e imagens entregues ao modelo por MCP. Cloudflare v3 é o Control Plane remoto de produção do Device Agent, com WebSocket persistente, D1 e R2.

Versionamento é por componente, não global: bridge/distribuição `0.3.0`, Dev
Agent `1.30.0`, protocolo Blender Live `9`, bundle do companion `1` e
Reference Contract `1`. O inventário completo e as regras de compatibilidade
estão em [docs/VERSIONING.md](docs/VERSIONING.md) e também aparecem em
`agent.status.versions`.
`agent.status.capability_contracts` expõe também o estado de promoção das operações tipadas, ações concretas disponíveis e runtime guards relevantes; isso permite distinguir capacidade compilada de simples versão instalada.
Veja [configuração e limites](docs/MULTI_PROJECT_AGENT.md) e
[exemplo de projetos](config/projects.example.json).
O diagnóstico do catálogo Blender e as prioridades de modelagem baseadas em
pesquisa estão em [docs/BLENDER_MODELING_ROADMAP.md](docs/BLENDER_MODELING_ROADMAP.md).

Agente local tipado do OrdaX para projetos e ferramentas. **Blender**, **Unity** e **Git** são capabilities/adapters do mesmo agente; novos adapters poderão ser adicionados sem criar outro sistema. O agente também mantém o caminho MCP local e validações pelo GitHub em self-hosted runner.

Implementações históricas removidas da linha ativa são preservadas sob
`archive/*` quando ainda têm valor de diagnóstico/projeto. O índice e a política
de reutilização seletiva estão em [docs/ARCHIVES.md](docs/ARCHIVES.md).

Veja [o plano de evolução do OrdaX Device Agent](docs/ORDAX_DEVICE_AGENT_EVOLUTION.md) para GitHub, Product MCP, app Projetos, controle Web e atualização contínua. A política de [atualização por componentes](docs/COMPONENT-UPDATES.md) separa core, MCP e adapters para evitar reinstalação/reboot do sistema por mudanças comuns.

Novos aliases compatíveis:

```powershell
ordax-device-agent
ordax-device-mcp
```

Os aliases antigos continuam válidos enquanto bootstrap, recovery e estações são migrados com prova de compatibilidade.

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
                        | Preview / memória / sessões |
                        | Blender / Unity / Unreal    |
                        | Assets / observações        |
                        +-----------------------------+

mcp-blender-unity --> bridge histórica de baixo nível, mantida para compatibilidade e diagnóstico
```

A UI do ORDAX Studio, o MCP local, o Device Agent e o MCP remoto não são sistemas paralelos: todos convergem para os mesmos projetos e contratos tipados. Veja [o contrato de arquitetura do MCP](docs/ORDAX_STUDIO_MCP_ARCHITECTURE.md).

Para projetos Blender, a shell WebView2 carrega `blender.live_modeling_schema` no
bootstrap e mostra essas operações na visão **MCP / Capacidades**. Assim, ARRAY,
surface scatter e o workflow Boolean `preview → commit → cancel` ficam visíveis
no Studio com o mesmo status e as mesmas ações usados pelos clientes MCP, sem
manter uma lista paralela na interface.

A `main` é a única linha ativa de integração. Implementações históricas ficam
sob `archive/*` e não participam de updates, recovery ou deploy normal.
O HORDAX permanece no repositório `washingtonmsdj/HORDAX-game`.

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

O pacote oficial do plugin est? versionado em `plugins/ordax-studio/` e conecta o ChatGPT ao endpoint MCP HTTPS de produ??o (`/mcp`) com autentica??o Product/OAuth. O uso remoto normal n?o exige `mcp-start.ps1`, t?nel local ou terminal aberto. O Device Agent instalado no Windows permanece ativo por Scheduled Task e atende o Control Plane por conex?o de sa?da.

Veja `docs/ORDAX_STUDIO_PRODUCT.md` e `docs/PRODUCT_MCP_CONNECT.md`.

## MCP local

Requer Python 3.11+.

```powershell
.\scripts\windows\mcp-start.ps1
```

Na primeira execução o script cria `.venv` e instala o pacote em modo editável.

Instalação manual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
python -m ordax_studio.mcp_server
```

Depois da instalação, `ordax-studio-mcp`, `ordax-mcp` e o alias histórico `mcp-blender` iniciam esse mesmo servidor. `mcp-blender-unity` permanece disponível apenas para a bridge de baixo nível usada por testes/diagnóstico específicos de Blender/Unity.

Variáveis opcionais:

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

A superfície recomendada é o **ORDAX Studio MCP**, não a bridge histórica. Entre as ferramentas de primeira classe estão:

- `studio_status`, `repository_catalog`, `agent_capabilities` e `agent_briefing`;
- `project_inventory`, `project_search`, `project_read` e `project_read_batch`;
- `project_write` e `project_patch`, com precondição SHA-256 para evitar sobrescrita stale;
- `git_status` e `git_diff`;
- `project_preview_status`, `project_preview_start`, `project_preview_stop` e `project_preview_image`;
- `install_blender_adoption`, `blender_instances` e `adopt_blender` para reutilizar uma janela Blender já aberta sem criar uma segunda instância;
- `get_blender_status`, `get_scene_info`, `get_object_info`, `get_viewport_screenshot`, `add_primitive`, `modify_object`, `scatter_on_surface`, `preview_boolean_cut`, `commit_boolean_cut`, `cancel_boolean_cut`, `cleanup_mesh`, `preview_degenerate_repair`, `commit_degenerate_repair`, `cancel_degenerate_repair`, `preview_merge_by_distance`, `commit_merge_by_distance`, `cancel_merge_by_distance`, `preview_boundary_hole_fill`, `commit_boundary_hole_fill`, `cancel_boundary_hole_fill`, `delete_object`, `set_material`, `batch_edit` e `save_blender`;
- `session_context`, `session_resume`, `session_finish`, `memory_remember` e `session_checkpoint`;
- `action_execute` para capabilities tipadas registradas, incluindo Blender, Unity, Unreal e pipelines de assets.

A bridge `mcp-blender-unity` conserva ferramentas de baixo nível como `blender_version` e rotinas CLI de Unity para compatibilidade, mas novos clientes devem descobrir e usar o MCP do Studio.

`unity_compile_project` abre/importa o projeto em batch mode e inspeciona o log por erros de compilação.

`unity_validate_project` também executa, por padrão:

`HORDAX.EditorTools.CiValidation.Run`

`unity_capture_project` abre o HORDAX em Play Mode por automação, espera alguns
frames para a cena se estabilizar e renderiza uma captura PNG da câmera do jogo.
Isso permite validar visualmente câmera, HUD, hordas e composição sem depender de
uma captura manual feita no Editor.

Para validar o MCP completo e, opcionalmente, um projeto já registrado no ORDAX:

```powershell
.\scripts\windows\mcp-test.ps1
.\scripts\windows\mcp-test.ps1 -Project "ordax-games"
```

O alias de parâmetro `-ProjectPath` foi preservado por compatibilidade do script, mas o valor agora deve ser o **slug registrado do projeto**, não um caminho arbitrário do computador.

## CLI direto

Unity:

```powershell
.\scripts\windows\unity-run.ps1 `
  -ProjectPath "C:\dev\HORDAX-game" `
  -ExecuteMethod "HORDAX.EditorTools.CiValidation.Run"
```

Somente compilação/import:

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
2. escolhe uma instalação Unity saudável;
3. compila o projeto;
4. executa `HORDAX.EditorTools.CiValidation.Run`;
5. abre o protótipo em Play Mode por automação;
6. gera `prototype.png` em 1280x720;
7. publica screenshot, logs e `report.json` como artifact do workflow.

O alvo é controlado por `config/hordax-autopilot.json`, portanto pode ser
alterado remotamente sem editar scripts no computador do runner. O último SHA
validado fica apenas na máquina do runner, em `LOCALAPPDATA\HORDAX-Autopilot`,
para evitar executar Unity novamente quando não houve mudança de código.

## GitHub workflows e self-hosted runner

Veja `docs/SELF_HOSTED_RUNNER.md`.

- **Bridge CI** — automático em PRs e pushes para `main`; roda unit tests em
  Ubuntu/Windows, valida PowerShell, package metadata e o wheel real do companion.
- **Merged Branch Hygiene** — automático após avanço da `main`, PR mesclado e
  também por agenda; remove apenas branches transitórias com PR mesclado, sem PR
  aberto e totalmente contidas na `main`.
- **OrdaX Agent Recovery** — automático em pushes relevantes da `main` e manual;
  usa runner Windows self-hosted para compile/smokes/recovery somente quando o
  commit ainda é o head atual.
- **HORDAX Unity Autopilot** — agendado e manual; observa o commit configurado do
  HORDAX e só executa Unity quando houver SHA novo.
- **Toolchain smoke** — manual; verifica Blender/Unity instalados no runner.
- **Validate HORDAX in Unity** — manual; valida um ref escolhido do HORDAX e
  publica o log como artifact.

O Scheduled Task do Dev Agent usa um bootstrap estável copiado para
`%LOCALAPPDATA%\OrdaX\DevAgent\bootstrap`, fora do checkout gerenciado. Esse
bootstrap faz preflight, fetch com refspec explícito, fast-forward, refresh
semântico de dependências, compile gate e rollback antes de carregar o agente.
Assim uma versão antiga do próprio agente não precisa estar saudável para
atualizar o checkout numa próxima reinicialização controlada.

O runner self-hosted é necessário apenas para operações que realmente dependem
do Blender/Unity instalado na estação. CI hospedado continua validando código,
contratos, packaging e scripts mesmo quando a estação local está offline.

## Action domain architecture

The central `ActionRegistry` remains the only allow-list surface, but domain
implementations are composed as mixins rather than accumulating in one module:

- `actions.py` — composition root, explicit allow-list, locking and project resolution;
- `blender_actions.py` — Blender/Blender Live typed actions;
- `blender_adoption.py` — discovery, PID matching e adoção segura de janelas Blender já abertas;
- `unity_actions.py` — Unity CLI/editor/play/capture typed actions;
- `agent_actions.py` — agent status, self-test and managed self-update;
- `artifact_actions.py` — bounded project artifact preview;
- `git_actions.py` — safe Git status/diff/fast-forward synchronization;
- `references.py` — Reference Contract and reference-guided generation;
- `observations.py` — project-scoped visual evidence;
- `process_runner.py` — shared bounded subprocess execution.
- `assets/ordax_studio_blender_addon.py` — add-on mínimo persistente para discovery/adoption; não expõe modelagem arbitrária.
- `assets/blender_companion_bundle.json` — explicit fingerprinted runtime bundle for the Blender companion and its helper modules; changes to any listed helper invalidate the loaded companion.
- `assets/blender_uv_math.py` — pure deterministic UV/triangle math extracted from the Blender runtime for ordinary unit testing, including overlap area and normalized 3D→UV shape distortion.
- `assets/blender_spatial_math.py` — pure deterministic AABB overlap/containment math used by contact auditing, independently unit-tested outside Blender.
- `assets/blender_quality_rules.py` — pure axis/tolerance validation shared by deterministic quality gates and unit-tested without Blender.
- `assets/blender_modeling_contracts.py` — shared typed modeling schemas, closed-world plan normalization and transform validation; no `bpy` dependency, packaged with the companion bundle.

Moving a method into a domain module does not add an action. An operation becomes
remotely callable only when `ActionRegistry._actions` explicitly registers it.

## Política de uma única janela Blender

O ORDAX Studio instala o add-on mínimo `ordax_studio_bridge` nas preferências do Blender. Ele publica somente presença local e recebe pedidos tipados de adoção; toda inspeção e mutação continuam no companion Blender Live validado por fingerprint.

Ao selecionar um projeto Blender, o Studio tenta reutilizar a janela existente. `start_blender` segue a mesma regra: **adota primeiro e só cria um novo processo quando não existe nenhuma janela correspondente**. Se mais de uma janela física apontar para o mesmo projeto, o ORDAX não escolhe aleatoriamente: `blender_instances` retorna os PIDs e `adopt_blender` exige uma seleção explícita. A presença do companion inclui PID, root do projeto, protocolo e fingerprint para impedir reaproveitamento de uma sessão stale ou errada.

O add-on legado `blendmcp_addon.py` de terceiros não faz parte desse fluxo canônico. Ele pode permanecer instalado para diagnóstico/compatibilidade, mas o cliente `blendmcp` do Codex aponta para o ORDAX Studio MCP.

## Blender Live 1.7.0

The visible Blender companion now exposes a richer typed perception loop:

- `blender_live_view` — MCP-native one-call visual loop: captures the currently visible Blender 3D viewport and returns the actual PNG/JPEG pixels as `ImageContent`, so capable MCP clients can inspect the scene without a second artifact-fetch call.
- `blender_live_multiview` — MCP-native deterministic visual review: captures up to six bounded orthographic views and returns every rendered view as `ImageContent` in one call, with bounds, object scope, hashes and manifest metadata.

- \`blender.live_scene_snapshot\` — world-space bounds, dimensions, relations,
  materials, modifiers, constraints, mesh counts and semantic OrdaX properties.
- \`blender.live_object_inspect\` — full inspection for one stable object name.
- \`blender.live_object_fingerprints\` — deterministic transform/base-mesh or evaluated-mesh hashes for approved-component revision guards.
- \`blender.live_multiview_capture\` — deterministic orthographic front/back/left/right/top/3⁄4 evidence with automatic framing, hashes and a manifest; explicit object lists are isolated during capture.
  Supports `mode=material` and deterministic `mode=silhouette`. Material mode uses Eevee with temporary deterministic studio lights so Principled BSDF transparency/transmission and surface materials are visible; silhouette remains Workbench-only and does not silently fall back to a material render.
- `blender.multiview_compare` — compare two OrdaX multiview manifests with normalized MAE/RMS, changed-pixel ratio, bounds deltas, optional diff images and explicit thresholds.
  Silhouette manifests additionally expose IoU and may gate with `min_silhouette_iou`.
- \`blender.live_contact_audit\` — evaluated mesh BVH intersection checks for
  protected object pairs.
- \`blender.live_quality_gate\` — deterministic dimensions, symmetry, proportion,
  containment, mesh-quality and UV-quality checks. UV quality measures collapsed
  faces/triangles, out-of-tile loops, scale-invariant shape distortion and
  optional exact triangle-overlap evidence under a bounded analysis budget. Mesh quality also emits bounded repair hints; only safe, revision-guarded fixes are marked automatic.
- `blender.live_modeling_schema` — read-only typed modeling contracts. The
  validated mutations are `blender.live_object_transform`,
  `blender.live_create_primitive`, `blender.live_add_modifier`, `blender.live_surface_scatter`, `blender.live_boolean_cut_preview`, `blender.live_mesh_cleanup`, `blender.live_degenerate_repair_preview`, `blender.live_merge_by_distance_preview` and `blender.live_boundary_hole_fill_preview`. They share
  closed-world planning, runtime guards and Blender-side validation. Surface scatter was promoted after a successful real Blender 5.2.2 BlenderBench on
  September 28, 2026. The same BlenderBench run promoted non-destructive Boolean cutter preview/commit/cancel across box, circle, slot, convex polygon and vent profiles. Later Blender 5.2.2 runs promoted revision-guarded `mesh_cleanup` for isolated loose vertices and the explicit `degenerate_repair_preview → commit/cancel` workflow for zero-length edges and zero-area faces, driven by repair hints from `mesh_quality`.
- `blender.live_modeling_plan` — read-only closed-world planner that validates
  one modeling intent, rejects unknown/inapplicable fields and returns normalized
  defaults/arguments plus the concrete action when execution is available. Use
  `schema → plan → execute`.
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
- \`blender.asset_search\` — typed external asset discovery (Poly Haven first).
- \`blender.asset_manifest\` — provider file manifest/provenance lookup.

The companion advertises a protocol version and capabilities, polls commands at
low latency, and refuses silent use of an outdated companion. Clean outdated
sessions may restart automatically; unsaved Blender work is preserved.

- `blender.live_object_metadata` — stable semantic IDs and provenance.
- `blender.live_checkpoint_create/list/restore` — managed rollback points.
- `blender.live_trajectory` — durable before/after operation journal.
- `blender.live_generation_pass` — checkpoint → fingerprint protected approved objects → generate → verify locks → inspect → contact audit → deterministic quality gate → optional deterministic multiview → optional baseline comparison → capture → save, with rollback on failure.
- `blender.live_export` — export through the visible companion when the UI session must be used.
- `blender.export_headless` — export a saved `.blend` in an isolated Blender background process with a hard process timeout; intended for final GLB/FBX delivery so exporter stalls cannot block the visible companion.

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



## Segurança

Não versione tokens, segredos ou dados de licença. Use variáveis de ambiente locais e GitHub Secrets quando necessário.


### Product MCP / ORDAX Chat App

The authenticated Product MCP host is available as:

`ordax-product-mcp`

It uses `ORDAX_PRODUCT_ACCESS_TOKEN` plus the Cloudflare v3 Product API. The
current product surface supports project discovery, broad project-scoped file
operations, Git, artifacts/previews, typed adapters and an explicit privileged
`terminal.exec` capability for full development workflows.

There is still no generic `action_execute` escape hatch. Authority is granted
per device, project and capability, and every remote action goes through the
same Product grant and audit path. See `ordax_chat_app/` for the product
boundary and roadmap.
