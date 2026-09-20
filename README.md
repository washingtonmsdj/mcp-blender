# MCP Blender + Unity CLI

## OrdaX multi-projeto (0.3)

O agente aceita projetos locais cadastrados, companion Unity genérico, inspeção e
preview Blender, sequências de capturas com snapshots e imagens entregues ao modelo
por MCP. A fila Supabase existente continua atendendo clientes remotos.
Veja [configuração e limites](docs/MULTI_PROJECT_AGENT.md) e
[exemplo de projetos](config/projects.example.json).

Ponte local para controlar **Blender CLI** e **Unity CLI** por MCP e para executar validações pelo GitHub em um self-hosted runner.

O antigo Ordax Engine foi removido da `main`. O snapshot anterior está preservado em:

`archive/ordax-engine-before-cleanup-2026-09-17`

## Arquitetura

```text
ChatGPT / cliente MCP
        |
        v
mcp-blender-unity
        |
        +--> Blender CLI
        |
        +--> Unity CLI
                 |
                 +--> HORDAX-game
```

O HORDAX permanece no repositório `washingtonmsdj/HORDAX-game`.

## Estrutura

```text
mcp_blender_unity/
  config.py
  process.py
  server.py

scripts/windows/
  blender-run.ps1
  mcp-start.ps1
  toolchain-status.ps1
  unity-run.ps1

.github/workflows/
  toolchain-smoke.yml
  unity-hordax-validate.yml

docs/
  SELF_HOSTED_RUNNER.md
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

## GitHub self-hosted runner

Veja `docs/SELF_HOSTED_RUNNER.md`.

O workflow **Validate HORDAX in Unity** faz checkout do HORDAX em diretório isolado, roda o Unity em batch mode e publica o log como artifact.

Os workflows são manuais por segurança.

## Action domain architecture

The central `ActionRegistry` remains the only allow-list surface, but domain
implementations are composed as mixins rather than accumulating in one module:

- `actions.py` — registry, agent, Git and Unity orchestration;
- `blender_actions.py` — Blender/Blender Live typed actions;
- `unity_actions.py` — Unity CLI/editor/play/capture typed actions;
- `references.py` — Reference Contract and reference-guided generation;
- `observations.py` — project-scoped visual evidence;
- `process_runner.py` — shared bounded subprocess execution.

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

`python scripts/blender_benchmark.py` adds an end-to-end regression: exact baseline self-comparison must pass, while a controlled geometry mutation must fail silhouette IoU and expose the expected bounds delta. See `docs/BLENDERBENCH.md`. The benchmark also contains valid/invalid UV fixtures so the Blender 5.x UV API and `uv_quality` implementation are exercised in the real runtime.

### Reference Contract

- `project.references` validates a versioned project-local visual brief without copying images.
- `project.reference_images` materializes selected PNG/JPEG references into the managed artifact root with manifest/image hashes.
- `blender.reference_review` pairs those references with deterministic Blender multiview captures for explicit object names.
- `blender.reference_generation_pass` preflights reference integrity, runs the recoverable generation pass, checks declared physical dimensions and creates a fingerprint-locked `reference-pass.json`; it **does not save the final `.blend` while visual review is pending**.
- `blender.reference_decision` closes that pass explicitly: `accept` rechecks fingerprints and saves only the exact reviewed candidate, while `reject` restores the generation checkpoint. A scene changed after capture cannot be accepted without a new review.
- Blender Live protocol v9 reports declared scene unit metadata so physical dimensions are checked only when the scene actually defines a usable scale.
- Arbitrary source/reference images do **not** receive a fabricated similarity score; camera/lens/crop/pose correspondence remains explicit evidence that must be reviewed.

See `docs/REFERENCE_CONTRACT.md` and `config/references.example.json`.



## Segurança

Não versione tokens, segredos ou dados de licença. Use variáveis de ambiente locais e GitHub Secrets quando necessário.
