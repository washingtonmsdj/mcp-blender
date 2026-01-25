import { useRef, type RefObject } from "react";

import type { OrdaxSpec } from "@/lib/ordax/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Pause, Play, RotateCcw } from "lucide-react";
import { useMemo, useState } from "react";
import { OrdaxCanvas, type OrdaxCanvasHandle } from "@/components/ordax/OrdaxCanvas";

type Props = {
  spec?: OrdaxSpec;
};

export function PreviewPanel({ spec }: Props) {
  const [running, setRunning] = useState(false);
  const canvasRef = useRef<OrdaxCanvasHandle>(null);

  const entities = spec?.scene.entities ?? [];
  const gravity = spec?.scene.gravity;

  const hud = useMemo(
    () => ({ fps: running ? 60 : 0, build: spec ? "Build OK" : "Waiting" }),
    [running, spec],
  );

  const handleReset = () => {
    setRunning(false);
    canvasRef.current?.reset();
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between gap-2 border-b border-border/50 glass-panel px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="text-sm font-bold tracking-wide">GAME PREVIEW</div>
          <Badge variant="outline" className="border-primary/30 bg-primary/10 text-primary font-mono text-xs">
            {hud.build}
          </Badge>
          {running && (
            <Badge variant="outline" className="border-neon-green/30 bg-neon-green/10 text-neon-green font-mono text-xs animate-pulse">
              {hud.fps} FPS
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" className="glass-panel border-border/50 hover:border-primary/30 transition-colors font-mono text-xs" onClick={() => setRunning((v) => !v)}>
            {running ? <Pause className="mr-2 h-4 w-4" /> : <Play className="mr-2 h-4 w-4" />}
            {running ? "Pause" : "Play"}
          </Button>
          <Button variant="outline" className="glass-panel border-border/50 hover:border-primary/30 transition-colors font-mono text-xs" onClick={handleReset}>
            <RotateCcw className="mr-2 h-4 w-4" />
            Reset
          </Button>
        </div>
      </div>

      <div className="relative flex-1 bg-surface-1">
        {!spec ? (
          <div className="absolute inset-0 grid place-items-center p-6">
            <div className="w-full max-w-3xl rounded-xl glass-panel border border-border/50 p-6 neon-glow">
              <div className="text-xs uppercase tracking-wider text-primary font-mono">Ordax Runtime (2D)</div>
              <div className="mt-2 text-3xl font-bold neon-text">Aguardando spec</div>
              <div className="mt-3 text-sm text-muted-foreground">Peça um jogo no chat à esquerda para gerar e renderizar a cena aqui.</div>
              <Separator className="my-5 bg-border/50" />
              <div className="grid gap-4 md:grid-cols-3">
                <div className="rounded-lg glass-panel border border-border/50 p-4">
                  <div className="text-xs text-muted-foreground font-mono">gameType</div>
                  <div className="mt-2 font-mono text-sm text-primary">—</div>
                </div>
                <div className="rounded-lg glass-panel border border-border/50 p-4">
                  <div className="text-xs text-muted-foreground font-mono">gravity</div>
                  <div className="mt-2 font-mono text-sm text-primary">—</div>
                </div>
                <div className="rounded-lg glass-panel border border-border/50 p-4">
                  <div className="text-xs text-muted-foreground font-mono">entities</div>
                  <div className="mt-2 font-mono text-sm text-primary">—</div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="absolute inset-0">
            <OrdaxCanvas ref={canvasRef} spec={spec} running={running} />
          </div>
        )}
      </div>
    </div>
  );
}
