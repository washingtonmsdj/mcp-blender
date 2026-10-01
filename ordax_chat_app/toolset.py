"""Project-scoped development tools exposed to the embedded chat model."""
from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ToolExecutionResult:
    output: str
    followup_items: list[dict[str, Any]]


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
        "name": "process_stdin",
        "description": "Send text to stdin of a running ORDAX-managed persistent process.",
        "parameters": _object({
            "process_id": {"type": "string"},
            "text": {"type": "string"},
            "newline": {"type": "boolean"},
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
        "name": "browser",
        "description": "Operate an ORDAX-owned Chromium session. Use snapshot before click/type so node IDs are current. Operations: start, list, status, navigate, snapshot, click, type, screenshot, stop.",
        "parameters": _object({
            "operation": {
                "type": "string",
                "enum": ["start", "list", "status", "navigate", "snapshot", "click", "type", "screenshot", "stop"],
            },
            "session_id": _nullable({"type": "string"}),
            "url": _nullable({"type": "string"}),
            "headless": _nullable({"type": "boolean"}),
            "wait_seconds": _nullable({"type": "number", "minimum": 0.1, "maximum": 30.0}),
            "node_id": _nullable({"type": "string"}),
            "text": _nullable({"type": "string"}),
            "clear": _nullable({"type": "boolean"}),
            "max_elements": _nullable({"type": "integer", "minimum": 20, "maximum": 500}),
            "width": _nullable({"type": "integer", "minimum": 320, "maximum": 2560}),
            "height": _nullable({"type": "integer", "minimum": 240, "maximum": 1600}),
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
    {
        "type": "function",
        "name": "agents",
        "description": "Coordinate persistent ORDAX workers for the selected project. Operations: status, create_worker, delegate, inbox, message. Workers report back through their coordinator.",
        "parameters": _object({
            "operation": {
                "type": "string",
                "enum": ["status", "create_worker", "delegate", "inbox", "message"],
            },
            "worker_id": _nullable({"type": "string"}),
            "name": _nullable({"type": "string"}),
            "role": _nullable({"type": "string"}),
            "title": _nullable({"type": "string"}),
            "instruction": _nullable({"type": "string"}),
            "priority": _nullable({"type": "integer", "minimum": 0, "maximum": 100}),
            "message": _nullable({"type": "string"}),
            "unread_only": _nullable({"type": "boolean"}),
        }),
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
    "process_stdin": "process.write_stdin",
    "process_stop": "process.stop",
    "preview_status": "project.preview_status",
}


class DevelopmentToolset:
    def __init__(
        self,
        action_registry,
        *,
        project: str,
        max_output_bytes: int = 512 * 1024,
        orchestrator=None,
        agent_id: str | None = None,
    ):
        self.action_registry = action_registry
        self.project = project
        self.max_output_bytes = max_output_bytes
        self.orchestrator = orchestrator
        self.agent_id = agent_id

    @property
    def definitions(self) -> list[dict[str, Any]]:
        return [dict(item) for item in DEVELOPMENT_TOOLS]

    def execute_with_followups(self, name: str, arguments_json: str) -> ToolExecutionResult:
        raw_output = self.execute(name, arguments_json)
        try:
            envelope = json.loads(raw_output)
        except json.JSONDecodeError:
            return ToolExecutionResult(raw_output, [])
        if not isinstance(envelope, dict):
            return ToolExecutionResult(raw_output, [])
        data = envelope.get("data")
        if not isinstance(data, dict):
            return ToolExecutionResult(raw_output, [])

        raw_path = data.pop("image_path", None)
        if not raw_path:
            return ToolExecutionResult(
                json.dumps(envelope, ensure_ascii=False, separators=(",", ":"), default=str),
                [],
            )
        try:
            image_path = Path(str(raw_path)).expanduser().resolve()
            state_root = Path(self.action_registry.config.state_dir).expanduser().resolve()
            image_path.relative_to(state_root)
        except (OSError, ValueError):
            envelope["ok"] = False
            envelope["summary"] = "visual tool returned an image outside ORDAX state"
            return ToolExecutionResult(
                json.dumps(envelope, ensure_ascii=False, separators=(",", ":"), default=str),
                [],
            )
        if not image_path.is_file():
            envelope["ok"] = False
            envelope["summary"] = "visual tool image is missing"
            return ToolExecutionResult(
                json.dumps(envelope, ensure_ascii=False, separators=(",", ":"), default=str),
                [],
            )
        size = image_path.stat().st_size
        if size <= 0 or size > 8 * 1024 * 1024:
            envelope["ok"] = False
            envelope["summary"] = "visual tool image exceeds the ORDAX vision transfer limit"
            return ToolExecutionResult(
                json.dumps(envelope, ensure_ascii=False, separators=(",", ":"), default=str),
                [],
            )
        mime = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
        }.get(image_path.suffix.lower())
        if mime is None:
            envelope["ok"] = False
            envelope["summary"] = "visual tool returned an unsupported image format"
            return ToolExecutionResult(
                json.dumps(envelope, ensure_ascii=False, separators=(",", ":"), default=str),
                [],
            )
        encoded_image = base64.b64encode(image_path.read_bytes()).decode("ascii")
        output = json.dumps(envelope, ensure_ascii=False, separators=(",", ":"), default=str)
        followup = {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": f"Visual output captured by ORDAX tool {name}. Analyze this image as tool evidence.",
                },
                {
                    "type": "input_image",
                    "image_url": f"data:{mime};base64,{encoded_image}",
                    "detail": "auto",
                },
            ],
        }
        return ToolExecutionResult(output, [followup])

    def execute(self, name: str, arguments_json: str) -> str:
        try:
            raw = json.loads(arguments_json or "{}")
        except json.JSONDecodeError as error:
            return json.dumps({"ok": False, "summary": f"invalid tool arguments: {error}"})
        if not isinstance(raw, dict):
            return json.dumps({"ok": False, "summary": "tool arguments must be an object"})

        action = _TOOL_ACTIONS.get(name)
        if name == "agents":
            return self._execute_agents(raw)
        if name == "browser":
            operation = str(raw.get("operation") or "")
            action = {
                "start": "browser.start",
                "list": "browser.list",
                "status": "browser.status",
                "navigate": "browser.navigate",
                "snapshot": "browser.snapshot",
                "click": "browser.click",
                "type": "browser.type",
                "screenshot": "browser.screenshot",
                "stop": "browser.stop",
            }.get(operation)
        if action is None:
            return json.dumps({"ok": False, "summary": f"unknown ORDAX tool or operation: {name}"})

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
        if name == "browser":
            payload.pop("operation", None)
            allowed_by_operation = {
                "browser.start": {"url", "headless", "wait_seconds"},
                "browser.list": set(),
                "browser.status": {"session_id"},
                "browser.navigate": {"session_id", "url", "wait_seconds"},
                "browser.snapshot": {"session_id", "max_elements"},
                "browser.click": {"session_id", "node_id"},
                "browser.type": {"session_id", "node_id", "text", "clear"},
                "browser.screenshot": {"session_id", "width", "height"},
                "browser.stop": {"session_id"},
            }
            allowed_payload = allowed_by_operation[action]
            unexpected = sorted(set(payload) - allowed_payload)
            if unexpected:
                return json.dumps(
                    {
                        "ok": False,
                        "summary": "unsupported browser argument(s) for operation: " + ", ".join(unexpected),
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
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


    def _execute_agents(self, raw: dict[str, Any]) -> str:
        if self.orchestrator is None or not self.agent_id:
            return json.dumps(
                {"ok": False, "summary": "agent coordination is unavailable in this session"},
                ensure_ascii=False,
                separators=(",", ":"),
            )
        definition = next((item for item in DEVELOPMENT_TOOLS if item["name"] == "agents"), None)
        allowed = set((definition or {}).get("parameters", {}).get("properties", {}))
        unsupported = sorted(set(raw) - allowed)
        if unsupported:
            return json.dumps(
                {"ok": False, "summary": "unsupported tool argument(s): " + ", ".join(unsupported)},
                ensure_ascii=False,
                separators=(",", ":"),
            )

        operation = str(raw.get("operation") or "")
        current = self.orchestrator.get_agent(self.agent_id)
        if current["project_slug"] != self.project:
            return json.dumps(
                {"ok": False, "summary": "current agent is not bound to the selected project"},
                ensure_ascii=False,
                separators=(",", ":"),
            )

        try:
            if operation == "status":
                status = self.orchestrator.status(self.project)
                data = {
                    "current_agent": current,
                    "agents": status["agents"],
                    "goals": status["goals"],
                    "work_counts": status.get("work_counts", {}),
                    "unread_messages": status.get("unread_messages", 0),
                }
                summary = "Agent team status ready"

            elif operation == "create_worker":
                if current.get("parent_agent_id") is not None:
                    raise ValueError("only a coordinator can create workers")
                name = str(raw.get("name") or "").strip()
                role = str(raw.get("role") or "").strip()
                if not name or not role:
                    raise ValueError("name and role are required for create_worker")
                data = self.orchestrator.create_agent(
                    self.project,
                    name,
                    role,
                    parent_agent_id=self.agent_id,
                )
                summary = f"Worker created: {data['name']}"

            elif operation == "delegate":
                if current.get("parent_agent_id") is not None:
                    raise ValueError("only a coordinator can delegate work")
                worker_id = str(raw.get("worker_id") or "").strip()
                title = str(raw.get("title") or "").strip()
                instruction = str(raw.get("instruction") or "").strip()
                if not worker_id or not title or not instruction:
                    raise ValueError("worker_id, title and instruction are required for delegate")
                worker = self.orchestrator.get_agent(worker_id)
                if worker.get("parent_agent_id") != self.agent_id or worker["project_slug"] != self.project:
                    raise ValueError("target worker does not belong to this coordinator")
                data = self.orchestrator.enqueue_work(
                    worker_id,
                    title,
                    instruction,
                    priority=int(raw.get("priority") if raw.get("priority") is not None else 50),
                )
                summary = f"Delegated to {worker['name']}: {title}"

            elif operation == "inbox":
                messages = self.orchestrator.inbox(
                    self.agent_id,
                    unread_only=bool(raw.get("unread_only", True)),
                    limit=100,
                )
                data = {"messages": messages}
                summary = "Agent inbox ready"

            elif operation == "message":
                worker_id = str(raw.get("worker_id") or "").strip()
                message = str(raw.get("message") or "").strip()
                if not worker_id or not message:
                    raise ValueError("worker_id and message are required for message")
                target = self.orchestrator.get_agent(worker_id)
                data = self.orchestrator.send_message(
                    self.agent_id,
                    worker_id,
                    message,
                    kind="message",
                )
                summary = f"Message sent to {target['name']}"

            else:
                raise ValueError(f"unsupported agents operation: {operation}")
        except Exception as error:
            return json.dumps(
                {"ok": False, "summary": f"{type(error).__name__}: {error}"},
                ensure_ascii=False,
                separators=(",", ":"),
            )

        return json.dumps(
            {"ok": True, "summary": summary, "data": data},
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        )
