from __future__ import annotations

import sys
import zipfile
from pathlib import Path


REQUIRED = {
    "ordax_studio/studio.html",
    "ordax_studio/assets/studio.js",
    "ordax_studio/assets/studio.css",
    "ordax_studio/assets/blender-connection.js",
    "ordax_studio/assets/blender-connection.css",
}


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_packaged_studio_assets.py <wheel-or-directory>")
    target = Path(sys.argv[1]).resolve()
    if target.is_dir():
        wheels = sorted(target.glob("*.whl"))
        if len(wheels) != 1:
            raise SystemExit(f"expected exactly one wheel in {target}, found {len(wheels)}")
        target = wheels[0]
    if not target.is_file() or target.suffix != ".whl":
        raise SystemExit(f"wheel not found: {target}")

    with zipfile.ZipFile(target) as archive:
        names = set(archive.namelist())
    missing = sorted(REQUIRED - names)
    if missing:
        raise SystemExit("wheel is missing ORDAX Studio assets: " + ", ".join(missing))
    print(f"ORDAX Studio package assets OK: {target.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
