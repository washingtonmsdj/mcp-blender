import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Monitor,
  Zap,
  HardDrive,
  Wifi,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";

export function StudioBottomBar() {
  return (
    <div className="h-7 border-t border-border/50 bg-card/60 flex items-center justify-between px-4 text-[10px]">
      {/* Left Section */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5">
          <Monitor className="h-3 w-3 text-muted-foreground" />
          <span className="text-muted-foreground">Resolução:</span>
          <span className="text-primary font-mono">800x600</span>
        </div>

        <div className="h-3 w-px bg-border/50"></div>

        <div className="flex items-center gap-1.5">
          <Zap className="h-3 w-3 text-neon-green" />
          <span className="text-muted-foreground">FPS:</span>
          <span className="text-neon-green font-mono">60</span>
        </div>

        <div className="h-3 w-px bg-border/50"></div>

        <div className="flex items-center gap-1.5">
          <HardDrive className="h-3 w-3 text-muted-foreground" />
          <span className="text-muted-foreground">Engine:</span>
          <span className="text-foreground font-mono">Ordax 1.0</span>
        </div>

        <div className="h-3 w-px bg-border/50"></div>

        <div className="flex items-center gap-1.5">
          <span className="text-muted-foreground">Build:</span>
          <span className="text-foreground font-mono">Release 2.4.1</span>
        </div>
      </div>

      {/* Right Section */}
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="sm"
          className="h-5 px-2 text-[10px] gap-1.5"
        >
          <CheckCircle2 className="h-3 w-3 text-neon-green" />
          <span className="text-neon-green">0 Erros</span>
        </Button>

        <div className="h-3 w-px bg-border/50"></div>

        <Button
          variant="ghost"
          size="sm"
          className="h-5 px-2 text-[10px] gap-1.5"
        >
          <AlertCircle className="h-3 w-3 text-muted-foreground" />
          <span className="text-muted-foreground">0 Avisos</span>
        </Button>

        <div className="h-3 w-px bg-border/50"></div>

        <div className="flex items-center gap-1.5">
          <Wifi className="h-3 w-3 text-neon-green" />
          <Badge
            variant="outline"
            className="h-4 border-neon-green/30 bg-neon-green/10 text-neon-green text-[9px] px-1.5"
          >
            Online
          </Badge>
        </div>
      </div>
    </div>
  );
}
