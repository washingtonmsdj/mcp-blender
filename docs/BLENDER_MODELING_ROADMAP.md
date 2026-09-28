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
of independent objects. The typed `ARRAY` plan has been added with a 64-copy
ceiling and a 500,000 evaluated-face budget. It remains pending BlenderBench
promotion, so it cannot mutate a live scene yet. Start with a fixed-count linear
array; add radial placement and curve fitting only after their origin and
orientation contracts can be proven with Blender 5.x fixtures.

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

This should be a separate typed Geometry Nodes operation, not arbitrary node
tree injection. It needs a declared source object, target surface, density or
count, seed, scale/rotation ranges, instance-vs-realized output and a strict
instance/face budget. It should report the seed and evaluated instance count so
an agent can reproduce and inspect the result. Preserve instances through
preview when possible; realize them only when a downstream operation requires
editable mesh geometry.

Sources: [randomized fastener workflow](https://www.reddit.com/r/blenderhelp/comments/1ipz5np/i_used_simple_array_modifiers_on_the_hex_nuts_is/),
[pattern-of-holes discussion](https://www.reddit.com/r/blender/comments/1985hfi/how_would_you_create_this_pattern/),
[Distribute Points on Faces manual](https://docs.blender.org/manual/en/4.4/modeling/geometry_nodes/point/distribute_points_on_faces.html).

### 3. More expressive non-destructive cutters

The current box-cutout action handles rectangular openings well. Community
hard-surface tool discussions repeatedly show demand for circular/slot/vent
profiles, panel grooves, in-draw bevels and a preview before committing a cut.
The next step should be a small set of typed cutter profiles with exact
dimensions and explicit cut/slice modes, using temporary cutter objects and
clean rollback. Do not add a generic `bpy.ops` or remote `eval` endpoint for this:
cutters need bounded inputs, deterministic names, evaluated-geometry budgets and
before/after evidence just like the existing actions.

Sources: [Hardflow workflow discussion](https://www.reddit.com/r/blender/comments/1ulu4nn/i_built_hardflow_a_free_opensource_hardsurface/),
[HardCuts parametric boolean workflow](https://www.reddit.com/r/blender/comments/1rufkb6/i_released_the_alpha_of_my_hard_surface_modeling/).

### 4. Retopology guidance rather than automated retopology

One user described manually extruding edges across a surface and asked for a
faster way to turn drawn guides into topology. Automated retopology and
interactive stroke tools depend on artistic judgment and viewport interaction.
The existing mesh-quality gate already measures topology counts; it now also
returns bounded edge/face/vertex examples with indices and local coordinates,
including n-gons and non-finite coordinates. It also groups disconnected mesh
components and reports bounded summaries with local bounds, so the artist or
agent can locate islands without another scene mutation. A caller can set
`max_connected_components` when a single continuous shell is required; multiple
components can be intentional. Next add repair hints and carefully bounded
corrective operations. Only later consider a typed retopo operation with an
explicit target density and a preview/rollback gate.

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

1. Promote the fixed-count linear `ARRAY` variant after adding positive and
   negative host contracts and real Blender 5.x BlenderBench controls for count,
   spacing, evaluated face limits, duplicate names, rollback and source-file
   integrity.
2. Add a fixed-seed Geometry Nodes surface scatter operation with instance
   count and memory budgets.
3. Expand box cutouts into a constrained library of slot, circle, polygon and
   vent cutters; retain live boolean previews and one-operation rollback.
4. Add component-aware repair hints and small corrective operations to the
   read-only mesh diagnostics before attempting automated topology changes.

Each mutation should stay small in the MCP surface: one composable typed action,
strict schemas, clear failure evidence, and visual/geometry inspection after
the action. Keep the existing generic script path as an explicitly enabled
expert escape hatch, not the default modeling interface.
