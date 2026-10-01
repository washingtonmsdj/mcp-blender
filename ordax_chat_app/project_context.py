"""Bounded project rules/skills context for ORDAX agents."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


_RULE_FILES = ("AGENTS.md", "CLAUDE.md")
_RULE_DIRS = (".ordax/rules", ".cursor/rules")
_SKILL_DIRS = (".ordax/skills",)


@dataclass(frozen=True)
class ContextDocument:
    kind: str
    relative_path: str
    text: str


@dataclass(frozen=True)
class ProjectAgentContext:
    documents: tuple[ContextDocument, ...]
    truncated: bool
    total_bytes: int

    def instructions_block(self) -> str:
        if not self.documents:
            return ""
        parts = [
            "Project-specific rules and skills follow. Treat them as durable project instructions. "
            "More specific instructions override generic ones; never infer permissions from them."
        ]
        for document in self.documents:
            parts.append(
                f"\n--- {document.kind.upper()}: {document.relative_path} ---\n{document.text.strip()}"
            )
        if self.truncated:
            parts.append(
                "\n[ORDAX NOTE] Additional project context exists but was omitted to stay within the context budget."
            )
        return "\n".join(parts).strip()


class ProjectContextLoader:
    def __init__(
        self,
        *,
        max_total_bytes: int = 256 * 1024,
        max_file_bytes: int = 64 * 1024,
        max_documents: int = 64,
    ):
        self.max_total_bytes = max_total_bytes
        self.max_file_bytes = max_file_bytes
        self.max_documents = max_documents

    @staticmethod
    def _safe_relative(root: Path, path: Path) -> str | None:
        try:
            resolved = path.resolve()
            relative = resolved.relative_to(root.resolve())
        except (OSError, ValueError):
            return None
        if ".git" in relative.parts:
            return None
        return relative.as_posix()

    def _candidate_files(self, root: Path) -> Iterable[tuple[str, Path]]:
        seen: set[Path] = set()

        for name in _RULE_FILES:
            path = root / name
            if path.is_file():
                resolved = path.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    yield "rules", path

        for directory_name in _RULE_DIRS:
            directory = root / directory_name
            if not directory.is_dir():
                continue
            for path in sorted(directory.rglob("*.md")):
                resolved = path.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    yield "rules", path

        for directory_name in _SKILL_DIRS:
            directory = root / directory_name
            if not directory.is_dir():
                continue
            for path in sorted(directory.rglob("SKILL.md")):
                resolved = path.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    yield "skill", path

    def load(self, project_root: str | Path) -> ProjectAgentContext:
        root = Path(project_root).expanduser().resolve()
        documents: list[ContextDocument] = []
        total_bytes = 0
        truncated = False

        for kind, path in self._candidate_files(root):
            if len(documents) >= self.max_documents:
                truncated = True
                break

            relative = self._safe_relative(root, path)
            if relative is None:
                continue
            try:
                raw = path.read_bytes()
            except OSError:
                continue
            if not raw:
                continue
            if len(raw) > self.max_file_bytes:
                raw = raw[: self.max_file_bytes]
                truncated = True
            if total_bytes + len(raw) > self.max_total_bytes:
                remaining = self.max_total_bytes - total_bytes
                if remaining <= 0:
                    truncated = True
                    break
                raw = raw[:remaining]
                truncated = True

            try:
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                continue
            text = text.strip()
            if not text:
                continue

            encoded = text.encode("utf-8")
            total_bytes += len(encoded)
            documents.append(
                ContextDocument(kind=kind, relative_path=relative, text=text)
            )
            if total_bytes >= self.max_total_bytes:
                truncated = True
                break

        return ProjectAgentContext(
            documents=tuple(documents),
            truncated=truncated,
            total_bytes=total_bytes,
        )
