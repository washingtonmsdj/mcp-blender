import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  LayoutDashboard,
  FolderOpen,
  Star,
  Clock,
  Key,
  Plus,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { Link } from "react-router-dom";

const recentProjects = [
  { name: "Meu Jogo de Plat...", type: "Platformer", date: "Hoje" },
  { name: "Space Shooter", type: "Shooter", date: "Ontem" },
  { name: "RPG Moderno", type: "RPG", date: "2 dias" },
  { name: "Racing Game 3D", type: "Racing", date: "1 sem" },
];

export function StudioSidebar({ collapsed }: { collapsed?: boolean }) {
  const isCollapsed = !!collapsed;
  return (
    <div
      className={cn(
        "border-r border-border/50 bg-card flex flex-col transition-[width] duration-200 ease-linear",
        isCollapsed ? "w-14" : "w-64",
      )}
    >
      {/* New Project Button */}
      <div className="p-3 border-b border-border/50">
        <Button 
          className={cn("w-full justify-start gap-2 neon-glow", isCollapsed && "justify-center px-0")}
          size="sm"
          onClick={() => toast.success("Novo projeto criado!")}
        >
          <Plus className="h-4 w-4" />
          {!isCollapsed && "Novo Projeto"}
        </Button>
      </div>

      {/* Navigation */}
      <div className="p-3 space-y-1">
        <Link to="/">
          <Button
            variant="ghost"
            className={cn("w-full justify-start gap-2 text-xs h-8", isCollapsed && "justify-center px-0")}
          >
            <LayoutDashboard className="h-4 w-4" />
            {!isCollapsed && "Dashboard"}
          </Button>
        </Link>

        <Link to="/">
          <Button
            variant="ghost"
            className={cn(
              "w-full justify-start gap-2 text-xs h-8 bg-primary/10 text-primary",
              isCollapsed && "justify-center px-0",
            )}
          >
            <FolderOpen className="h-4 w-4" />
            {!isCollapsed && (
              <>
                Meus Projetos
                <Badge variant="secondary" className="ml-auto text-xs">
                  12
                </Badge>
              </>
            )}
          </Button>
        </Link>

        <Button
          variant="ghost"
          className={cn("w-full justify-start gap-2 text-xs h-8", isCollapsed && "justify-center px-0")}
          onClick={() => toast.info("Favoritos: 3 projetos")}
        >
          <Star className="h-4 w-4" />
          {!isCollapsed && (
            <>
              Favoritos
              <Badge variant="secondary" className="ml-auto text-xs">
                3
              </Badge>
            </>
          )}
        </Button>

        <Button
          variant="ghost"
          className={cn("w-full justify-start gap-2 text-xs h-8", isCollapsed && "justify-center px-0")}
          onClick={() => toast.info("Mostrando projetos recentes")}
        >
          <Clock className="h-4 w-4" />
          {!isCollapsed && "Recentes"}
        </Button>

        <Button
          variant="ghost"
          className={cn("w-full justify-start gap-2 text-xs h-8", isCollapsed && "justify-center px-0")}
          onClick={() => toast.info("Licença: Ordax Pro")}
        >
          <Key className="h-4 w-4" />
          {!isCollapsed && "Licença"}
        </Button>
      </div>

      <Separator className="bg-border/50" />

      {/* Recent Projects */}
      {!isCollapsed && (
      <div className="flex-1 overflow-hidden">
        <div className="p-3">
          <div className="text-xs font-semibold text-muted-foreground mb-2 flex items-center justify-between">
            RECENTE
            <ChevronRight className="h-3 w-3" />
          </div>
        </div>

        <ScrollArea className="h-[calc(100%-2rem)]">
          <div className="px-3 space-y-1">
            {recentProjects.map((project, idx) => (
              <button
                key={idx}
                onClick={() => toast.success(`Abrindo: ${project.name}`)}
                className={cn(
                  "w-full text-left p-2 rounded-lg hover:bg-surface-2 transition-colors group",
                  idx === 0 && "bg-surface-2"
                )}
              >
                <div className="flex items-start gap-2">
                  <div className="w-8 h-8 rounded bg-primary/20 flex items-center justify-center shrink-0 group-hover:neon-glow transition-all">
                    <FolderOpen className="h-4 w-4 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-medium truncate">
                      {project.name}
                    </div>
                    <div className="text-[10px] text-muted-foreground">
                      {project.type}
                    </div>
                  </div>
                </div>
                <div className="text-[10px] text-muted-foreground mt-1 ml-10">
                  {project.date}
                </div>
              </button>
            ))}
          </div>
        </ScrollArea>
      </div>
      )}

      {/* Bottom Stats */}
      <div className={cn("border-t border-border/50 bg-card/60", isCollapsed ? "p-2" : "p-3")}>
        <div className="text-[10px] text-muted-foreground space-y-1">
          {!isCollapsed && (
            <div className="flex justify-between">
              <span>Uso de Disco:</span>
              <span className="text-primary">2.4GB / 10GB</span>
            </div>
          )}
          <div className="h-1 bg-surface-2 rounded-full overflow-hidden">
            <div className="h-full w-[24%] bg-primary rounded-full"></div>
          </div>
        </div>
      </div>
    </div>
  );
}
