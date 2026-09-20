# MCP Blender + Unity CLI

## OrdaX multi-projeto (0.3.0)

O agente aceita projetos locais cadastrados, companion Unity genérico, auditoria
espacial de cenas, inspeção/preview Blender e sequências de capturas com snapshots
e imagens entregues ao modelo por MCP. A fila Supabase existente continua atendendo clientes remotos.

Versionamento é por componente, não global: bridge/distribuição `0.3.0`, Dev
Agent `1.17.0`, protocolo Blender Live `9`, bundle do companion `1` e
Reference Contract `1`. O inventário completo e as regras de compatibilidade
estão em [docs/VERSIONING.md](docs/VERSIONING.md) e também aparecem em
`agent.status.versions`.
`agent.status.capability_contracts` expõe também o estado de promoção das operações tipadas, ações concretas disponíveis e runtime guards relevantes; isso permite distinguir capacidade compilada de simples versão instalada.
Veja [configuração e limites](docs/MULTI_PROJECT_AGENT.md) e
[exemplo de projetos](config/projects.example.json).

Ponte local para controlar **Blender CLI** e **Unity CLI** por MCP e para executar validações pelo GitHub em um self-hosted runner.

Implementações históricas removidas da linha ativa são preservadas sob
`archive/*` quando ainda têm valor de diagnóstico/projeto. O índice e a política
de reutilização seletiva estão em [docs/ARCHIVES.md](docs/ARCHIVES.md).

## Arquitetura

```text
ChatGPT / cliente MCP
        |
        +--> mcp-blender-unity 0.3.x
        |       +--> Blender CLI / headless export
        |       +--> Unity CLI
        |
        +--> ordax-project-mcp / OrdaX Dev Agent
                |
                +--> ActionRegistry tipado (allow-list)
                +--> projetos locais cadastrados
                +--> Blender Live companion (janela visível)
                +--> Unity companion / Editor
                +--> Reference Contract + evidência visual
                +--> Git / artifacts / observações
                |
                +--> Supabase control plane (fila remota opcional)

Blender Live companion <--> inbox/results/trajectory locais versionados por protocolo
Unity CLI / companion   <--> HORDAX-game e outros projetos Unity cadastrados
```

A `main` é a única linha ativa de integração. Implementações históricas ficam
sob `archive/*` e não participam de updates, recovery ou deploy normal.
O HORDAX permanece no repositório `washingtonmsdj/HORDAX-game`.

## Estrutura

```text
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

control-plane/supabase/
  migrations + Edge Function do Dev Agent

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
python -m mcp_blender_unity.server
```

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

## Tools MCP

- `toolchain_status`
- `blender_version`
- `blender_run_python`
- `unity_compile_project`
- `unity_validate_project`
- `unity_run_method`
- `unity_capture_project`

`unity_compile_project` abre/importa o projeto em batch mode e inspeciona o log por erros de compilação.

`unity_validate_project` também executa, por padrão:

`HORDAX.EditorTools.CiValidation.Run`

`unity_capture_project` abre o HORDAX em Play Mode por automação, espera alguns
frames para a cena se estabilizar e renderiza uma captura PNG da câmera do jogo.
Isso permite validar visualmente câmera, HUD, hordas e composição sem depender de
uma captura manual feita no Editor.

For a project-specific toolchain report, pass its path to the Windows smoke test:

```powershell
.\scripts\windows\mcp-test.ps1 -ProjectPath "C:\dev\HORDAX-game"
```

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
- `unity_actions.py` — Unity CLI/editor/play/capture typed actions;
- `agent_actions.py` — agent status, self-test and managed self-update;
- `artifact_actions.py` — bounded project artifact preview;
- `git_actions.py` — safe Git status/diff/fast-forward synchronization;
- `references.py` — Reference Contract and reference-guided generation;
- `observations.py` — project-scoped visual evidence;
- `process_runner.py` — shared bounded subprocess execution.
- `assets/blender_companion_bundle.json` — explicit fingerprinted runtime bundle for the Blender companion and its helper modules; changes to any listed helper invalidate the loaded companion.
- `assets/blender_uv_math.py` — pure deterministic UV/triangle math extracted from the Blender runtime for ordinary unit testing, including overlap area and normalized 3D→UV shape distortion.
- `assets/blender_spatial_math.py` — pure deterministic AABB overlap/containment math used by contact auditing, independently unit-tested outside Blender.
- `assets/blender_quality_rules.py` — pure axis/tolerance validation shared by deterministic quality gates and unit-tested without Blender.
- `assets/blender_modeling_contracts.py` — shared typed modeling schemas, closed-world plan normalization and transform validation; no `bpy` dependency, packaged with the companion bundle.

Moving a method into a domain module does not add an action. An operation becomes
remotely callable only when `ActionRegistry._actions` explicitly registers it.

## Blender Live 1.7.0

The visible Blender companion now exposes a richer typed perception loop:

- \`blender.live_scene_snapshot\` — world-space bounds, dimensions, relations,
  materials, modifiers, constraints, mesh counts and semantic OrdaX properties.
- \`blender.live_object_inspect\` — full inspection for one stable object name.
- \`blender.live_object_fingerprints\` — deterministic transform/base-mesh or evaluated-mesh hashes for approved-component revision guards.
- \`blender.live_multiview_capture\` — deterministic orthographic front/back/left/right/top/3⁄4 evidence with automatic framing, hashes and a manifest; explicit object lists are isolated during capture.
  Supports `mode=material` and deterministic `mode=silhouette`; silhouette requires Workbench and does not silently fall back to a material render.
- `blender.multiview_compare` — compare two OrdaX multiview manifests with normalized MAE/RMS, changed-pixel ratio, bounds deltas, optional diff images and explicit thresholds.
  Silhouette manifests additionally expose IoU and may gate with `min_silhouette_iou`.
- \`blender.live_contact_audit\` — evaluated mesh BVH intersection checks for
  protected object pairs.
- \`blender.live_quality_gate\` — deterministic dimensions, symmetry, proportion,
  containment, mesh-quality and UV-quality checks. UV quality measures collapsed
  faces/triangles, out-of-tile loops, scale-invariant shape distortion and
  optional exact triangle-overlap evidence under a bounded analysis budget.
- `blender.live_modeling_schema` — read-only typed modeling contracts. The
  validated mutations are `blender.live_object_transform`,
  `blender.live_create_primitive` and `blender.live_add_modifier`. They share
  closed-world planning, runtime guards and Blender-side validation. Create and
  modifier were promoted after a successful real Blender 5.2.2 BlenderBench on
  September 20, 2026.
- `blender.live_modeling_plan` — read-only closed-world planner that validates
  one modeling intent, rejects unknown/inapplicable fields and returns normalized
  defaults/arguments plus the concrete action when execution is available. Use
  `schema → plan → execute`.
  Modifier plans publish runtime guard limits (8 modifiers, 200k evaluated
  faces, 500k projected SUBSURF faces); the visible Blender companion verifies
  those limits from live scene metrics, never user-claimed counts.
  Create/modifier plans also carry runtime preconditions and rollback guarantees
  (Object Mode/no render, uniqueness/local-target requirements and
  cleanup-on-failure).
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

On Windows, the Dev Agent also launches an independent local watchdog process. The watchdog probes the local status endpoint, tracks the active job independently of the Python worker, and terminates only the Dev Agent process tree after repeated health failures or a single unchanged busy job exceeding the bounded 15-minute safety window. The existing launcher/Scheduled Task then restarts the agent and performs the normal safe fast-forward update.

See \`docs/BLENDER_MCP_REFERENCE_REVIEW.md\` for the design review that informed
this layer and the capabilities intentionally not copied.

`python scripts/verify_visual_agent.py` now runs both the existing isolated render smoke and the real companion deterministic silhouette-multiview path. On the Windows self-hosted recovery runner this candidate smoke runs before the managed agent is touched.

`python scripts/blender_benchmark.py` adds an end-to-end regression: exact baseline self-comparison must pass, while a controlled geometry mutation must fail silhouette IoU and expose the expected bounds delta. See `docs/BLENDERBENCH.md`. The benchmark also contains valid/invalid UV fixtures and a real companion-dispatch modeling fixture: `object_transform` must mutate the temporary scene in memory, a zero-scale negative control must be rejected, both commands must be journaled, and the source `.blend` must remain byte-for-byte unchanged on disk.

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
