import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { 
  Folder, 
  FileCode, 
  Image, 
  Music, 
  Plus,
  ChevronRight 
} from "lucide-react";
import { useState } from "react";

export const ProjectSidebar = () => {
  const [expanded, setExpanded] = useState<string[]>(["files"]);

  const toggleFolder = (id: string) => {
    setExpanded(prev => 
      prev.includes(id) 
        ? prev.filter(item => item !== id)
        : [...prev, id]
    );
  };

  return (
    <aside className="w-64 border-r border-border/50 glass-panel">
      <div className="h-full flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-border/50">
          <Button className="w-full neon-glow" size="sm">
            <Plus className="h-4 w-4 mr-2" />
            Novo Projeto
          </Button>
        </div>

        {/* File Tree */}
        <ScrollArea className="flex-1">
          <div className="p-2 space-y-1">
            {/* Files Folder */}
            <div>
              <Button
                variant="ghost"
                size="sm"
                className="w-full justify-start font-mono text-xs"
                onClick={() => toggleFolder("files")}
              >
                <ChevronRight 
                  className={`h-4 w-4 mr-2 transition-transform ${
                    expanded.includes("files") ? "rotate-90" : ""
                  }`}
                />
                <Folder className="h-4 w-4 mr-2 text-primary" />
                Arquivos
              </Button>
              
              {expanded.includes("files") && (
                <div className="ml-6 space-y-1">
                  <Button variant="ghost" size="sm" className="w-full justify-start font-mono text-xs">
                    <FileCode className="h-4 w-4 mr-2 text-neon-cyan" />
                    main.ts
                  </Button>
                  <Button variant="ghost" size="sm" className="w-full justify-start font-mono text-xs">
                    <FileCode className="h-4 w-4 mr-2 text-neon-cyan" />
                    game.ts
                  </Button>
                  <Button variant="ghost" size="sm" className="w-full justify-start font-mono text-xs">
                    <FileCode className="h-4 w-4 mr-2 text-neon-cyan" />
                    player.ts
                  </Button>
                </div>
              )}
            </div>

            <Separator className="my-2 bg-border/50" />

            {/* Assets Folder */}
            <div>
              <Button
                variant="ghost"
                size="sm"
                className="w-full justify-start font-mono text-xs"
                onClick={() => toggleFolder("assets")}
              >
                <ChevronRight 
                  className={`h-4 w-4 mr-2 transition-transform ${
                    expanded.includes("assets") ? "rotate-90" : ""
                  }`}
                />
                <Folder className="h-4 w-4 mr-2 text-primary" />
                Assets
              </Button>
              
              {expanded.includes("assets") && (
                <div className="ml-6 space-y-1">
                  <Button variant="ghost" size="sm" className="w-full justify-start font-mono text-xs">
                    <Image className="h-4 w-4 mr-2 text-neon-magenta" />
                    Sprites
                  </Button>
                  <Button variant="ghost" size="sm" className="w-full justify-start font-mono text-xs">
                    <Music className="h-4 w-4 mr-2 text-neon-green" />
                    Áudio
                  </Button>
                </div>
              )}
            </div>
          </div>
        </ScrollArea>
      </div>
    </aside>
  );
};
