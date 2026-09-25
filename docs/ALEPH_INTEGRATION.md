# Aleph geospatial capture integration

OrdaX integrates [Belluxx/Aleph](https://github.com/Belluxx/Aleph) as a managed
external geospatial component for world/environment generation.

Aleph can provide a project with:

- satellite imagery (`satellite.png` and GeoTIFF/COG output);
- terrain/elevation data;
- OpenStreetMap roads, buildings and other mapped objects;
- Street View reference photographs;
- named-place and nearby-POI resolution;
- resumable rectangular area captures.

The upstream project is MIT licensed and requires Python 3.11+. It explicitly
warns that some data access uses undocumented APIs, so OrdaX treats it as a
replaceable external dependency rather than vendoring its implementation.

## Managed installation

No manual global `pip install` is required.

On first use of an Aleph data action, the Device Agent automatically installs a
known-good upstream revision into:

```text
<state-dir>/components/aleph/
  repo/
  venv/
  component.json
```

The currently audited default is:

```text
Belluxx/Aleph
commit 502667d0b46e67555c7956d4ff281be5e8511a30
package 0.1.0
```

Installation creates a dedicated virtual environment and installs the checkout
in editable mode. The upstream Git origin is checked before updates, and the
resolved commit is stored in `component.json`.

`geo.aleph_update` is the explicit opt-in path for moving the managed checkout
to the latest upstream `main`. Normal first-use installation stays pinned for
reproducibility.

## Data acquisition actions

### `geo.aleph_status`

Reports whether the managed component is installed and healthy, the pinned
revision and the local component root. It does not install anything.

### `geo.aleph_ensure`

Installs the pinned revision if needed and verifies `alephgeo --help`.

### `geo.aleph_update`

Fetches the upstream repository, checks out current `origin/main`, reinstalls it
inside the isolated venv and records the resolved commit.

### `geo.aleph_resolve`

Typed wrapper around Aleph place/reverse/nearby lookup.

```json
{
  "action": "geo.aleph_resolve",
  "project": "my-world",
  "arguments": {
    "query": "Elevador Lacerda, Salvador"
  }
}
```

```json
{
  "action": "geo.aleph_resolve",
  "project": "my-world",
  "arguments": {
    "at": [-12.9714, -38.5014],
    "nearby": true,
    "radius": 300,
    "limit": 20
  }
}
```

### `geo.aleph_satellite`

Downloads a satellite reference by place, coordinates, bounding box, or an
exact `Z/X/Y` tile. Output is always confined to the registered project.

```json
{
  "action": "geo.aleph_satellite",
  "project": "my-world",
  "arguments": {
    "at": [-12.9714, -38.5014],
    "size": 500,
    "zoom": 19,
    "format": "png",
    "output_dir": "generated/aleph/salvador"
  }
}
```

Aleph generates a merged PNG and GeoTIFF/COG for satellite-area captures; the
selected `format` controls saved source tiles.

### `geo.aleph_streetview`

Captures one panorama-derived reference or a sampled street sequence. Primary
selectors match upstream Aleph: exactly one of `place`, `at`, `street`, or
`pano_id`.

```json
{
  "action": "geo.aleph_streetview",
  "project": "my-world",
  "arguments": {
    "street": "Avenida Sete de Setembro, Salvador",
    "best_match": true,
    "stops": 12,
    "view": "both",
    "format": "png"
  }
}
```

### `geo.aleph_capture`

Downloads a rectangular environment reference pack. Aleph sources are:

- `streetview`
- `satellite`
- `osm` — includes terrain

The OrdaX wrapper always sends `--no-plan`, because an agent action cannot wait
for an interactive confirmation prompt.

```json
{
  "action": "geo.aleph_capture",
  "project": "my-world",
  "arguments": {
    "bbox": [-12.975, -38.506, -12.970, -38.498],
    "sources": ["osm", "satellite", "streetview"],
    "satellite_zoom": 19,
    "terrain_zoom": 14,
    "step": 20,
    "output_dir": "generated/aleph/captures"
  }
}
```

To protect the workstation and upstream services from accidental city-scale
requests, captures above roughly 100 km² require explicit
`allow_large_area=true`.

### `geo.aleph_capture_resume`

Continues a project-local Aleph capture containing `manifest.json`.

### `geo.aleph_capture_export`

Rebuilds outputs from an already downloaded capture offline.

## Capture inspection and Blender reconstruction

### `geo.aleph_capture_inspect`

Inspects a capture without downloading anything. It validates the Aleph manifest
format/version, reports capture bounds/state/stage progress, inventories core
files and exposes which reconstruction capabilities are available:

- terrain mesh from `terrain.tif`;
- satellite material from `satellite.png`;
- buildings and roads from `map.osm`;
- georeferenced Street View references from `streetview/photos.geojson`.

```json
{
  "action": "geo.aleph_capture_inspect",
  "project": "my-world",
  "arguments": {
    "capture_dir": "generated/aleph/captures/aleph-20260924T200000Z-abcd"
  }
}
```

### `geo.aleph_blender_stage`

Builds a new project-local `.blend` from an immutable Aleph capture.

The conversion is two-phase:

```text
Aleph capture
    |
    +--> managed Aleph Python/Pillow preprocessor
    |      terrain.tif -> sampled terrain mesh + UVs
    |      map.osm     -> buildings + road polylines
    |      satellite   -> local texture reference
    |
    +--> Blender --background --factory-startup
           terrain + satellite material
           OSM building massing
           width-classed road curves
           Street View reference cameras
           provenance / coordinate metadata
           packed satellite image
           -> output .blend
```

Example:

```json
{
  "action": "geo.aleph_blender_stage",
  "project": "my-world",
  "arguments": {
    "capture_dir": "generated/aleph/captures/aleph-20260924T200000Z-abcd",
    "output_blend": "world/salvador_reference.blend",
    "terrain_samples": 192,
    "include_terrain": true,
    "include_buildings": true,
    "include_roads": true,
    "use_satellite": true
  }
}
```

`terrain_samples` controls the largest terrain-grid dimension and is bounded to
16–512. The default is 128. This gives an explicit fidelity/performance knob
instead of silently producing a huge mesh from every source pixel.

Existing `.blend` output is never replaced unless `overwrite=true` is explicit.
Temporary neutral staging data is deleted after a successful build unless
`keep_staging=true` is requested. Diagnostic JSON reports are retained under the
agent artifact directory.

### Coordinate strategy

Aleph terrain is georeferenced in EPSG:3857 and its capture bounds are WGS84.
OrdaX converts those coordinates to **local metres centered on the capture**
before Blender ingestion:

```text
Web Mercator absolute X/Y
        - capture center
        = Blender local X/Y metres

terrain elevation
        - minimum sampled capture elevation
        = Blender local Z metres
```

This deliberately avoids putting multi-million-metre Earth coordinates directly
into Blender, where float precision becomes an unnecessary problem. The original
bounds, EPSG:3857 origin and base elevation are stored as scene/object metadata
so the derived scene remains traceable to geographic space.

### Terrain

`terrain.tif` is sampled only inside the requested capture bounds. The generated
mesh gets UVs covering 0–1 across the same rectangle. When `satellite.png` is
available, it is applied as a terrain material and packed into the `.blend` so
the work scene does not silently lose the texture when staging files are cleaned.

### Buildings

The OSM converter supports ordinary closed building ways and outer rings from
building multipolygon relations. Heights are resolved in this order:

1. explicit `height` (metres or feet);
2. `building:levels × 3.2 m`;
3. 9 m fallback.

`min_height` / `building:min_level` are also honored. Building heights are
bounded to protect against malformed tags. Buildings are placed against sampled
terrain elevation when terrain is available.

Current inner multipolygon rings/holes are recorded as simplified rather than
silently claimed as exact geometry. A later architectural-detail pass can turn
those into boolean courtyards if required.

### Roads

OSM `highway=*` ways are converted to 3D polylines and grouped by width in
Blender curve objects. An explicit OSM `width` wins; otherwise OrdaX applies
bounded class defaults for motorway/trunk/primary/secondary/residential/service,
footway/cycleway/path and related classes. Road points follow terrain height when
terrain is present.

These roads are reference/game-blockout geometry, not a claim of civil-survey
precision. They are designed to provide a structurally useful starting point for
later road-network, collision and gameplay passes.

### Street View reference cameras

When `streetview/photos.geojson` exists, the Blender builder creates a bounded,
evenly sampled set of up to 64 `ALEPH_StreetView` cameras. Each camera uses the
photo's geographic position, heading, pitch and FOV, sits approximately at eye
height above the terrain, and stores the local reference-image path plus useful
panorama/road metadata.

The photos are **not packed automatically** into the `.blend`. Keeping them as
local references avoids turning a work file into a multi-gigabyte archive while
still making the evidence available to Blender/OrdaX tooling.

## How this fits the 3D/game pipeline

Aleph is a **world-reference/data acquisition layer**. The new staging layer
turns that evidence into editable game-world blockout/reference geometry:

```text
real-world place / bbox
        |
        v
Aleph
  satellite + terrain + OSM + Street View
        |
        v
project-local immutable/reference capture
        |
        v
geo.aleph_blender_stage
  terrain + UV/satellite
  building massing
  road curves
  Street View cameras
        |
        +--> Blender detail/modeling passes
        +--> AI 3D providers for missing/detail assets
        +--> Mixamo / animation pipeline for characters
        +--> reference/visual quality gates
        |
        v
Unity / Unreal / Godot / GLB export
```

The capture remains canonical and unmodified. The `.blend` is a reproducible
derivative, so terrain/buildings/roads can be regenerated at another fidelity
without layering destructive edits onto raw geospatial data.

## Reliability and security rules

1. Aleph is installed only from the hard-coded `Belluxx/Aleph` origin.
2. First-use installation is pinned to an audited commit.
3. Updates are explicit and record the resulting upstream commit.
4. Aleph runs from its own virtual environment.
5. OrdaX does not accept arbitrary Aleph executable/repository URLs.
6. Generated/captured output paths must remain inside the registered project.
7. Capture size is bounded by default.
8. OrdaX requests JSON output; subprocess progress/error text is bounded before
   returning to model context.
9. Captures should be retained/cached because the upstream project warns that
   undocumented APIs may break or rate-limit without notice.
10. Aleph-to-Blender conversion performs no map-network requests; it consumes the
    completed local capture.
11. Blender reconstruction starts from `--factory-startup` and writes a new
    project-local `.blend`; replacement requires explicit overwrite.
12. Generated geometry is centered in local metre space while geographic
    provenance remains stored as metadata.

## Upstream facts verified on 2026-09-24

At the audited revision, Aleph declares Python 3.11+, Pillow as its package
dependency, `alephgeo` as its CLI entry point, and an MIT license. Its published
CLI documents satellite, Street View, place resolution, area capture,
resume/export, terrain and OSM workflows.
