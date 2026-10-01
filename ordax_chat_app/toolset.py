"""Project-scoped development tools exposed to the embedded chat model."""
from __future__ import annotations

import json
from typing import Any


def _nullable(inner: dict[str, Any]) -> dict[str, Any]:
    return {"anyOf": [inner, {"type": "null"}]}


def _object(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


DEVELOPMENT_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "workspace_list",
        "description": "List files/directories in the selected project. Use this before guessing paths.",
        "parameters": _object({
            "path": {"type": "string"},
            "max_depth": {"type": "integer", "minimum": 1, "maximum": 8},
            "max_entries": {"type": "integer", "minimum": 1, "maximum": 1500},
            "include_hidden": {"type": "boolean"},
        }),
        "strict": True,
    },
    {
        "type": "function",
        "name": "workspace_read",
        "description": "Read UTF-8 text from the selected project. Prefer targeted line ranges for large files.",
        "parameters": _object({
            "path": {"type": "string"},
            "start_line": {"type": "integer", "minimum": 1},
            "end_line": _nullable({"type": "integer", "minimum": 1}),
        }),
        "strict": True,
    },
    {
        "type": "function",
        "name": "workspace_write",
        "description": "Create or replace a UTF-8 text file. Replacing an existing file requires the SHA-256 returned by workspace_read.",
        "parameters": _object({
            "path": {"type": "string"},
            "content": {"type": "string"},
            "expected_sha256": _nullable({"type": "string"}),
            "create": {"type": "boolean"},
        }),
        "strict": True,
    },
    {
        "type": "function",
        "name": "workspace_patch",
        "description": "Apply exact text replacements to a file using the SHA-256 returned by workspace_read.",
        "parameters": _object({
            "path": {"type": "string"},
            "expected_sha256": {"type": "string"},
            "replacements": {
                "type": "array",
                "minItems": 1,
                "maxItems": 50,
                "items": {
                    "type": "object",
                    "properties": {
                        "old": {"type": "string"},
                        "new": {"type": "string"},
                        "expected_count": {"type": "integer", "minimum": 1, "maximum": 1000},
                    },
                    "required": ["old", "new", "expected_count"],
                    "additionalProperties": False,
                },
            },
        }),
        "strict": True,
    },
    {
        "type": "function",
        "name": "workspace_mkdir",
        "description": "Create a directory inside the selected project.",
        "parameters": _object({
            "path": {"type": "string"},
            "parents": {"type": "boolean"},
        }),
        "strict": True,
    },
    {
        "type": "function",
        "name": "workspace_move",
        "description": "Move or rename a path inside the selected project.",
        "parameters": _object({
            "source": {"type": "string"},
            "destination": {"type": "string"},
            "expected_sha256": _nullable({"type": "string"}),
            "overwrite": {"type": "boolean"},
        }),
        "strict": True,
    },
    {
        "type": "function",
        "name": "workspace_remove",
        "description": "Remove a file or directory inside the selected project. Use recursive only when intentionally removing a non-empty directory.",
        "parameters": _object({
            "path": {"type": "string"},
            "expected_sha256": _nullable({"type": "string"}),
            "recursive": {"type": "boolean"},
        }),
        "strict": True,
    },
    {
        "type": "function",
        "name": "project_search",
        "description": "Search text across the selected project before editing unfamiliar code.",
        "parameters": _object({
            "query": {"type": "string"},
            "max_results": {"type": "integer", "minimum": 1, "maximum": 100},
            "max_files": {"type": "integer", "minimum": 50, "maximum": 5000},
            "case_sensitive": {"type": "boolean"},
        }),
        "strict": True,
    },
    {
        "type": "function",
        "name": "project_health",
        "description": "Inspect project health, Git state, memory and configured adapters.",
        "parameters": _object({}),
        "strict": True,
    },
    {
        "type": "function",
        "name": "git",
        "description": "Run a Git subcommand against the selected project, including status, diff, branch, add, commit, pull or push when authorized.",
        "parameters": _object({
            "args": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 80},
            "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 1200},
        }),
        "strict": True,
    },
    {
        "type": "function",
        "name": "terminal",
        "description": "Run a real foreground command in the selected project. Prefer argv. Use command+shell only when shell syntax is genuinely required.",
        "parameters": _object({
            "cwd": {"type": "string"},
            "argv": _nullable({"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 128}),
            "command": _nullable({"type": "string"}),
            "shell": {"type": "boolean"},
            "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 1800},
            "env": _nullable({
                "type": "array",
                "maxItems": 32,
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "value": {"type": "string"},
                    },
                    "required": ["name", "value"],
                    "additionalProperties": False,
                },
            }),
        }),
        "strict": True,
    },
    {
        "type": "function",
        "name": "process_start",
        "description": "Start a persistent project process such as a dev server, watcher or long-running build. The process survives ORDAX agent restarts and writes logs.",
        "parameters": _object({
            "cwd": {"type": "string"},
            "argv": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 128},
            "env": _nullable({
                "type": "array",
                "maxItems": 32,
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "value": {"type": "string"},
                    },
                    "required": ["name", "value"],
                    "additionalProperties": False,
                },
            }),
            "wait_seconds": {"type": "number", "minimum": 0.1, "maximum": 5.0},
        }),
        "strict": True,
    },
    {
        "type": "function",
        "name": "process_list",
        "description": "List persistent processes belonging to the selected project.",
        "parameters": _object({}),
        "strict": True,
    },
    {
        "type": "function",
        "name": "process_status",
        "description": "Inspect one persistent process by its ORDAX process ID.",
        "parameters": _object({
            "process_id": {"type": "string"},
        }),
        "strict": True,
    },
    {
        "type": "function",
        "name": "process_logs",
        "description": "Read the recent log tail from a persistent process.",
        "parameters": _object({
            "process_id": {"type": "string"},
            "max_bytes": {"type": "integer", "minimum": 1024, "maximum": 262144},
        }),
        "strict": True,
    },
    {
        "type": "function",
        "name": "process_stop",
        "description": "Stop a persistent ORDAX-owned process and its child process tree.",
        "parameters": _object({
            "process_id": {"type": "string"},
        }),
        "strict": True,
    },
    {
        "type": "function",
        "name": "preview_status",
        "description": "Inspect the selected project's managed preview/runtime state.",
        "parameters": _object({}),
        "strict": True,
    },
]


_TOOL_ACTIONS = {
    "workspace_list": "workspace.directory_list",
    "workspace_read": "workspace.text_read",
    "workspace_write": "workspace.text_write",
    "workspace_patch": "workspace.text_patch",
    "workspace_mkdir": "workspace.directory_create",
    "workspace_move": "workspace.path_move",
    "workspace_remove": "workspace.path_remove",
    "project_search": "project.search_text",
    "project_health": "agent.project_health",
    "git": "git.command",
    "terminal": "terminal.exec",
    "process_start": "process.start",
    "process_list": "process.list",
    "process_status": "process.status",
    "process_logs": "process.logs",
    "process_stop": "process.stop",
    "preview_status": "project.preview_status",
}


class DevelopmentToolset:
    def __init__(self, action_registry, *, project: str, max_output_bytes: int = 512 * 1024):
        self.action_registry = action_registry
        self.project = project
        self.max_output_bytes = max_output_bytes

    @property
    def definitions(self) -> list[dict[str, Any]]:
        return [dict(item) for item in DEVELOPMENT_TOOLS]

    def execute(self, name: str, arguments_json: str) -> str:
        action = _TOOL_ACTIONS.get(name)
        if action is None:
            return json.dumps({"ok": False, "summary": f"unknown ORDAX tool: {name}"})
        try:
            raw = json.loads(arguments_json or "{}")
        except json.JSONDecodeError as error:
            return json.dumps({"ok": False, "summary": f"invalid tool arguments: {error}"})
        if not isinstance(raw, dict):
            return json.dumps({"ok": False, "summary": "tool arguments must be an object"})

        definition = next((item for item in DEVELOPMENT_TOOLS if item["name"] == name), None)
        allowed = set((definition or {}).get("parameters", {}).get("properties", {}))
        unsupported = sorted(set(raw) - allowed)
        if unsupported:
            return json.dumps(
                {
                    "ok": False,
                    "summary": "unsupported tool argument(s): " + ", ".join(unsupported),
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )

        payload = {key: value for key, value in raw.items() if value is not None}
        if name in {"terminal", "process_start"} and isinstance(payload.get("env"), list):
            env: dict[str, str] = {}
            for item in payload["env"]:
                if not isinstance(item, dict):
                    return json.dumps({"ok": False, "summary": "terminal env entries must be objects"})
                key = str(item.get("name") or "")
                value = item.get("value")
                if not key or key in env or not isinstance(value, str):
                    return json.dumps({"ok": False, "summary": "terminal env names must be unique non-empty strings"})
                env[key] = value
            payload["env"] = env
        payload["project"] = self.project
        result = self.action_registry.execute(action, payload)
        output = {
            "ok": bool(result.ok),
            "summary": str(result.summary),
            "data": result.data if isinstance(result.data, dict) else {},
        }
        encoded = json.dumps(output, ensure_ascii=False, separators=(",", ":"), default=str)
        if len(encoded.encode("utf-8")) > self.max_output_bytes:
            encoded = json.dumps(
                {
                    "ok": False,
                    "summary": "tool output exceeded the model transfer limit; request a narrower range or more targeted command",
                    "data": {
                        "tool": name,
                        "max_output_bytes": self.max_output_bytes,
                    },
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
        return encoded
