import { useRef, useState, useMemo, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Play,
  Pause,
  RotateCcw,
  Maximize2,
  Settings,
  Eye,
  Code2,
  Activity,
} from "lucide-react";
import type { OrdaxSpec } from "@/lib/ordax/types";
import { OrdaxCanvas, type OrdaxCanvasHandle } from "@/components/ordax/OrdaxCanvas";
import { toast } from "sonner";
import { StellarVanguardStudioRunner } from "@/games/stellar-vanguard/StudioRunner";

type Props = {
  spec?: OrdaxSpec;
  gameId?: string;
};

type EngineMode = "json" | "code";

export function StudioPreviewPanel({ spec, gameId }: Props) {
  const [running, setRunning] = useState(false);
  const [activeTab, setActiveTab] = useState<"preview" | "visual">("preview");
  const [debugInfo, setDebugInfo] = useState<any>(null);
  const [showStartOverlay, setShowStartOverlay] = useState(false);
  const canvasRef = useRef<OrdaxCanvasHandle>(null);

  const [engineMode, setEngineMode] = useState<EngineMode>(() => (gameId === "stellar-vanguard" ? "code" : "json"));

  useEffect(() => {
    // Default to code for Stellar Vanguard, json otherwise.
    setEngineMode(gameId === "stellar-vanguard" ? "code" : "json");
  }, [gameId]);

  const hud = useMemo(
    () => ({ fps: running ? 60 : 0, build: spec ? "Build OK" : "Waiting" }),
    [running, spec]
  );

  // Update debug info periodically
  useEffect(() => {
    if (!running || !canvasRef.current) return;

    const interval = setInterval(() => {
      const info = canvasRef.current?.getDebugInfo();
      if (info) {
        setDebugInfo(info);
      }
    }, 100);

    return () => clearInterval(interval);
  }, [running]);

  // Auto-start when a new spec arrives (no need to press Play)
  useEffect(() => {
    if (!spec || engineMode === "code") {
      setRunning(false);
      setDebugInfo(null);
      setShowStartOverlay(false);
      return;
    }

    setRunning(true);
    setShowStartOverlay(true);
    const id = window.setTimeout(() => setShowStartOverlay(false), 1200);
    return () => window.clearTimeout(id);
  }, [spec]);

  const isGameOver = !!debugInfo?.player && Number(debugInfo.player.health) <= 0;

  useEffect(() => {
    if (isGameOver) {
      setRunning(false);
    }
  }, [isGameOver]);

  const handleReset = () => {
    if (engineMode === "json") {
      setRunning(false);
      canvasRef.current?.reset();
      toast.success("Jogo resetado!");
      return;
    }
    toast.info("Reset do runner Code-first: em desenvolvimento");
  };

  const handleNewGame = () => {
    if (engineMode === "json") {
      canvasRef.current?.reset();
      setRunning(true);
      setShowStartOverlay(false);
      return;
    }
    toast.info("New Game do runner Code-first: em desenvolvimento");
  };

  return (
    <div className="flex h-full flex-col bg-card">
      {/* Header with Tabs */}
      <div className="h-12 border-b border-border/50 flex items-center justify-between px-4 bg-card/60">
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)}>
          <TabsList className="h-8 bg-transparent border border-border/50">
            <TabsTrigger value="preview" className="text-xs gap-2 h-7">
              <Eye className="h-3 w-3" />
              Game Preview
            </TabsTrigger>
            <TabsTrigger value="visual" className="text-xs gap-2 h-7">
              <Code2 className="h-3 w-3" />
              Visual Editor
            </TabsTrigger>
          </TabsList>
        </Tabs>

        <div className="flex items-center gap-2">
          {gameId === "stellar-vanguard" && (
            <Tabs value={engineMode} onValueChange={(v) => setEngineMode(v as EngineMode)}>
              <TabsList className="h-8 bg-transparent border border-border/50">
                <TabsTrigger value="code" className="text-xs h-7">
                  Code
                </TabsTrigger>
                <TabsTrigger value="json" className="text-xs h-7">
                  JSON
                </TabsTrigger>
              </TabsList>
            </Tabs>
          )}
          {spec && (
            <>
              <Badge
                variant="outline"
                className="border-primary/30 bg-primary/10 text-primary text-xs h-6"
              >
                {hud.build}
              </Badge>
              {running && (
                <Badge
                  variant="outline"
                  className="border-neon-green/30 bg-neon-green/10 text-neon-green text-xs h-6 animate-pulse"
                >
                  {hud.fps} FPS
                </Badge>
              )}
            </>
          )}
        </div>
      </div>

      {/* Controls Bar */}
      {spec && engineMode === "json" && (
        <div className="h-10 border-b border-border/50 flex items-center justify-between px-4 bg-card/60">
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs gap-2"
              onClick={() => setRunning((v) => !v)}
            >
              {running ? (
                <>
                  <Pause className="h-3 w-3" />
                  Pause
                </>
              ) : (
                <>
                  <Play className="h-3 w-3" />
                  Play
                </>
              )}
            </Button>

            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs gap-2"
              onClick={handleReset}
            >
              <RotateCcw className="h-3 w-3" />
              Reset
            </Button>

            <div className="h-4 w-px bg-border/50 mx-1"></div>

            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs gap-2"
              onClick={() => toast.info("Fullscreen em desenvolvimento")}
            >
              <Maximize2 className="h-3 w-3" />
              Fullscreen
            </Button>

            <Button 
              variant="ghost" 
              size="sm" 
              className="h-7 text-xs gap-2"
              onClick={() => toast.info("Settings em desenvolvimento")}
            >
              <Settings className="h-3 w-3" />
              Settings
            </Button>
          </div>

          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span>Resolução: 800x600</span>
            <span>•</span>
            <span>60 FPS</span>
            <span>•</span>
            <span>Engine: Ordax 1.0</span>
          </div>
        </div>
      )}

      {/* Preview Area */}
      <div className="relative flex-1 bg-background flex flex-col">
        {!spec && engineMode === "json" ? (
          <div className="flex-1 flex items-center justify-center p-8">
            <div className="text-center space-y-4 max-w-md">
              <div className="w-20 h-20 mx-auto rounded-2xl bg-gradient-to-br from-primary/20 to-secondary/20 flex items-center justify-center border border-border/50">
                <Eye className="h-10 w-10 text-primary/50" />
              </div>
              <div>
                <h3 className="text-xl font-bold neon-text mb-2">
                  Descreva seu jogo no chat
                </h3>
                <p className="text-sm text-muted-foreground">
                  A IA vai responder sua descrição e gerar o jogo automaticamente
                </p>
              </div>
              <div className="pt-4 space-y-2">
                <div className="text-xs text-muted-foreground font-semibold">
                  Exemplos:
                </div>
                <div className="space-y-1 text-xs text-muted-foreground">
                  <div>• "Quero um jogo de nave espacial com asteroides"</div>
                  <div>• "Crie um platformer 2D com moedas"</div>
                  <div>• "Jogo de corrida top-down"</div>
                </div>
              </div>
            </div>
          </div>
        ) : engineMode === "code" ? (
          <div className="flex-1 p-4">
            <div className="w-full h-full rounded-lg overflow-hidden border border-border/50 bg-background">
              {gameId === "stellar-vanguard" ? (
                <StellarVanguardStudioRunner />
              ) : (
                <div className="h-full w-full grid place-items-center p-8 text-center">
                  <div>
                    <div className="text-sm font-medium text-foreground">Code-first preview</div>
                    <div className="mt-1 text-sm text-muted-foreground">
                      Nenhum runner registrado para este gameId.
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : (
          <>
            {/* Canvas */}
            <div className="flex-1 p-4">
              <div className="w-full h-full rounded-lg overflow-hidden border border-border/50 bg-background">
                <OrdaxCanvas ref={canvasRef} spec={spec} running={running} />
              </div>
            </div>

            {/* Game State Overlays */}
            {(showStartOverlay || isGameOver) && (
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div className="pointer-events-auto rounded-xl border border-border/50 bg-background/80 backdrop-blur px-6 py-5 text-center max-w-sm">
                  {isGameOver ? (
                    <>
                      <div className="text-lg font-bold mb-1">Game Over</div>
                      <div className="text-xs text-muted-foreground mb-4">Sua nave foi destruída. Quer começar um novo jogo?</div>
                      <div className="flex items-center justify-center gap-2">
                        <Button size="sm" onClick={handleNewGame}>
                          New Game
                        </Button>
                        <Button size="sm" variant="outline" onClick={handleReset}>
                          Reset
                        </Button>
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="text-lg font-bold mb-1">New Game</div>
                      <div className="text-xs text-muted-foreground">Iniciando automaticamente…</div>
                    </>
                  )}
                </div>
              </div>
            )}

            {/* Debug Panel */}
            {debugInfo && (
              <div className="h-32 border-t border-border/50 bg-card/60">
                <div className="h-8 border-b border-border/50 flex items-center px-3">
                  <Activity className="h-3.5 w-3.5 text-primary mr-2" />
                  <span className="text-xs font-semibold">Debug Info</span>
                </div>
                <ScrollArea className="h-24">
                  <div className="p-3 space-y-2">
                    {/* Systems */}
                    <div className="flex flex-wrap gap-2">
                      {debugInfo.systems.physics && (
                        <Badge variant="outline" className="text-[10px] h-5 border-primary/30 bg-primary/10 text-primary">
                          ✓ Physics
                        </Badge>
                      )}
                      {debugInfo.systems.collision && (
                        <Badge variant="outline" className="text-[10px] h-5 border-accent/30 bg-accent/10 text-accent">
                          ✓ Collision
                        </Badge>
                      )}
                      {debugInfo.systems.particles && (
                        <Badge variant="outline" className="text-[10px] h-5 border-secondary/30 bg-secondary/10 text-secondary">
                          ✓ Particles ({debugInfo.systems.particleCount})
                        </Badge>
                      )}
                      {debugInfo.systems.score && (
                        <Badge variant="outline" className="text-[10px] h-5 border-primary/30 bg-primary/10 text-primary">
                          ✓ Score
                        </Badge>
                      )}
                      {debugInfo.systems.ai && (
                        <Badge variant="outline" className="text-[10px] h-5 border-secondary/30 bg-secondary/10 text-secondary">
                          ✓ AI
                        </Badge>
                      )}
                      {debugInfo.systems.camera && (
                        <Badge variant="outline" className="text-[10px] h-5 border-primary/30 bg-primary/10 text-primary">
                          ✓ Camera
                        </Badge>
                      )}
                      {debugInfo.systems.audio && (
                        <Badge variant="outline" className="text-[10px] h-5 border-accent/30 bg-accent/10 text-accent">
                          ✓ Audio
                        </Badge>
                      )}
                      {debugInfo.systems.animation && (
                        <Badge variant="outline" className="text-[10px] h-5 border-secondary/30 bg-secondary/10 text-secondary">
                          ✓ Animation
                        </Badge>
                      )}
                      {debugInfo.systems.ui && (
                        <Badge variant="outline" className="text-[10px] h-5 border-accent/30 bg-accent/10 text-accent">
                          ✓ UI
                        </Badge>
                      )}
                    </div>

                    {/* Stats */}
                    <div className="grid grid-cols-4 gap-3 text-[10px]">
                      <div className="space-y-0.5">
                        <div className="text-muted-foreground">Entities</div>
                        <div className="text-primary font-mono">{debugInfo.entities.total + debugInfo.entities.spawned}</div>
                      </div>
                      {debugInfo.player && (
                        <>
                          <div className="space-y-0.5">
                            <div className="text-muted-foreground">Health</div>
                            <div className="text-primary font-mono">{debugInfo.player.health}</div>
                          </div>
                          <div className="space-y-0.5">
                            <div className="text-muted-foreground">Position</div>
                            <div className="text-primary font-mono">{debugInfo.player.x},{debugInfo.player.y}</div>
                          </div>
                        </>
                      )}
                      {debugInfo.score && (
                        <div className="space-y-0.5">
                          <div className="text-muted-foreground">Score</div>
                          <div className="text-primary font-mono">
                            {debugInfo.score.current}
                            {debugInfo.score.multiplier > 1 && (
                              <span className="text-secondary ml-1">x{debugInfo.score.multiplier.toFixed(1)}</span>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </ScrollArea>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
