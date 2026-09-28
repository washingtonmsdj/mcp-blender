from __future__ import annotations

from typing import Any

from ordax_core import MemoryStore

from .models import ActionResult


class MemoryActions:
    def _memory_store_instance(self) -> MemoryStore:
        store = getattr(self, "_ordax_memory_store", None)
        if store is None:
            store = MemoryStore()
            self._ordax_memory_store = store
        return store

    def memory_status(self, payload: dict[str, Any]) -> ActionResult:
        status = self._memory_store_instance().status()
        return ActionResult(True, "Persistent memory is available", status)

    def memory_context(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project(payload)
        store = self._memory_store_instance()
        data = store.context(project.slug, project.root)
        data["context_path"] = str(store.write_context(project.slug, project.root))
        return ActionResult(True, f"Persistent context loaded for {project.slug}", data)

    def memory_remember(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project(payload)
        content = str(payload.get("content") or "").strip()
        kind = str(payload.get("kind") or "note").strip()[:64] or "note"
        memory_id = self._memory_store_instance().remember(project.slug, project.root, content, kind)
        return ActionResult(True, f"Memory #{memory_id} saved for {project.slug}", {"memory_id": memory_id})

    def memory_task_add(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project(payload)
        task_id = self._memory_store_instance().add_task(
            project.slug, project.root, str(payload.get("title") or "")
        )
        return ActionResult(True, f"Task #{task_id} saved for {project.slug}", {"task_id": task_id})

    def memory_task_toggle(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project(payload)
        try:
            task_id = int(payload.get("task_id"))
        except (TypeError, ValueError) as error:
            raise ValueError("task_id must be an integer") from error
        done = self._memory_store_instance().toggle_task(project.slug, project.root, task_id)
        return ActionResult(True, f"Task #{task_id} updated", {"task_id": task_id, "done": done})

    def memory_checkpoint(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project(payload)
        checkpoint_id = self._memory_store_instance().checkpoint(
            project.slug, project.root, str(payload.get("summary") or "")
        )
        return ActionResult(
            True,
            f"Checkpoint #{checkpoint_id} saved for {project.slug}",
            {"checkpoint_id": checkpoint_id},
        )
