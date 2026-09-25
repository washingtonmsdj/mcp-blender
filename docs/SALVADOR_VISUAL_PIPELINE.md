# Salvador visual pipeline — Blender → Three.js → Godot / Unity

This tranche moves the Device Agent from generic 3D automation toward a shared visual-environment pipeline for the Salvador reconstruction.

## Direction

Blender remains the canonical DCC for geometry, UVs, materials, scene structure, LOD generation and visual reference renders. Realtime-only effects are represented by a shared environment contract rather than by attempting to transport Blender shader graphs verbatim.

The first realtime target is **Three.js WebGPU**. Godot and Unity remain supported engine targets and should consume the same semantic environment values wherever their rendering models allow it.

```text
Salvador source/reference data
        |
        v
Blender canonical scene
        |
        +--> geometry / UV / PBR / LOD
        +--> environment derivative/reference render
        +--> verified Web GLB
        |
        v
ordax.visual-environment/1
        |
        +--> Blender Nishita/Sun/Ocean reference
        +--> Three.js WebGPURenderer  <- current primary realtime target
        +--> Godot WorldEnvironment  <- follow-up mapping
        +--> Unity HDRP               <- follow-up mapping
```

## Visual environment contract

`ordax_dev_agent.visual_environment` defines `ordax.visual-environment/1`.

It deliberately keeps visual dimensions separate instead of hiding them behind one quality score:

- sun elevation, azimuth, illuminance and color temperature;
- sky turbidity, Rayleigh and Mie scattering controls;
- cloud coverage and density;
- horizon haze, visibility and fog controls;
- wind speed/direction;
- ocean sea level, significant wave height, swell period/direction, choppiness, foam and water colors;
- exposure and tone-mapping choice.

Built-in starting presets:

- `salvador_clear_noon`
- `salvador_golden_hour`

These are art-direction starting points, not claims of historical meteorological measurements. Scene-specific work should override values using references and the intended time/weather state.

Typed actions:

- `visual.environment_schema`
- `visual.environment_preset`
- `visual.environment_write`
- `visual.blender_environment_build`
- `visual.blender_environment_audit`

The contract is closed-world and range checked. Unknown fields are rejected instead of silently ignored.

## Blender environment derivative

`visual.blender_environment_build` opens a registered source `.blend` in an isolated background Blender process and saves a **separate derivative**. The host hashes the source before and after the operation and fails the result if the canonical source changed.

The first mapping currently applies:

- metric scene units;
- Nishita Sky Texture in the World node tree;
- shared sun elevation/azimuth to both the Sky Texture and a deterministic `SUN` object;
- color-temperature approximation for the sun light;
- EV100-derived Blender exposure and AgX when requested;
- a conservative Principled Volume atmosphere from the shared fog value;
- an `Ocean` modifier reference surface at the shared sea level;
- wave scale/choppiness/wind/direction/foam mapping;
- a Principled water reference material with shared deep-water color and roughness;
- full environment JSON embedded as scene metadata for later audit/provenance.

`visual.blender_environment_audit` reopens a `.blend` read-only through the same isolated CLI path and verifies the embedded environment metadata, physical sky node, Sun object and Ocean modifier when ocean is enabled.

This is deliberately a **reference rendering mapping**, not a claim that Blender's Ocean modifier/shader is portable to Three.js, Godot or Unity.

## Three.js visual viewer

`game_assets.threejs_prepare_viewer` consumes a verified **web-targeted, self-contained GLB** plus an optional environment override and creates a project-local Vite viewer.

The generated runtime currently pins:

- Three.js `0.186.0`
- Vite `8.3.0`
- `WebGPURenderer` with its WebGL2 fallback
- `SkyMesh` for physical-ish sky / sun / procedural cloud presentation
- `WaterMesh` for the first ocean surface
- `GLTFLoader`
- soft shadows, directional sunlight, atmospheric fog, camera auto-framing and runtime draw-call/triangle telemetry

The action copies both the verified GLB and its OrdaX provenance manifest into the viewer. The source `.blend` and source export are never mutated.

Default output:

```text
ordax/threejs-viewer/
  package.json
  index.html
  src/main.js
  public/ordax/
    model.glb
    model.glb.ordax.json
    environment.json
    runtime.json
```

Then:

```bash
npm install
npm run dev
```

`game_assets.threejs_runtime_audit` verifies the generated viewer structure, pinned versions, environment contract, GLB structure and copied GLB hash.

A separate `game_assets.threejs_browser_validate` gate now loads the verified Web GLB in local Three.js through Chrome/Chromium, builds a real scene, renders it, reads pixels and returns geometry/material/texture/render evidence. That gate proves a browser can load and render the GLB; it does **not yet** prove the full WebGPU sky/ocean viewer matches the Blender environment reference.

## Why the ocean remains a separate runtime system

A Blender Ocean Modifier or Blender shader cannot be treated as a portable realtime artifact. The portable source of truth is the semantic water state: sea level, wind, wave/swell parameters, choppiness, foam, absorption/color and roughness.

Blender maps those values into an Ocean-modifier reference surface. Three.js currently maps them to the first `WaterMesh` implementation. The next visual iterations should add:

1. multi-band Gerstner displacement in TSL;
2. camera-centered ocean LOD/rings;
3. crest foam from slope/Jacobian evidence;
4. shore foam/depth interaction;
5. reflection/environment prefiltering;
6. boat wake emitters;
7. a spectral/compute path only after the simpler implementation is visually measured.

The same environment manifest should later drive Godot and Unity implementations rather than duplicating authored weather/ocean values per engine.

## Immediate next gates

### P0 — real Blender environment smoke

Run the new builder through the real workstation Blender 5.x and prove:

- the source `.blend` hash is unchanged;
- the derivative opens successfully;
- Nishita + Sun + Ocean survive save/reopen;
- a deterministic camera render completes;
- the audit passes on the saved derivative;
- a negative/invalid environment control fails closed.

Only after that smoke should the Blender environment mapping be treated as production-promoted.

### P0 — visual cross-runtime comparison

Extend browser evidence from the generic GLB gate to the prepared WebGPU environment viewer:

- deterministic camera shared with Blender reference framing;
- WebGPU/backend evidence;
- screenshot artifact and console errors;
- sky/ocean/atmosphere visible in the capture;
- pixel/structural comparison against the Blender reference without requiring identical shaders.

### P1 — PBR material contract v2

Expand beyond scalar Principled values to texture-bearing PBR:

- base color, normal, roughness, metallic, occlusion, emissive;
- clearcoat, IOR, transmission/thickness where portable;
- UV set/scale/rotation;
- texture provenance and color-space rules;
- KTX2/BasisU delivery as a post-validation optimization stage.

### P1 — Salvador surface library

Build reusable measured/reference-guided families for:

- painted plaster and aged stucco;
- concrete;
- asphalt;
- Portuguese/Bahian stone paving and sidewalks;
- ceramic roof tiles;
- glass and metal;
- seawalls/rocks/sand;
- dirt, moisture, moss, rust and facade weathering through decals/masks.

### P1 — Godot and Unity environment adapters

Map the same contract to:

- Godot `WorldEnvironment`, directional sun, fog and water shader;
- Unity HDRP Volume, Physically Based Sky, Directional Light, fog/cloud/water equivalents.

Do not require visual parity by identical shader code. Require semantic parity plus captured visual evidence.
