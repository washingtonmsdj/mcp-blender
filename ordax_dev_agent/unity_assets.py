"""Project-local Unity asset inventory for typed OrdaX actions."""

from __future__ import annotations

from collections import Counter
import os
from pathlib import Path
from typing import Any


CLASS_BY_SUFFIX = {
    ".prefab": "prefab",
    ".mat": "material",
    ".asset": "asset",
    ".terrainlayer": "terrain_layer",
    ".unity": "scene",
    ".fbx": "model",
    ".obj": "model",
    ".blend": "model",
    ".png": "texture",
    ".jpg": "texture",
    ".jpeg": "texture",
    ".tga": "texture",
    ".psd": "texture",
    ".exr": "texture",
    ".hdr": "texture",
    ".wav": "audio",
    ".mp3": "audio",
    ".ogg": "audio",
    ".shader": "shader",
    ".shadergraph": "shader_graph",
    ".cs": "script",
}


def asset_inventory(
    project_root: Path,
    *,
    terms: list[str] | None = None,
    max_results: int = 500,
) -> dict[str, Any]:
    assets = project_root.resolve() / "Assets"
    if not assets.is_dir():
        return {
            "assets_root": str(assets),
            "exists": False,
            "total_files": 0,
            "matches": [],
            "counts_by_kind": {},
        }

    normalized_terms = [
        term.strip().lower()
        for term in (terms or [])
        if isinstance(term, str) and term.strip()
    ]
    max_results = max(1, min(int(max_results), 2000))

    matches: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    total = 0

    # os.walk preserves the textual root that was supplied. This matters on
    # Windows, where tempfile / CI paths can be represented simultaneously as
    # an 8.3 alias (RUNNER~1) and a long path (runneradmin). Path.rglob may
    # surface the long spelling and make relative_to() reject the same physical
    # directory as unrelated.
    for current_root, _, file_names in os.walk(str(assets)):
        current = Path(current_root)
        try:
            inside_assets = current.relative_to(assets)
        except ValueError:
            # Defensive fallback: the walk must never escape Assets.
            continue

        for file_name in file_names:
            path = current / file_name
            if path.suffix.lower() == ".meta":
                continue
            total += 1
            suffix = path.suffix.lower()
            kind = CLASS_BY_SUFFIX.get(suffix, "other")
            counts[kind] += 1

            rel_path = Path("Assets") / inside_assets / file_name
            rel = rel_path.as_posix()
            haystack = rel.lower()
            if normalized_terms and not all(term in haystack for term in normalized_terms):
                continue
            if len(matches) < max_results:
                try:
                    size = path.stat().st_size
                except OSError:
                    size = None
                matches.append({
                    "path": rel,
                    "name": path.name,
                    "kind": kind,
                    "extension": suffix,
                    "size_bytes": size,
                })

    return {
        "assets_root": str(assets),
        "exists": True,
        "query_terms": normalized_terms,
        "total_files": total,
        "matched_files": len(matches),
        "matches_truncated": len(matches) >= max_results,
        "counts_by_kind": dict(sorted(counts.items())),
        "matches": matches,
    }
