import { ReactNode, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  LayoutDashboard,
  FolderOpen,
  Star,
  Clock,
  FileText,
  Plus,
  Upload,
  Settings,
  User,
  ChevronRight,
  Folder,
  FileCode,
  Image,
  Music,
  Box,
  Palette,
  Zap,
  Code,
} from "lucide-react";

interface GameForgeLayoutProps {
  children: ReactNode;
  leftSidebar?: ReactNode;
  rightSidebar?: ReactNode;
  showTopBar?: boolean;
  showBottomBar?: boolean;
}

export const GameForgeLayout = ({
  children,
  leftSidebar,
  rightSidebar,
  showTopBar = true,
  showBottomBar = true,
}: GameForgeLayoutProps) => {
  const navigate = useNavigate();
  const [activeNav, setActiveNav] = useState("dashboard");
  const [expandedFolders, setExpandedFolders] = useState<string[]>(["src", "assets"]);

  const toggleFolder = (id: string) => {
    setExpandedFolders((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const recentProjects = [
    { name: "Meu Jogo de Plat...", type: "Platformer" },
    { name: "Space Shooter", type: "Shooter" },
    { name: "RPG Moderno", type: "RPG" },
    { name: "Racing Game 3D", type: "Racing" },
  ];

  return (
    <div className="h-screen flex flex-col bg-[#0a0a0a] text-foreground">
      {/* Top Bar */}
      {showTopBar && (
        <header className="h-12 bg-[#0f0f0f] border-b border-border/30 flex items-center px-4 gap-4">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-7 h-7 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-lg flex items-center justify-center">
              <Zap className="h-4 w-4 text-white" />
            </div>
            <span className="font-bold text-sm">GameForge AI</span>
          </Link>

          <Separator orientation="vertical" className="h-6 bg-border/30" />

          <nav className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              className="h-8 text-xs bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/20"
            >
              Setup
            </Button>
            <Button variant="ghost" size="sm" className="h-8 text-xs hover:bg-white/5">
              Templates
            </Button>
            <Button variant="ghost" size="sm" className="h-8 text-xs hover:bg-white/5">
              Assets
            </Button>
          </nav>

          <div className="flex-1" />

          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              className="h-8 text-xs hover:bg-white/5"
              onClick={() => navigate("/workspace")}
            >
              <Plus className="h-3 w-3 mr-1" />
              Novo Projeto
            </Button>
            <Button variant="ghost" size="sm" className="h-8 text-xs hover:bg-white/5">
              <FolderOpen className="h-3 w-3 mr-1" />
              Meus Projetos
            </Button>
            <Button variant="ghost" size="sm" className="h-8 text-xs hover:bg-white/5">
              <Upload className="h-3 w-3 mr-1" />
              Exportar
            </Button>

            <Separator orientation="vertical" className="h-6 bg-border/30 mx-2" />

            <Button variant="ghost" size="icon" className="h-8 w-8 hover:bg-white/5">
              <Settings className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" className="h-8 w-8 hover:bg-white/5">
              <User className="h-4 w-4" />
            </Button>
            <Badge variant="outline" className="h-6 text-xs border-cyan-500/30 text-cyan-400">
              Local
            </Badge>
          </div>
        </header>
      )}

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar - Navigation */}
        {leftSidebar || (
          <aside className="w-56 bg-[#0f0f0f] border-r border-border/30 flex flex-col">
            <div className="p-3">
              <Button className="w-full bg-cyan-500 hover:bg-cyan-600 text-white h-9 text-sm">
                <Plus className="h-4 w-4 mr-2" />
                Novo Projeto
              </Button>
            </div>

            <ScrollArea className="flex-1">
              <nav className="p-2 space-y-1">
                <Button
                  variant="ghost"
                  size="sm"
                  className={`w-full justify-start h-9 text-sm ${
                    activeNav === "dashboard" ? "bg-white/10" : "hover:bg-white/5"
                  }`}
                  onClick={() => setActiveNav("dashboard")}
                >
                  <LayoutDashboard className="h-4 w-4 mr-3" />
                  Dashboard
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className={`w-full justify-start h-9 text-sm ${
                    activeNav === "projects" ? "bg-white/10" : "hover:bg-white/5"
                  }`}
                  onClick={() => setActiveNav("projects")}
                >
                  <FolderOpen className="h-4 w-4 mr-3" />
                  Meus Projetos
                  <Badge variant="secondary" className="ml-auto h-5 text-xs">
                    12
                  </Badge>
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className={`w-full justify-start h-9 text-sm ${
                    activeNav === "favorites" ? "bg-white/10" : "hover:bg-white/5"
                  }`}
                  onClick={() => setActiveNav("favorites")}
                >
                  <Star className="h-4 w-4 mr-3" />
                  Favoritos
                  <Badge variant="secondary" className="ml-auto h-5 text-xs">
                    3
                  </Badge>
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className={`w-full justify-start h-9 text-sm ${
                    activeNav === "recent" ? "bg-white/10" : "hover:bg-white/5"
                  }`}
                  onClick={() => setActiveNav("recent")}
                >
                  <Clock className="h-4 w-4 mr-3" />
                  Recentes
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className={`w-full justify-start h-9 text-sm ${
                    activeNav === "license" ? "bg-white/10" : "hover:bg-white/5"
                  }`}
                  onClick={() => setActiveNav("license")}
                >
                  <FileText className="h-4 w-4 mr-3" />
                  Licença
                </Button>
              </nav>

              <Separator className="my-3 bg-border/30" />

              <div className="px-2">
                <div className="text-xs text-muted-foreground font-semibold mb-2 px-2">
                  RECENTE
                </div>
                <div className="space-y-1">
                  {recentProjects.map((project, idx) => (
                    <Button
                      key={idx}
                      variant="ghost"
                      size="sm"
                      className="w-full justify-start h-8 text-xs hover:bg-white/5"
                    >
                      <div className="w-6 h-6 bg-purple-500/20 rounded flex items-center justify-center mr-2 flex-shrink-0">
                        <Box className="h-3 w-3 text-purple-400" />
                      </div>
                      <div className="flex-1 text-left truncate">{project.name}</div>
                    </Button>
                  ))}
                </div>
              </div>
            </ScrollArea>

            <div className="p-3 border-t border-border/30">
              <div className="text-xs text-muted-foreground">
                <div className="font-mono">Uso do Jogo</div>
                <div className="mt-1 h-1.5 bg-white/10 rounded-full overflow-hidden">
                  <div className="h-full w-1/3 bg-cyan-500 rounded-full" />
                </div>
                <div className="mt-1 font-mono">33%</div>
              </div>
            </div>
          </aside>
        )}

        {/* Center Content */}
        <main className="flex-1 flex flex-col overflow-hidden">{children}</main>

        {/* Right Sidebar - File Tree */}
        {rightSidebar || (
          <aside className="w-64 bg-[#0f0f0f] border-l border-border/30 flex flex-col">
            <div className="h-12 border-b border-border/30 flex items-center justify-between px-3">
              <span className="text-sm font-semibold">Arquivos</span>
              <Button variant="ghost" size="icon" className="h-7 w-7 hover:bg-white/5">
                <Plus className="h-3 w-3" />
              </Button>
            </div>

            <ScrollArea className="flex-1">
              <div className="p-2 space-y-0.5">
                {/* src folder */}
                <div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-full justify-start h-7 text-xs hover:bg-white/5 px-2"
                    onClick={() => toggleFolder("src")}
                  >
                    <ChevronRight
                      className={`h-3 w-3 mr-1 transition-transform ${
                        expandedFolders.includes("src") ? "rotate-90" : ""
                      }`}
                    />
                    <Folder className="h-3 w-3 mr-2 text-blue-400" />
                    src
                  </Button>
                  {expandedFolders.includes("src") && (
                    <div className="ml-4 space-y-0.5">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="w-full justify-start h-7 text-xs hover:bg-white/5 px-2"
                      >
                        <FileCode className="h-3 w-3 mr-2 text-cyan-400" />
                        main.ts
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="w-full justify-start h-7 text-xs hover:bg-white/5 px-2"
                      >
                        <FileCode className="h-3 w-3 mr-2 text-cyan-400" />
                        game.ts
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="w-full justify-start h-7 text-xs hover:bg-white/5 px-2"
                      >
                        <FileCode className="h-3 w-3 mr-2 text-cyan-400" />
                        player.ts
                      </Button>
                    </div>
                  )}
                </div>

                {/* assets folder */}
                <div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-full justify-start h-7 text-xs hover:bg-white/5 px-2"
                    onClick={() => toggleFolder("assets")}
                  >
                    <ChevronRight
                      className={`h-3 w-3 mr-1 transition-transform ${
                        expandedFolders.includes("assets") ? "rotate-90" : ""
                      }`}
                    />
                    <Folder className="h-3 w-3 mr-2 text-blue-400" />
                    assets
                  </Button>
                  {expandedFolders.includes("assets") && (
                    <div className="ml-4 space-y-0.5">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="w-full justify-start h-7 text-xs hover:bg-white/5 px-2"
                        onClick={() => toggleFolder("sprites")}
                      >
                        <ChevronRight
                          className={`h-3 w-3 mr-1 transition-transform ${
                            expandedFolders.includes("sprites") ? "rotate-90" : ""
                          }`}
                        />
                        <Folder className="h-3 w-3 mr-2 text-purple-400" />
                        sprites
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="w-full justify-start h-7 text-xs hover:bg-white/5 px-2"
                        onClick={() => toggleFolder("audio")}
                      >
                        <ChevronRight
                          className={`h-3 w-3 mr-1 transition-transform ${
                            expandedFolders.includes("audio") ? "rotate-90" : ""
                          }`}
                        />
                        <Folder className="h-3 w-3 mr-2 text-green-400" />
                        audio
                      </Button>
                    </div>
                  )}
                </div>

                {/* Other folders */}
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full justify-start h-7 text-xs hover:bg-white/5 px-2"
                >
                  <ChevronRight className="h-3 w-3 mr-1" />
                  <Folder className="h-3 w-3 mr-2 text-blue-400" />
                  scripts
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full justify-start h-7 text-xs hover:bg-white/5 px-2"
                >
                  <ChevronRight className="h-3 w-3 mr-1" />
                  <Folder className="h-3 w-3 mr-2 text-blue-400" />
                  config
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full justify-start h-7 text-xs hover:bg-white/5 px-2"
                >
                  <FileCode className="h-3 w-3 mr-2 text-cyan-400" />
                  package.json
                </Button>
              </div>
            </ScrollArea>
          </aside>
        )}
      </div>

      {/* Bottom Bar */}
      {showBottomBar && (
        <footer className="h-7 bg-[#0f0f0f] border-t border-border/30 flex items-center px-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-4">
            <span className="font-mono">Resolução: 1920x1080</span>
            <Separator orientation="vertical" className="h-4 bg-border/30" />
            <span className="font-mono">60 FPS</span>
            <Separator orientation="vertical" className="h-4 bg-border/30" />
            <span className="font-mono">Engine: Ordax v2.0</span>
            <Separator orientation="vertical" className="h-4 bg-border/30" />
            <span className="font-mono">Build: Release 1.0</span>
          </div>
        </footer>
      )}
    </div>
  );
};
