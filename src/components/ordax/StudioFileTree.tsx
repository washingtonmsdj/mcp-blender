import { useState, useEffect } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  ChevronRight,
  ChevronDown,
  Folder,
  FolderOpen,
  FileJson,
  FileCode,
  FileImage,
  FileAudio,
  Search,
  Plus,
  MoreHorizontal,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { vfs } from "@/lib/vfs/VirtualFileSystem";

type TreeNode = {
  id: string;
  name: string;
  type: "file" | "folder";
  path: string;
  language?: string;
  children?: TreeNode[];
  expanded?: boolean;
};

export function StudioFileTree({
  onFileOpen,
  collapsed,
}: {
  onFileOpen?: (fileId: string) => void;
  collapsed?: boolean;
}) {
  const [tree, setTree] = useState<TreeNode | null>(null);
  const [search, setSearch] = useState("");
  const isCollapsed = !!collapsed;

  // Load tree from VFS
  useEffect(() => {
    loadTree();

    // Listen to VFS changes
    const unsubscribe = vfs.on(() => {
      loadTree();
    });

    return unsubscribe;
  }, []);

  const loadTree = () => {
    const vfsTree = vfs.getTree();
    if (vfsTree) {
      setTree(convertTree(vfsTree));
    }
  };

  const convertTree = (node: any): TreeNode => {
    if (node.type === "file") {
      return {
        id: node.id,
        name: node.name,
        type: "file",
        path: node.path,
        language: node.language,
      };
    }

    return {
      id: node.id,
      name: node.name,
      type: "folder",
      path: node.path,
      expanded: true,
      children: node.children?.map(convertTree) || [],
    };
  };

  const handleToggle = (nodeId: string) => {
    const toggleNode = (node: TreeNode): TreeNode => {
      if (node.id === nodeId) {
        return { ...node, expanded: !node.expanded };
      }
      if (node.children) {
        return {
          ...node,
          children: node.children.map(toggleNode),
        };
      }
      return node;
    };

    if (tree) {
      setTree(toggleNode(tree));
    }
  };

  const handleFileClick = (node: TreeNode) => {
    if (node.type === "file") {
      const vfsNode = vfs.getNodeById(node.id);
      if (vfsNode && vfsNode.type === "file") {
        toast.success(`Abrindo: ${node.name}`);
        onFileOpen?.(node.id);
      }
    }
  };

  const handleCreateFile = () => {
    const result = vfs.createFile("newfile.ts", "/src", "typescript", "// New file\n");
    if (result) {
      toast.success("Arquivo criado!");
    } else {
      toast.error("Erro ao criar arquivo");
    }
  };

  if (!tree) return null;

  return (
    <div
      className={cn(
        "border-l border-border/50 bg-card flex flex-col transition-[width] duration-200 ease-linear",
        isCollapsed ? "w-14" : "w-64",
      )}
    >
      {/* Header */}
      <div className="h-12 border-b border-border/50 flex items-center justify-between px-3 bg-card/60">
        {!isCollapsed && <span className="font-semibold text-sm">Estrutura</span>}
        <div className={cn("flex items-center gap-1", isCollapsed && "w-full justify-center")}>
          <Button 
            variant="ghost" 
            size="icon" 
            className="h-7 w-7"
            onClick={handleCreateFile}
          >
            <Plus className="h-3.5 w-3.5" />
          </Button>
          {!isCollapsed && (
            <Button 
              variant="ghost" 
              size="icon" 
              className="h-7 w-7"
              onClick={() => toast.info("Menu em desenvolvimento")}
            >
              <MoreHorizontal className="h-3.5 w-3.5" />
            </Button>
          )}
        </div>
      </div>

      {/* Search */}
      {!isCollapsed && (
        <div className="p-3 border-b border-border/50">
          <div className="relative">
            <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar arquivos..."
              className="h-8 pl-8 text-xs"
            />
          </div>
        </div>
      )}

      {/* File Tree */}
      <ScrollArea className="flex-1">
        <div className={cn("p-2", isCollapsed && "px-1")}>
          {tree.children?.map((node) => (
            <TreeNodeComponent
              key={node.id}
              node={node}
              onToggle={handleToggle}
              onClick={handleFileClick}
              compact={isCollapsed}
            />
          ))}
        </div>
      </ScrollArea>

      {/* Bottom Info */}
      <div className={cn("border-t border-border/50 bg-card/60", isCollapsed ? "p-2" : "p-3")}>
        <div className="text-[10px] text-muted-foreground space-y-1">
          {!isCollapsed && (
            <div className="flex justify-between">
              <span>Arquivos:</span>
              <span className="text-primary">{vfs.getAllFiles().length}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function TreeNodeComponent({
  node,
  level = 0,
  onToggle,
  onClick,
  compact,
}: {
  node: TreeNode;
  level?: number;
  onToggle: (id: string) => void;
  onClick: (node: TreeNode) => void;
  compact?: boolean;
}) {
  const getIcon = () => {
    if (node.type === "folder") {
      return node.expanded ? FolderOpen : Folder;
    }
    if (node.language === "typescript") return FileCode;
    if (node.language === "json") return FileJson;
    return FileCode;
  };

  const Icon = getIcon();

  return (
    <div>
      <button
        onClick={() => {
          if (node.type === "folder") {
            onToggle(node.id);
          } else {
            onClick(node);
          }
        }}
        className={cn(
          "w-full flex items-center gap-2 px-2 py-1 hover:bg-surface-2 rounded text-xs transition-colors",
          level === 0 && "font-medium"
        )}
        style={{ paddingLeft: compact ? 8 : `${level * 12 + 8}px` }}
      >
        {node.type === "folder" && (
          <span className="text-muted-foreground">
            {node.expanded ? (
              <ChevronDown className="h-3 w-3" />
            ) : (
              <ChevronRight className="h-3 w-3" />
            )}
          </span>
        )}
        {node.type === "file" && !compact && <span className="w-3" />}
        <Icon className="h-3.5 w-3.5 text-primary shrink-0" />
        {!compact && <span className="flex-1 text-left truncate">{node.name}</span>}
      </button>

      {node.type === "folder" && !compact && node.expanded && node.children && (
        <div>
          {node.children.map((child) => (
            <TreeNodeComponent
              key={child.id}
              node={child}
              level={level + 1}
              onToggle={onToggle}
              onClick={onClick}
              compact={compact}
            />
          ))}
        </div>
      )}
    </div>
  );
}
