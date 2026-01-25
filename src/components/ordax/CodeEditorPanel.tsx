import { useState, useEffect } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { X, Save, RotateCcw } from "lucide-react";
import { toast } from "sonner";
import { vfs } from "@/lib/vfs/VirtualFileSystem";
import type { VirtualFile } from "@/lib/vfs/types";

type OpenFile = {
  id: string;
  name: string;
  path: string;
  content: string;
  language: string;
  modified: boolean;
  originalContent: string;
};

type Props = {
  openFileId: string | null;
  onClose: () => void;
};

export function CodeEditorPanel({ openFileId, onClose }: Props) {
  const [openFiles, setOpenFiles] = useState<OpenFile[]>([]);
  const [activeFileId, setActiveFileId] = useState<string | null>(null);

  // Open file when openFileId changes
  useEffect(() => {
    if (openFileId) {
      openFile(openFileId);
    }
  }, [openFileId]);

  const openFile = (fileId: string) => {
    // Check if already open
    const existing = openFiles.find((f) => f.id === fileId);
    if (existing) {
      setActiveFileId(fileId);
      return;
    }

    // Load from VFS
    const vfsNode = vfs.getNodeById(fileId);
    if (!vfsNode || vfsNode.type !== "file") {
      toast.error("Arquivo não encontrado");
      return;
    }

    const file: OpenFile = {
      id: vfsNode.id,
      name: vfsNode.name,
      path: vfsNode.path,
      content: vfsNode.content,
      language: vfsNode.language,
      modified: false,
      originalContent: vfsNode.content,
    };

    setOpenFiles((prev) => [...prev, file]);
    setActiveFileId(fileId);
  };

  const closeFile = (fileId: string) => {
    const file = openFiles.find((f) => f.id === fileId);
    if (file?.modified) {
      if (!confirm(`${file.name} tem alterações não salvas. Deseja fechar mesmo assim?`)) {
        return;
      }
    }

    setOpenFiles((prev) => prev.filter((f) => f.id !== fileId));
    
    if (activeFileId === fileId) {
      const remaining = openFiles.filter((f) => f.id !== fileId);
      setActiveFileId(remaining.length > 0 ? remaining[0].id : null);
    }

    if (openFiles.length === 1) {
      onClose();
    }
  };

  const updateContent = (fileId: string, newContent: string) => {
    setOpenFiles((prev) =>
      prev.map((f) =>
        f.id === fileId
          ? { ...f, content: newContent, modified: newContent !== f.originalContent }
          : f
      )
    );
  };

  const saveFile = (fileId: string) => {
    const file = openFiles.find((f) => f.id === fileId);
    if (!file) return;

    const success = vfs.updateFileContent(fileId, file.content);
    if (success) {
      setOpenFiles((prev) =>
        prev.map((f) =>
          f.id === fileId
            ? { ...f, modified: false, originalContent: f.content }
            : f
        )
      );
      toast.success(`${file.name} salvo!`);
    } else {
      toast.error("Erro ao salvar arquivo");
    }
  };

  const revertFile = (fileId: string) => {
    const file = openFiles.find((f) => f.id === fileId);
    if (!file) return;

    setOpenFiles((prev) =>
      prev.map((f) =>
        f.id === fileId
          ? { ...f, content: f.originalContent, modified: false }
          : f
      )
    );
    toast.info("Alterações revertidas");
  };

  const activeFile = openFiles.find((f) => f.id === activeFileId);

  if (openFiles.length === 0) {
    return null;
  }

  return (
    <div className="h-full flex flex-col bg-card">
      {/* Tabs */}
      <div className="border-b border-border/50 bg-card/60">
        <div className="flex items-center overflow-x-auto">
          {openFiles.map((file) => (
            <div
              key={file.id}
              className={`
                flex items-center gap-2 px-3 py-2 border-r border-border/50 cursor-pointer
                hover:bg-surface-2 transition-colors min-w-[120px] max-w-[200px]
                ${activeFileId === file.id ? "bg-card" : ""}
              `}
              onClick={() => setActiveFileId(file.id)}
            >
              <span className="text-xs truncate flex-1">
                {file.name}
                {file.modified && <span className="text-primary ml-1">●</span>}
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  closeFile(file.id);
                }}
                className="hover:bg-surface-3 rounded p-0.5"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Editor */}
      {activeFile && (
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Toolbar */}
            <div className="h-10 border-b border-border/50 flex items-center justify-between px-3 bg-card/60">
            <div className="text-xs text-muted-foreground">
              {activeFile.path}
            </div>
            <div className="flex items-center gap-2">
              {activeFile.modified && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={() => revertFile(activeFile.id)}
                >
                  <RotateCcw className="h-3 w-3 mr-1" />
                  Reverter
                </Button>
              )}
              <Button
                variant="default"
                size="sm"
                className="h-7 text-xs"
                onClick={() => saveFile(activeFile.id)}
                disabled={!activeFile.modified}
              >
                <Save className="h-3 w-3 mr-1" />
                Salvar
              </Button>
            </div>
          </div>

          {/* Code Area */}
          <ScrollArea className="flex-1">
            <textarea
              value={activeFile.content}
              onChange={(e) => updateContent(activeFile.id, e.target.value)}
                className="w-full h-full min-h-[500px] p-4 bg-background text-sm font-mono resize-none focus:outline-none"
              spellCheck={false}
              style={{
                tabSize: 2,
                lineHeight: "1.6",
              }}
            />
          </ScrollArea>

          {/* Status Bar */}
            <div className="h-8 border-t border-border/50 flex items-center justify-between px-3 bg-card/60 text-[10px] text-muted-foreground">
            <div className="flex items-center gap-4">
              <span>Linguagem: {activeFile.language}</span>
              <span>Linhas: {activeFile.content.split("\n").length}</span>
              <span>Caracteres: {activeFile.content.length}</span>
            </div>
            {activeFile.modified && (
              <span className="text-primary">● Não salvo</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
