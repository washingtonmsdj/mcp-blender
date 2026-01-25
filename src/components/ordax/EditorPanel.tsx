import { useMemo, useState } from "react";
import { FileJson2, Layers, Package, Search } from "lucide-react";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import type { OrdaxSpec } from "@/lib/ordax/types";

type Props = {
  spec?: OrdaxSpec;
  rawJson?: string;
};

const ORDAX_MODULES = [
  "InputSystem",
  "PhysicsSystem",
  "CollisionSystem",
  "ParticleSystem",
  "AnimationSystem",
  "AudioSystem",
  "CameraSystem",
  "AISystem",
  "SpawnerSystem",
  "ScoreSystem",
  "UISystem",
  "TimerSystem",
  "DialogueSystem",
  "InventorySystem",
  "SaveSystem",
];

export function EditorPanel({ spec, rawJson }: Props) {
  const [query, setQuery] = useState("");

  const files = useMemo(
    () =>
      [
        { name: "ordax.json", kind: "config" },
        { name: "scene.main.json", kind: "scene" },
        { name: "systems.json", kind: "config" },
      ].filter((f) => f.name.toLowerCase().includes(query.toLowerCase())),
    [query],
  );

  const filteredModules = useMemo(
    () => ORDAX_MODULES.filter((m) => m.toLowerCase().includes(query.toLowerCase())),
    [query],
  );

  const pretty = useMemo(() => {
    if (!rawJson) return "{\n  // Gere um jogo pelo chat para ver o JSON aqui\n}";
    try {
      return JSON.stringify(JSON.parse(rawJson), null, 2);
    } catch {
      return rawJson;
    }
  }, [rawJson]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between gap-2 border-b border-border/50 glass-panel px-4 py-3">
        <div className="text-sm font-bold tracking-wide">EDITOR</div>
        <Badge variant="outline" className="border-primary/30 bg-primary/10 text-primary font-mono text-xs">
          {spec?.gameType ?? "—"}
        </Badge>
      </div>

      <div className="border-b border-border/50 bg-surface-2 px-4 py-3">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input value={query} onChange={(e) => setQuery(e.target.value)} className="pl-9 glass-panel border-border/50 font-mono text-sm" placeholder="Search files/modules..." />
        </div>
      </div>

      <Tabs defaultValue="code" className="flex flex-1 flex-col">
        <TabsList className="h-11 justify-start gap-1 rounded-none border-b border-border/50 bg-surface-1 px-3">
          <TabsTrigger value="code" className="gap-2 font-mono text-xs">
            <FileJson2 className="h-4 w-4" /> JSON
          </TabsTrigger>
          <TabsTrigger value="assets" className="gap-2 font-mono text-xs">
            <Package className="h-4 w-4" /> Assets
          </TabsTrigger>
          <TabsTrigger value="modules" className="gap-2 font-mono text-xs">
            <Layers className="h-4 w-4" /> Modules
          </TabsTrigger>
        </TabsList>

        <TabsContent value="code" className="m-0 flex-1">
          <div className="grid h-full grid-rows-[auto_1fr]">
            <div className="px-4 py-2 text-xs text-muted-foreground font-mono border-b border-border/50 bg-surface-2">ordax.json</div>
            <ScrollArea className="px-4 pb-4">
              <pre className="overflow-x-auto rounded-lg glass-panel border border-border/50 p-4 text-xs leading-relaxed text-foreground mt-4">
                <code className="font-mono">{pretty}</code>
              </pre>
            </ScrollArea>
          </div>
        </TabsContent>

        <TabsContent value="assets" className="m-0 flex-1">
          <ScrollArea className="h-full px-4 py-4">
            <div className="glass-panel p-4 rounded-lg border border-border/50 text-sm text-muted-foreground">
              (MVP) Assets ainda não configurados — a IA descreve entidades via props.
            </div>
            <Separator className="my-4 bg-border/50" />
            <div className="space-y-2">
              {files.map((f) => (
                <div key={f.name} className="flex items-center justify-between rounded-lg glass-panel border border-border/50 px-4 py-3 hover:border-primary/30 transition-colors">
                  <div className="font-mono text-sm">{f.name}</div>
                  <Badge variant="secondary" className="border border-border/60 bg-surface-2 font-mono text-xs">
                    {f.kind}
                  </Badge>
                </div>
              ))}
            </div>
          </ScrollArea>
        </TabsContent>

        <TabsContent value="modules" className="m-0 flex-1">
          <ScrollArea className="h-full px-4 py-4">
            <div className="grid gap-2">
              {filteredModules.map((m) => {
                const enabled = spec?.systems?.includes(m);
                return (
                  <div key={m} className="flex items-center justify-between rounded-lg glass-panel border border-border/50 px-4 py-3 hover:border-primary/30 transition-colors">
                    <div className="font-mono text-sm">{m}</div>
                    <Badge
                      variant={enabled ? "default" : "secondary"}
                      className={enabled ? "bg-primary/20 text-primary border border-primary/40 neon-glow font-mono text-xs" : "border border-border/60 bg-surface-2 font-mono text-xs"}
                    >
                      {enabled ? "Active" : "Available"}
                    </Badge>
                  </div>
                );
              })}
            </div>
          </ScrollArea>
        </TabsContent>
      </Tabs>
    </div>
  );
}
