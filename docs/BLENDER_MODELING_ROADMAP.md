# Blender modeling improvements from workflow research

## Audit snapshot

This review is based on `origin/main` at `d48d350` (September 25, 2026). The
project already has a strong agent foundation: typed mutations, a live Blender
companion, batched actions, checkpoints, multiview captures, reference review,
mesh/contact/UV audits and box cutouts. The main modeling gap is not scene
control; it is a narrow set of convenient, reusable geometry operations between
primitive creation and a user-authored generation script.

Reddit threads are useful as examples of where artists lose time, but the posts
below are anecdotal and do not measure how common each problem is.

## Findings and ranked opportunities

### 1. Repeated geometry with predictable spacing

Artists use repeated parts for rivets, vents, bolts, trim and architectural
details. One Blender 5.0 discussion called out the improved array workflow and
surface scatter as features people wanted to try. A separate help thread about
uniform rivets described the Array + Curve workflow as useful but initially
finicky. A 2026 community add-on overview also groups linear/radial arrays,
repeat, booleans and precision placement into one hard-surface workflow.

The native Array modifier is the right first increment for this MCP: it is
non-destructive, deterministic, and easier to bound than generating thousands
of independent objects. The fixed-count linear `ARRAY` variant is now promoted
after BlenderBench validation on Blender 5.2.2, with a 64-copy ceiling and a
500,000 projected-face budget. Radial placement and curve fitting remain deferred
until their origin and orientation contracts can be proven with Blender 5.x fixtures.

Sources: [Blender 5.0 discussion](https://www.reddit.com/r/blender/comments/1p0jwvc/blender_50_released/),
[uniform rivets workflow](https://www.reddit.com/r/blender/comments/nml89x/how_to_uniformly_place_rivets_around_window/),
[hard-surface workflow toolkit discussion](https://www.reddit.com/r/blender/comments/1ulu4nn/i_built_hardflow_a_free_opensource_hardsurface/),
[parametric boolean/array workflow](https://www.reddit.com/r/blender/comments/1rufkb6/i_released_the_alpha_of_my_hard_surface_modeling/),
[Blender Array modifier reference](https://docs.blender.org/manual/en/5.2/modeling/modifiers/generate/array_legacy.html).

### 2. Surface scatter and controlled variation

Surface placement is a natural follow-up for bolts, greebles and repeated props.
In a Blender help thread, artists suggested Geometry Nodes to randomize the
orientation of an array of nuts; in another, they described nodes for placing
holes at reference points. The Blender manual describes Geometry Nodes as a
surface point-distribution workflow.

This is now implemented as the typed `surface_scatter` operation rather than
arbitrary node-tree injection. It requires a declared mesh source and target,
uses a fixed seed, bounded density, deterministic scale range, optional normal
alignment and a hard `max_instances` cap enforced inside the node graph. The
runtime also measures the actual generated instance count, preserves instances
by default, rejects source/target or projected-geometry budgets before mutation,
and removes the new modifier/node group on failure. BlenderBench on Blender
5.2.2 validated a 25-instance hard cap, seed preservation, negative overflow
control, trajectory evidence and source `.blend` integrity.

Sources: [randomized fastener workflow](https://www.reddit.com/r/blenderhelp/comments/1ipz5np/i_used_simple_array_modifiers_on_the_hex_nuts_is/),
[pattern-of-holes discussion](https://www.reddit.com/r/blender/comments/1985hfi/how_would_you_create_this_pattern/),
[Distribute Points on Faces manual](https://docs.blender.org/manual/en/5.2/modeling/geometry_nodes/point/distribute_points_on_faces.html).

### 3. More expressive non-destructive cutters

This opportunity is now implemented as a typed, non-destructive Boolean workflow.
`boolean_cut_preview` accepts bounded `box`, `circle`, `slot`, convex `polygon` and
`vent` profiles in target-local coordinates. A preview creates temporary cutter
objects plus Exact Difference Boolean modifiers without applying them to the base
mesh. `blender.live_boolean_cut_commit` keeps those modifiers live and hides the
cutters; `blender.live_boolean_cut_cancel` removes the workflow and restores the
original modifier stack in one operation.

The contract caps the expanded workflow at eight cutter objects, 64 profile
segments, 16 polygon points, 200,000 target faces and 12,000 generated cutter
faces. Unknown/type-inapplicable fields and non-convex polygons are rejected
before IPC. BlenderBench on Blender 5.2.2 validated all five profile families,
a seven-cutter preview, an expansion-overflow negative control, non-destructive
commit, full cancel/rollback, trajectory evidence and unchanged source `.blend`
hashes. The legacy destructive box-cutout action remains only for compatibility;
new work should use the preview/commit/cancel workflow.

The same capability schema is surfaced inside ORDAX Studio's MCP / Capacidades
view so the desktop workspace and MCP clients discover the exact same modeling
contract and workflow actions from the central `ActionRegistry`.

Sources: [Hardflow workflow discussion](https://www.reddit.com/r/blender/comments/1ulu4nn/i_built_hardflow_a_free_opensource_hardsurface/),
[HardCuts parametric boolean workflow](https://www.reddit.com/r/blender/comments/1rufkb6/i_released_the_alpha_of_my_hard_surface_modeling/).

### 4. Retopology guidance rather than automated retopology

One user described manually extruding edges across a surface and asked for a
faster way to turn drawn guides into topology. Automated retopology and
interactive stroke tools depend on artistic judgment and viewport interaction.
The mesh-quality gate now turns its bounded topology evidence into explicit
`repair_hints`: loose/non-finite vertices, zero-length or boundary/wire/non-manifold
edges, disconnected components, n-gons and degenerate faces are described with
counts and local examples instead of being treated as universal defects.

The first corrective operation is deliberately narrower than the diagnostics.
`mesh_cleanup` can remove only truly isolated loose vertices, and only when the
quality check inspected the base mesh (`evaluated=false`). The hint carries a
base-geometry SHA-256 plus the expected loose-vertex count; Blender rechecks both,
works on a copied mesh datablock, swaps only after success and rejects stale
geometry, multi-user mesh data, shape keys, animation or constraints. BlenderBench
on Blender 5.2.2 validated one isolated-vertex removal plus stale-fingerprint
rejection while preserving the source `.blend` on disk. Zero-length edges and
zero-area faces now have that bounded contract: `degenerate_repair_preview` edits a
candidate copy, retains the exact original as an ORDAX backup and requires an
explicit commit or cancel. Explicit-selection Merge by Distance is now also available as a bounded preview workflow: callers must provide 2â€“64 base-mesh vertex indices, distance is capped at 0.001, unselected vertex identity is verified before the candidate is exposed, and commit/cancel use the same fingerprint guards. Other broader topology repairs remain review-only.

Sources: [surface-conforming modeling question](https://www.reddit.com/r/blenderhelp/comments/1iqqfnw/what_are_some_more_efficient_workflow_for_modeling_along_a_surface/),
[iterative topology/editability feedback on Blender MCP](https://www.reddit.com/r/OpenAI/comments/1we95z2/blender_mcp_is_impressive_but_not_that_useable_yet/),
[operator-driven modeling and per-step state feedback discussion](https://www.reddit.com/r/aigamedev/comments/1rml9vj/using_ai_agents_to_control_blender_modeling_tools/).

The newer MCP feedback thread describes the practical gap as iteration and
topology cleanup after an initial silhouette, rather than one-shot generation.
The agent-tooling discussion likewise favors editable native operations and
asks for scene statistics after each step. This supports a short loop of typed
operation, inspect, measured quality gate and visual review; it does not justify
automatically declaring every disconnected island or non-quad a defect.

## Suggested delivery sequence

1. **Concluído:** fixed-count linear `ARRAY` promovido após contratos positivos/
   negativos e BlenderBench real no Blender 5.2.2, mantendo limites de contagem,
   faces projetadas, nomes duplicados, rollback e integridade do `.blend`.
2. **Concluído:** `surface_scatter` com Geometry Nodes promovido após BlenderBench
   real, seed determinístico, contagem efetiva, hard cap de instâncias, orçamento
   de geometria projetada e rollback do modifier/node group.
3. **Concluído:** cutters Boolean tipados (`box`, `circle`, `slot`, `polygon`,
   `vent`) com Preview → Commit → Cancel não destrutivo, limites de geometria,
   rollback de uma operação, BlenderBench real e exposição no ORDAX Studio.
4. **Concluído:** repair hints component-aware no `mesh_quality` e primeiro
   `mesh_cleanup` revision-guarded para vértices realmente isolados, com cópia de
   datablock, hash stale guard, BlenderBench real e exposição no ORDAX Studio.
5. **Concluído:** `degenerate_repair_preview` para zero-length edges e faces de
   área zero, usando candidate mesh + backup oculto, Preview → Commit → Cancel,
   fingerprints stale/candidate guards e BlenderBench real no Blender 5.2.2.
6. **Próximo:** estudar reparos localizados ainda mais ambíguos, como merge por
   distância com seleção explícita ou pequenos hole-fill, sempre com preview,
   limites de região e rollback antes de qualquer commit.

Each mutation should stay small in the MCP surface: one composable typed action,
strict schemas, clear failure evidence, and visual/geometry inspection after
the action. Keep the existing generic script path as an explicitly enabled
expert escape hatch, not the default modeling interface.
