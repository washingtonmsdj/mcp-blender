import { useState, useEffect, useMemo, useRef } from "react";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
import type { OrdaxSpec } from "@/lib/ordax/types";
import { StudioTopBar } from "./StudioTopBar";
import { StudioSidebar } from "./StudioSidebar";
import { StudioChatPanel } from "./StudioChatPanel";
import { StudioPreviewPanel } from "./StudioPreviewPanel";
import { StudioFileTree } from "./StudioFileTree";
import { CodeEditorPanel } from "./CodeEditorPanel";
import { StudioBottomBar } from "./StudioBottomBar";
import { useProject } from "@/hooks/use-project";
import { vfs } from "@/lib/vfs/VirtualFileSystem";
import { toast } from "sonner";
import { useLocation } from "react-router-dom";
import { getGameById } from "@/games";

import stellarVanguardCodeGameSource from "@/games/stellar-vanguard/codeGame.ts?raw";

export function StudioWorkspace() {
  const location = useLocation();
  const [spec, setSpec] = useState<OrdaxSpec | undefined>(undefined);
  const [rawJson, setRawJson] = useState<string | undefined>(undefined);
  const [openFileId, setOpenFileId] = useState<string | null>(null);
  const [showEditor, setShowEditor] = useState(false);
  const { project, save, exportProject, updateSpec } = useProject();

  const requestedGameId = useMemo(() => {
    const params = new URLSearchParams(location.search);
    return params.get("game");
  }, [location.search]);

  const [leftOpen, setLeftOpen] = useState(false);
  const [rightOpen, setRightOpen] = useState(false);

  const topBarRef = useRef<HTMLDivElement | null>(null);
  const leftRef = useRef<HTMLDivElement | null>(null);
  const rightRef = useRef<HTMLDivElement | null>(null);

  // Auto-save every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      if (spec) {
        save();
      }
    }, 30000);

    return () => clearInterval(interval);
  }, [spec, save]);

  // Handle spec updates
  const handleSpecUpdate = (newSpec: OrdaxSpec, raw: string) => {
    setSpec(newSpec);
    setRawJson(raw);
    updateSpec(newSpec);
    
    // Update VFS with generated code
    vfs.updateFileContent(
      vfs.getNodeByPath("/config/ordax.json")?.id || "",
      raw
    );
  };

  // Load a predefined game into the Studio (via /workspace?game=...)
  useEffect(() => {
    if (!requestedGameId) return;
    // Don't override an active spec.
    if (spec) return;

    const def = getGameById(requestedGameId);
    if (!def) {
      toast.error("Game não encontrado");
      return;
    }

    try {
      const nextSpec = def.buildSpec();
      const raw = JSON.stringify(nextSpec, null, 2);
      setSpec(nextSpec);
      setRawJson(raw);
      updateSpec(nextSpec);

      // Persist into VFS for visibility/editing
      if (!vfs.getNodeByPath("/games")) vfs.createFolder("games", "/");
      const safeName = `${def.id}.ordax.json`;
      const existing = vfs.getNodeByPath(`/games/${safeName}`);
      if (existing?.type === "file") {
        vfs.updateFileContent(existing.id, raw);
      } else {
        vfs.createFile(safeName, "/games", "json", raw);
      }

      const config = vfs.getNodeByPath("/config/ordax.json");
      if (config?.type === "file") {
        vfs.updateFileContent(config.id, raw);
      }

      toast.success(`Carregado: ${def.title}`);
    } catch (e) {
      console.error(e);
      toast.error("Falha ao carregar game no Studio");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestedGameId]);

  // Seed code-first VFS workspace (hybrid model): mirror repo code into /vfs/games/<gameId>/.
  useEffect(() => {
    if (!requestedGameId) return;
    const gameId = requestedGameId;
    if (gameId !== "stellar-vanguard") return;

    // Ensure folder structure
    if (!vfs.getNodeByPath("/vfs")) vfs.createFolder("vfs", "/");
    if (!vfs.getNodeByPath("/vfs/games")) {
      if (!vfs.getNodeByPath("/vfs")) vfs.createFolder("vfs", "/");
      vfs.createFolder("games", "/vfs");
    }
    if (!vfs.getNodeByPath(`/vfs/games/${gameId}`)) {
      vfs.createFolder(gameId, "/vfs/games");
    }

    const entryPath = `/vfs/games/${gameId}/codeGame.ts`;
    const existing = vfs.getNodeByPath(entryPath);
    if (existing?.type === "file") return;
    vfs.createFile("codeGame.ts", `/vfs/games/${gameId}`, "typescript", stellarVanguardCodeGameSource);
  }, [requestedGameId]);

  // Handle export
  const handleExport = () => {
    if (!spec) {
      toast.error("Nenhum jogo para exportar");
      return;
    }
    exportProject();
  };

  // Handle file open
  const handleFileOpen = (fileId: string) => {
    setOpenFileId(fileId);
    setShowEditor(true);
  };

  // Handle editor close
  const handleEditorClose = () => {
    setShowEditor(false);
    setOpenFileId(null);
  };

  // Click-outside to collapse side panels
  useEffect(() => {
    if (!leftOpen && !rightOpen) return;

    const onDown = (e: MouseEvent) => {
      const t = e.target as Node | null;
      if (!t) return;
      // Ignore clicks inside sidebars or top bar (toggles live there)
      if (topBarRef.current?.contains(t)) return;
      if (leftRef.current?.contains(t)) return;
      if (rightRef.current?.contains(t)) return;
      setLeftOpen(false);
      setRightOpen(false);
    };

    window.addEventListener("mousedown", onDown);
    return () => window.removeEventListener("mousedown", onDown);
  }, [leftOpen, rightOpen]);

  return (
    <div className="h-screen w-screen flex flex-col bg-background overflow-hidden">
      {/* Top Bar */}
      <StudioTopBar
        ref={topBarRef}
        onExport={handleExport}
        onSave={save}
        onToggleLeft={() => {
          setLeftOpen((v) => !v);
          // keep behavior “Lovable-like”: opening one collapses the other
          setRightOpen(false);
        }}
        onToggleRight={() => {
          setRightOpen((v) => !v);
          setLeftOpen(false);
        }}
      />

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar */}
        <div ref={leftRef} className="h-full">
          <StudioSidebar collapsed={!leftOpen} />
        </div>

        {/* Center Content (Chat + Preview/Editor + File Tree) */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 flex overflow-hidden">
            <ResizablePanelGroup direction="horizontal" className="flex-1">
              {/* Chat Panel */}
              <ResizablePanel defaultSize={30} minSize={22} maxSize={40}>
                <StudioChatPanel gameId={requestedGameId ?? undefined} currentSpec={spec} onSpec={handleSpecUpdate} />
              </ResizablePanel>

              <ResizableHandle className="w-px bg-border/50 hover:bg-primary/30 transition-colors" />

              {/* Preview or Editor Panel */}
              <ResizablePanel defaultSize={70} minSize={40}>
                {showEditor ? (
                  <CodeEditorPanel openFileId={openFileId} onClose={handleEditorClose} />
                ) : (
                  <StudioPreviewPanel spec={spec} gameId={requestedGameId ?? undefined} />
                )}
              </ResizablePanel>
            </ResizablePanelGroup>

            {/* Right panel (File Tree) */}
            <div ref={rightRef} className="h-full">
              <StudioFileTree onFileOpen={handleFileOpen} collapsed={!rightOpen} />
            </div>
          </div>

          {/* Bottom Bar */}
          <StudioBottomBar />
        </div>
      </div>
    </div>
  );
}
