from __future__ import annotations

import argparse
import json
import os
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Any

from ordax_dev_agent.actions import ActionRegistry
from ordax_dev_agent.config import AgentConfig

APP_NAME = "ORDAX Studio"


def create_registry() -> ActionRegistry:
    return ActionRegistry(AgentConfig.from_env())


def snapshot(agent: ActionRegistry) -> dict[str, Any]:
    store = agent._memory_store_instance()
    return {
        "product": APP_NAME,
        "default_project": agent.config.default_project,
        "active_project": store.active_project(),
        "projects": [project.public() for project in agent.projects.values()],
        "memory": store.status(),
        "action_count": len(agent.names),
    }


class StudioApp(tk.Tk):
    def __init__(self, agent: ActionRegistry | None = None):
        super().__init__()
        self.agent = agent or create_registry()
        self.store = self.agent._memory_store_instance()
        self.current_project: str | None = None
        self.current_session_id: int | None = None
        self.title(APP_NAME)
        self.geometry("1280x800")
        self.minsize(1040, 680)
        self.configure(bg="#080F19")
        self._configure_style()
        self._build_ui()
        self.refresh_projects()

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#080F19")
        style.configure("TLabel", background="#080F19", foreground="#E2EBF7")
        style.configure("TButton", padding=7)
        style.configure("Treeview", background="#111E30", fieldbackground="#111E30", foreground="#E2EBF7", rowheight=27)
        style.configure("Treeview.Heading", background="#172B47", foreground="#E2EBF7")
        style.configure("TNotebook", background="#080F19", borderwidth=0)
        style.configure("TNotebook.Tab", padding=(12, 8), background="#111E30", foreground="#E2EBF7")
        style.map("TNotebook.Tab", background=[("selected", "#243249")])

    def _build_ui(self) -> None:
        top = tk.Frame(self, bg="#080F19")
        top.pack(fill="x", padx=18, pady=(14, 8))
        tk.Label(top, text=APP_NAME, bg="#080F19", fg="#E2EBF7", font=("Segoe UI Semibold", 19)).pack(side="left")
        self.status_label = tk.Label(top, text="", bg="#080F19", fg="#A9C9F7", font=("Segoe UI", 9))
        self.status_label.pack(side="right")

        body = tk.PanedWindow(self, orient="horizontal", bg="#243249", sashwidth=4, bd=0)
        body.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        sidebar = tk.Frame(body, bg="#0C1625", width=270)
        body.add(sidebar, minsize=230)
        main = tk.Frame(body, bg="#080F19")
        body.add(main, minsize=720)

        tk.Label(sidebar, text="PROJETOS", bg="#0C1625", fg="#8E9DB4", font=("Segoe UI Semibold", 9)).pack(anchor="w", padx=14, pady=(16, 8))
        self.project_list = tk.Listbox(sidebar, bg="#111E30", fg="#E2EBF7", selectbackground="#243249", borderwidth=0, highlightthickness=0, font=("Segoe UI", 10))
        self.project_list.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.project_list.bind("<<ListboxSelect>>", self._project_selected)

        buttons = tk.Frame(sidebar, bg="#0C1625")
        buttons.pack(fill="x", padx=10, pady=(0, 12))
        ttk.Button(buttons, text="Retomar sessão", command=self.resume_session).pack(fill="x", pady=3)
        ttk.Button(buttons, text="Checkpoint", command=self.save_checkpoint).pack(fill="x", pady=3)
        ttk.Button(buttons, text="Abrir pasta", command=self.open_project).pack(fill="x", pady=3)
        ttk.Button(buttons, text="Atualizar", command=self.refresh_all).pack(fill="x", pady=3)

        self.tabs = ttk.Notebook(main)
        self.tabs.pack(fill="both", expand=True)
        self.workspace_tab = ttk.Frame(self.tabs)
        self.context_tab = ttk.Frame(self.tabs)
        self.memory_tab = ttk.Frame(self.tabs)
        self.tasks_tab = ttk.Frame(self.tabs)
        self.capabilities_tab = ttk.Frame(self.tabs)
        self.terminal_tab = ttk.Frame(self.tabs)
        for frame, title in ((self.workspace_tab, "Workspace"), (self.context_tab, "Contexto"),
                             (self.memory_tab, "Memória"), (self.tasks_tab, "Tarefas"),
                             (self.capabilities_tab, "Capabilities"), (self.terminal_tab, "Terminal")):
            self.tabs.add(frame, text=title)
        self._build_workspace_tab()
        self._build_context_tab()
        self._build_memory_tab()
        self._build_tasks_tab()
        self._build_capabilities_tab()
        self._build_terminal_tab()

    def _text_box(self, parent: tk.Widget, *, console: bool = False) -> tk.Text:
        box = tk.Text(parent, bg="#050A10" if console else "#111E30", fg="#E2EBF7",
                      insertbackground="#E2EBF7", relief="flat", wrap="word",
                      font=("Consolas", 10), padx=12, pady=12)
        box.pack(fill="both", expand=True)
        return box

    def _build_workspace_tab(self) -> None:
        wrap = tk.PanedWindow(self.workspace_tab, orient="horizontal", bg="#243249", sashwidth=4, bd=0)
        wrap.pack(fill="both", expand=True, padx=12, pady=12)
        left = tk.Frame(wrap, bg="#0C1625")
        right = tk.Frame(wrap, bg="#080F19")
        wrap.add(left, minsize=320)
        wrap.add(right, minsize=500)

        bar = tk.Frame(left, bg="#0C1625")
        bar.pack(fill="x", padx=8, pady=8)
        tk.Label(bar, text="ARQUIVOS", bg="#0C1625", fg="#8E9DB4", font=("Segoe UI Semibold", 9)).pack(side="left")
        ttk.Button(bar, text="Atualizar", command=self.refresh_workspace).pack(side="right")
        self.workspace_tree = ttk.Treeview(left, columns=("kind", "path", "size"), show="headings")
        self.workspace_tree.heading("kind", text="Tipo")
        self.workspace_tree.heading("path", text="Caminho")
        self.workspace_tree.heading("size", text="Tamanho")
        self.workspace_tree.column("kind", width=70, stretch=False)
        self.workspace_tree.column("path", width=330)
        self.workspace_tree.column("size", width=90, stretch=False)
        self.workspace_tree.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.workspace_tree.bind("<Double-1>", self.open_workspace_file)

        editor_bar = tk.Frame(right, bg="#080F19")
        editor_bar.pack(fill="x", padx=8, pady=8)
        self.workspace_file_label = tk.Label(editor_bar, text="Nenhum arquivo aberto", bg="#080F19", fg="#E2EBF7", font=("Segoe UI", 10))
        self.workspace_file_label.pack(side="left")
        ttk.Button(editor_bar, text="Salvar", command=self.save_workspace_file).pack(side="right")
        self.workspace_editor = self._text_box(right)
        self.workspace_path: str | None = None
        self.workspace_sha256: str | None = None

    def _build_context_tab(self) -> None:
        wrap = tk.Frame(self.context_tab, bg="#080F19")
        wrap.pack(fill="both", expand=True, padx=18, pady=18)
        self.project_title = tk.Label(wrap, text="Nenhum projeto", bg="#080F19", fg="#E2EBF7", font=("Segoe UI Semibold", 17))
        self.project_title.pack(anchor="w")

        self.project_path = tk.Label(wrap, text="", bg="#080F19", fg="#8E9DB4", font=("Segoe UI", 10))
        self.project_path.pack(anchor="w", pady=(4, 12))
        self.context_box = self._text_box(wrap)

    def _build_memory_tab(self) -> None:
        wrap = tk.Frame(self.memory_tab, bg="#080F19")
        wrap.pack(fill="both", expand=True, padx=18, pady=18)
        bar = tk.Frame(wrap, bg="#080F19")
        bar.pack(fill="x", pady=(0, 10))
        ttk.Button(bar, text="+ Memória", command=self.add_memory).pack(side="right")
        self.memory_tree = ttk.Treeview(wrap, columns=("kind", "content", "date"), show="headings")
        for key, title in (("kind", "Tipo"), ("content", "Conteúdo"), ("date", "Data")):
            self.memory_tree.heading(key, text=title)
        self.memory_tree.column("kind", width=100, stretch=False)
        self.memory_tree.column("content", width=600)
        self.memory_tree.column("date", width=180, stretch=False)
        self.memory_tree.pack(fill="both", expand=True)

    def _build_tasks_tab(self) -> None:
        wrap = tk.Frame(self.tasks_tab, bg="#080F19")
        wrap.pack(fill="both", expand=True, padx=18, pady=18)
        bar = tk.Frame(wrap, bg="#080F19")
        bar.pack(fill="x", pady=(0, 10))
        ttk.Button(bar, text="+ Tarefa", command=self.add_task).pack(side="right")
        self.task_tree = ttk.Treeview(wrap, columns=("state", "title", "date"), show="headings")
        for key, title in (("state", "Estado"), ("title", "Tarefa"), ("date", "Data")):
            self.task_tree.heading(key, text=title)

        self.task_tree.column("state", width=100, stretch=False)
        self.task_tree.column("title", width=600)
        self.task_tree.column("date", width=180, stretch=False)
        self.task_tree.pack(fill="both", expand=True)
        self.task_tree.bind("<Double-1>", self.toggle_task)

    def _build_capabilities_tab(self) -> None:
        wrap = tk.Frame(self.capabilities_tab, bg="#080F19")
        wrap.pack(fill="both", expand=True, padx=18, pady=18)
        bar = tk.Frame(wrap, bg="#080F19")
        bar.pack(fill="x", pady=(0, 10))
        for label, action in (("Git status", self.show_git_status),
                              ("Blender status", self.show_blender_status),
                              ("Abrir Blender", self.start_blender),
                              ("Unity status", self.show_unity_status),
                              ("Abrir Unity", self.start_unity)):
            ttk.Button(bar, text=label, command=action).pack(side="left", padx=(0, 6))
        self.capabilities_box = self._text_box(wrap)

    def _build_terminal_tab(self) -> None:
        wrap = tk.Frame(self.terminal_tab, bg="#080F19")
        wrap.pack(fill="both", expand=True, padx=18, pady=18)
        row = tk.Frame(wrap, bg="#080F19")
        row.pack(fill="x", pady=(0, 8))
        self.command_entry = tk.Entry(row, bg="#111E30", fg="#E2EBF7", insertbackground="#E2EBF7", relief="flat", font=("Consolas", 10))
        self.command_entry.pack(side="left", fill="x", expand=True, ipady=8)
        self.command_entry.bind("<Return>", lambda _: self.run_command())
        ttk.Button(row, text="Executar", command=self.run_command).pack(side="left", padx=(8, 0))
        self.terminal_output = self._text_box(wrap, console=True)

    def refresh_projects(self) -> None:
        self.project_slugs = list(self.agent.projects)
        self.project_list.delete(0, "end")
        active = self.store.active_project()
        active_name = str(active.get("name") or "") if active else ""

        selected_index = None
        for index, slug in enumerate(self.project_slugs):
            project = self.agent.projects[slug]
            marker = "●" if slug == active_name else " "
            availability = "" if project.root.is_dir() else " [indisponível]"
            self.project_list.insert("end", f"{marker} {slug}{availability}")
            if slug == active_name:
                selected_index = index
        if selected_index is None and self.agent.config.default_project in self.project_slugs:
            selected_index = self.project_slugs.index(self.agent.config.default_project)
        if selected_index is None:
            selected_index = next(
                (index for index, slug in enumerate(self.project_slugs) if self.agent.projects[slug].root.is_dir()),
                0 if self.project_slugs else None,
            )
        if selected_index is not None:
            self.project_list.selection_set(selected_index)
            self.project_list.activate(selected_index)
            self.current_project = self.project_slugs[selected_index]
        self.refresh_all()
        self.refresh_workspace()

    def _project_selected(self, _event=None) -> None:
        selection = self.project_list.curselection()
        if not selection:
            return
        self.current_project = self.project_slugs[selection[0]]
        project = self.agent.projects[self.current_project]
        self.store.set_active_project(project.slug, project.root)
        self.refresh_all()
        self.refresh_workspace()

    def refresh_all(self) -> None:
        slug = self.current_project
        if not slug or slug not in self.agent.projects:
            return
        project = self.agent.projects[slug]
        data = self.store.context(project.slug, project.root)
        self.project_title.config(text=project.slug)
        self.project_path.config(text=str(project.root))
        self.status_label.config(text=f"{len(self.agent.names)} ações • memória persistente • {', '.join(project.apps) or 'workspace'}")

        self.context_box.delete("1.0", "end")
        self.context_box.insert("1.0", self.store.context_text(project.slug, project.root))
        for item in self.memory_tree.get_children():
            self.memory_tree.delete(item)
        for row in data["memories"]:
            self.memory_tree.insert("", "end", iid=f"m{row['id']}", values=(row["kind"], row["content"], row["created_at"]))
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)
        for row in data["tasks"]:
            self.task_tree.insert("", "end", iid=str(row["id"]), values=("Concluída" if row["done"] else "Pendente", row["title"], row["created_at"]))
        capability_data = {
            "project": project.public(),
            "action_groups": sorted({name.split(".", 1)[0] for name in self.agent.names}),
            "action_count": len(self.agent.names),
            "current_session_id": self.current_session_id,
        }
        self.capabilities_box.delete("1.0", "end")
        self.capabilities_box.insert("1.0", json.dumps(capability_data, ensure_ascii=False, indent=2, default=str))

    def refresh_workspace(self) -> None:
        for item in self.workspace_tree.get_children():
            self.workspace_tree.delete(item)
        self.workspace_path = None
        self.workspace_sha256 = None
        self.workspace_file_label.config(text="Nenhum arquivo aberto")
        self.workspace_editor.delete("1.0", "end")
        if not self.current_project:
            return
        result = self.agent.execute("project.inventory", {
            "project": self.current_project,
            "max_depth": 4,
            "max_entries": 600,
        })
        if not result.ok:
            self.workspace_editor.insert("1.0", result.summary)
            return
        for index, entry in enumerate(result.data.get("entries", [])):
            size = entry.get("size_bytes")
            size_text = "" if size is None else (f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / 1024 / 1024:.1f} MB")
            self.workspace_tree.insert("", "end", iid=f"e{index}", values=(entry.get("kind", ""), entry.get("path", ""), size_text))

    def open_workspace_file(self, _event=None) -> None:
        selection = self.workspace_tree.selection()
        if not selection or not self.current_project:
            return
        values = self.workspace_tree.item(selection[0], "values")
        if not values or values[0] != "file":
            return
        path = str(values[1])
        result = self.agent.execute("project.text_read", {"project": self.current_project, "path": path})
        if not result.ok:
            messagebox.showerror(APP_NAME, result.summary)
            return
        self.workspace_path = path
        self.workspace_sha256 = str(result.data.get("sha256") or "")
        self.workspace_file_label.config(text=path)
        self.workspace_editor.delete("1.0", "end")
        self.workspace_editor.insert("1.0", result.data.get("content", ""))

    def save_workspace_file(self) -> None:
        if not self.current_project or not self.workspace_path or not self.workspace_sha256:
            return
        content = self.workspace_editor.get("1.0", "end-1c")
        result = self.agent.execute("project.text_write", {
            "project": self.current_project,
            "path": self.workspace_path,
            "content": content,
            "expected_sha256": self.workspace_sha256,
        })
        if not result.ok:
            messagebox.showerror(APP_NAME, result.summary)
            return
        self.workspace_sha256 = str(result.data.get("sha256") or "")
        messagebox.showinfo(APP_NAME, f"Arquivo salvo: {self.workspace_path}")

    def resume_session(self) -> None:
        if not self.current_project:
            return
        result = self.agent.execute("session.resume", {"project": self.current_project})
        if result.ok:
            self.current_session_id = int(result.data["session_id"])
            self.refresh_all()
            messagebox.showinfo(APP_NAME, result.summary)
        else:
            messagebox.showerror(APP_NAME, result.summary)

    def save_checkpoint(self) -> None:
        if not self.current_project:
            return
        summary = simpledialog.askstring("Checkpoint", "Resumo do estado atual e próximo passo:", parent=self)
        if summary is None:
            return
        result = self.agent.execute("memory.checkpoint", {"project": self.current_project, "summary": summary})
        self.refresh_all()
        (messagebox.showinfo if result.ok else messagebox.showerror)(APP_NAME, result.summary)

    def add_memory(self) -> None:
        if not self.current_project:
            return
        content = simpledialog.askstring("Memória", "O que deve permanecer entre sessões?", parent=self)
        if content:
            self.agent.execute("memory.remember", {"project": self.current_project, "content": content})
            self.refresh_all()

    def add_task(self) -> None:
        if not self.current_project:
            return
        title = simpledialog.askstring("Tarefa", "Descreva a tarefa:", parent=self)
        if title:
            self.agent.execute("memory.task_add", {"project": self.current_project, "title": title})
            self.refresh_all()

    def toggle_task(self, _event=None) -> None:
        selection = self.task_tree.selection()
        if not selection or not self.current_project:
            return
        self.agent.execute("memory.task_toggle", {"project": self.current_project, "task_id": int(selection[0])})
        self.refresh_all()

    def open_project(self) -> None:
        if not self.current_project:
            return
        root = self.agent.projects[self.current_project].root
        if root.is_dir():
            os.startfile(root)

    def _run_capability(self, action: str, *, required_app: str | None = None) -> None:
        if not self.current_project:
            return
        project_slug = self.current_project
        project = self.agent.projects[project_slug]
        if required_app and required_app not in project.apps:
            messagebox.showinfo(APP_NAME, f"{required_app.title()} não está configurado para {project.slug}.")
            return
        self.capabilities_box.delete("1.0", "end")
        self.capabilities_box.insert("1.0", f"Executando {action}...\n")

        def worker() -> None:
            try:
                result = self.agent.execute(action, {"project": project_slug})
                payload = {"action": action, "ok": result.ok, "summary": result.summary, "data": result.data}
            except Exception as error:
                payload = {"action": action, "ok": False, "error": f"{type(error).__name__}: {error}"}
            text = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
            self.after(0, lambda: self._show_capability_result(text))
        threading.Thread(target=worker, daemon=True).start()

    def _show_capability_result(self, text: str) -> None:
        self.capabilities_box.delete("1.0", "end")
        self.capabilities_box.insert("1.0", text)

    def show_git_status(self) -> None:
        self._run_capability("git.status")

    def show_blender_status(self) -> None:
        self._run_capability("blender.live_status", required_app="blender")

    def start_blender(self) -> None:
        self._run_capability("blender.live_start", required_app="blender")

    def show_unity_status(self) -> None:
        self._run_capability("unity.editor_status", required_app="unity")

    def start_unity(self) -> None:
        self._run_capability("unity.editor_start", required_app="unity")

    def run_command(self) -> None:
        command = self.command_entry.get().strip()
        if not command or not self.current_project:
            return
        root = self.agent.projects[self.current_project].root
        self.command_entry.delete(0, "end")
        self.terminal_output.insert("end", f"\n> {command}\n")
        self.terminal_output.see("end")

        def worker() -> None:
            try:
                completed = subprocess.run(command, cwd=root, shell=True, capture_output=True,
                                           text=True, errors="replace", timeout=600)
                output = (completed.stdout or "") + (completed.stderr or "") + f"\n[exit {completed.returncode}]\n"
            except Exception as error:
                output = f"ERRO: {type(error).__name__}: {error}\n"
            self.after(0, lambda: self._append_terminal(output))
        threading.Thread(target=worker, daemon=True).start()

    def _append_terminal(self, output: str) -> None:
        self.terminal_output.insert("end", output)
        self.terminal_output.see("end")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ordax-studio-desktop")
    parser.add_argument("--smoke", action="store_true", help="validate runtime without opening the GUI")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    agent = create_registry()
    if args.smoke:
        print(json.dumps(snapshot(agent), ensure_ascii=False, indent=2, default=str))
        return 0
    app = StudioApp(agent)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
