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
        +--> verified Web GLB
        |
        v
ordax.visual-environment/1
        |
        +--> Three.js WebGPURenderer  <- current primary target
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

The contract is closed-world and range checked. Unknown fields are rejected instead of silently ignored.

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

Dependency installation remains explicit:

```bash
npm install
```

OrdaX does not silently install npm dependencies because that would introduce network and lifecycle-script execution into an otherwise bounded validation action.

### Viewer gates now implemented

```text
game_assets.threejs_prepare_viewer
  -> game_assets.threejs_runtime_audit
  -> explicit npm install when node_modules is absent
  -> game_assets.threejs_viewer_validate
```

`game_assets.threejs_runtime_audit` verifies the generated runtime structure, pinned versions, environment contract, GLB structure and copied GLB hash.

`game_assets.threejs_viewer_validate` goes further. It requires the pinned Three.js and Vite versions to already be installed, refuses a modified build script, executes only the generated `vite build`, requires `dist/index.html` plus the copied GLB, serves the built viewer on an ephemeral `127.0.0.1` server with a restrictive CSP, and runs Chrome/Chromium headless without disabling its sandbox or enabling unsafe SwiftShader fallback.

The built viewer must update its own HUD after rendering. OrdaX reads that proof and checks:

- WebGPU versus WebGL2 fallback;
- environment name;
- model provenance hash prefix;
- rendered triangle count;
- draw-call count.

Workflows can require WebGPU explicitly. A viewer that successfully renders through WebGL2 still fails when `require_webgpu=true`.

A separate `game_assets.threejs_browser_validate` gate exists for the verified GLB itself. It loads the raw GLB with `GLTFLoader`, renders it to an offscreen WebGL render target, reads pixels back and records geometry/material/animation metrics plus visible-pixel evidence. This keeps raw-asset compatibility separate from the complete Salvador visual stack.

## Ocean implementation status

A Blender Ocean Modifier or Blender shader cannot be treated as a portable realtime artifact. The portable source of truth is the semantic water state: sea level, wind, wave/swell parameters, choppiness, foam, absorption/color and roughness.

The current Three.js viewer uses `WaterMesh`, which already animates multiple samples of the supplied normal map over time. The current implementation therefore provides reflective moving surface detail, but it is **not yet a geometrically displaced ocean spectrum**. In particular, `significant_wave_height_m` is not yet represented as real crest/trough displacement.

The next ocean tranche should therefore focus on measurable improvements rather than replacing the renderer blindly:

1. derive dominant wavelength from swell period and align wave bands to swell/wind direction;
2. replace random normal noise with deterministic directional multi-band ocean normals;
3. add multi-band Gerstner displacement in TSL using significant wave height and choppiness;
4. add camera-centered ocean LOD/rings so large Salvador bay views remain stable;
5. derive crest foam from slope/Jacobian evidence instead of a constant opacity mask;
6. add shore foam/depth interaction once shoreline/depth data is available;
7. improve reflection/environment prefiltering and shallow/deep absorption;
8. add wake emitters only after the base sea state is visually validated;
9. consider a spectral/compute path only after the simpler TSL model is measured and shown insufficient.

The same environment manifest should later drive Godot and Unity implementations rather than duplicating authored weather/ocean values per engine.

## Immediate next gates

### P0 — visual evidence and performance

The original browser-proof milestone is now partially complete. Implemented today:

- deterministic build verification;
- local loopback server;
- browser execution;
- WebGPU vs WebGL2-fallback evidence;
- model/environment provenance checks;
- triangle and draw-call telemetry;
- raw-GLB offscreen pixel readback.

Still required for the production-quality visual gate:

- persistent screenshot evidence from the full WebGPU viewer;
- console-error capture;
- frame-time/FPS and GPU-memory-friendly telemetry;
- fixed named camera viewpoints for Salvador landmarks;
- image regression against approved reference captures with explicit tolerance rather than a single opaque quality score.

### P0 — Blender environment application

Add Blender-side application of `ordax.visual-environment/1`:

- Nishita/physical sky mapping;
- Sun light mapping;
- world exposure/color management;
- ocean reference surface and Ocean Modifier parameters;
- deterministic reference render/capture.

This lets Blender and Three.js be compared from the same semantic environment.

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
