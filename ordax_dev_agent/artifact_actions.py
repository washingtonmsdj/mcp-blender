"""Project-scoped artifact preview actions."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any

from .models import ActionResult


class ArtifactActions:
    def artifact_preview(self, payload: dict[str, Any]) -> ActionResult:
        project_artifact = str(payload.get("project_artifact_path") or "").strip()
        if project_artifact:
            project = self._project(payload)
            root = (project.root / "Artifacts").resolve()
            path = (root / project_artifact).resolve()
        else:
            name = str(payload.get("artifact_name", "hordax-prototype.png"))
            root = (self.config.state_dir / "artifacts" / self._project(payload).slug).resolve()
            if name in {"hordax-prototype.png", "hordax-prototype.json", "latest.png", "latest.json"}:
                manifest = root / "latest.json"
                if not manifest.is_file():
                    return ActionResult(False, "No successful capture for this project yet")
                latest = json.loads(manifest.read_text(encoding="utf-8"))
                path = Path(
                    latest["snapshot_path" if name.endswith(".json") else "artifact"]
                ).resolve()
            else:
                path = (root / name).resolve()

        try:
            path.relative_to(root)
        except ValueError:
            return ActionResult(False, "artifact path escaped allowed root")

        if not path.is_file():
            return ActionResult(False, f"artifact not found: {path}")

        source_size = path.stat().st_size
        max_bytes = max(4096, min(int(payload.get("max_bytes", 262144)), 2 * 1024 * 1024))
        thumbnail = bool(payload.get("thumbnail", False))
        output_format = path.suffix.lower().lstrip(".")
        mime_type = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "webp": "image/webp",
            "json": "application/json",
        }.get(output_format, "application/octet-stream")

        thumbnail_size = None
        data = b""
        if thumbnail:
            if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                return ActionResult(False, "thumbnail is supported only for raster images")
            try:
                import io
                from PIL import Image
            except ImportError:
                return ActionResult(False, "Pillow is required for artifact thumbnails")

            max_width = max(64, min(int(payload.get("max_width", 480)), 1600))
            max_height = max(64, min(int(payload.get("max_height", 320)), 1200))
            quality = max(30, min(int(payload.get("quality", 72)), 92))

            with Image.open(path) as image:
                # Ask JPEG decoders to reduce resolution before allocating pixels.
                image.draft("RGB", (max_width, max_height))
                image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                image = image.convert("RGB")
                thumbnail_size = [image.width, image.height]
                buffer = io.BytesIO()
                image.save(
                    buffer,
                    format="JPEG",
                    quality=quality,
                    optimize=True,
                    progressive=True,
                )
                data = buffer.getvalue()
            output_format = "jpeg"
            mime_type = "image/jpeg"
        elif source_size <= max_bytes:
            # A concurrent writer must not turn a bounded preview into a huge read.
            with path.open("rb") as handle:
                data = handle.read(max_bytes + 1)
        if (not thumbnail and source_size > max_bytes) or len(data) > max_bytes:
            return ActionResult(
                False,
                f"artifact is too large for inline preview: {max(source_size if not thumbnail else 0, len(data))} > {max_bytes}",
                {
                    "path": str(path),
                    "source_size_bytes": source_size,
                    "preview_size_bytes": len(data) if thumbnail else max(source_size, len(data)),
                    "thumbnail": thumbnail,
                },
            )

        return ActionResult(
            True,
            "artifact preview ready",
            {
                "artifact_name": path.name,
                "path": str(path),
                "source_size_bytes": source_size,
                "size_bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "mime_type": mime_type,
                "format": output_format,
                "thumbnail": thumbnail,
                "thumbnail_size": thumbnail_size,
                "base64": base64.b64encode(data).decode("ascii"),
            },
        )


