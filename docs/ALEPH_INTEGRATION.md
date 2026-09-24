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

## Actions

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

Examples:

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

## How this fits the 3D/game pipeline

Aleph is a **world-reference/data acquisition layer**, not a mesh generator by
itself. The intended OrdaX flow is:

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
        +--> Blender terrain construction
        +--> OSM road/building reconstruction
        +--> Street View / satellite material-reference analysis
        +--> AI 3D providers for missing/detail assets
        |
        v
Blender quality gate
        |
        v
Unity / Unreal / Godot / GLB export
```

The next environment-generation layer should consume the Aleph capture rather
than calling remote map services directly. That gives us a reusable local
snapshot and makes iterative 3D work much less dependent on network availability
or undocumented upstream endpoints.

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

## Upstream facts verified on 2026-09-24

At the audited revision, Aleph declares Python 3.11+, Pillow as its package
dependency, `alephgeo` as its CLI entry point, and an MIT license. Its published
CLI documents satellite, Street View, place resolution, area capture,
resume/export, terrain and OSM workflows.
