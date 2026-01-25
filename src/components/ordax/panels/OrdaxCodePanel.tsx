import { useMemo, useState } from "react";
import OrdaxCodeView from "@/components/ordax/ui/OrdaxCodeView";

type FileNode = {
  path: string;
  kind: "file" | "folder";
  children?: FileNode[];
  language?: "ts" | "json" | "md";
  content?: string;
};

const engineModules = [
  { name: "InputSystem", status: "✅ Completo", detail: "Teclado, Mouse, Touch" },
  { name: "PhysicsSystem", status: "✅ Completo", detail: "Gravidade, Velocidade, Força, Fricção" },
  { name: "CollisionSystem", status: "✅ Completo", detail: "AABB, Círculo, Layers, Triggers" },
  { name: "ParticleSystem", status: "✅ Completo", detail: "Emissores, Explosões, Efeitos" },
  { name: "AnimationSystem", status: "✅ Completo", detail: "Sprites, Tweens, Keyframes" },
  { name: "AudioSystem", status: "✅ Completo", detail: "Sons, Música, Volume" },
  { name: "CameraSystem", status: "✅ Completo", detail: "Follow, Shake, Zoom, Bounds" },
  { name: "AISystem", status: "✅ Completo", detail: "Patrulha, Seguir, Fugir, Wander" },
  { name: "SpawnerSystem", status: "✅ Completo", detail: "Spawn, Waves, Object Pools" },
  { name: "ScoreSystem", status: "✅ Completo", detail: "Pontuação, Highscore" },
  { name: "UISystem", status: "✅ Completo", detail: "HUD, Barras, Textos" },
  { name: "TimerSystem", status: "✅ Completo", detail: "Contadores, Delays" },
  { name: "DialogueSystem", status: "✅ Completo", detail: "Conversas, Escolhas" },
  { name: "InventorySystem", status: "✅ Completo", detail: "Itens, Equipamentos" },
  { name: "SaveSystem", status: "✅ Completo", detail: "Salvar, Carregar" },
];

const projectTree: FileNode[] = [
  {
    path: "ordax/",
    kind: "folder",
    children: [
      {
        path: "game.config.json",
        kind: "file",
        language: "json",
        content: `{
  "engine": "Ordax",
  "project": "Neon Platformer",
  "gameType": "platformer_2d",
  "runners": ["PlatformerGameRunner"],
  "render": { "mode": "2D", "future3D": "Babylon" }
}`,
      },
      {
        path: "GameRunner.ts",
        kind: "file",
        language: "ts",
        content: `// Ordax GameRunner (mock)
export type GameType = "platformer_2d" | "racing" | "sports" | "puzzle";

export type OrdaxBuild = {
  gameType: GameType;
  systems: string[];
  scenes: string[];
};

export class PlatformerGameRunner {
  build(): OrdaxBuild {
    return {
      gameType: "platformer_2d",
      systems: ["InputSystem", "PhysicsSystem", "CollisionSystem", "CameraSystem", "UISystem"],
      scenes: ["MainScene"],
    };
  }
}
` ,
      },
      {
        path: "README.md",
        kind: "file",
        language: "md",
        content: `# Ordax — AI Game Studio (UI)

Este projeto é um **mock de interface** inspirado em Unity Editor + VS Code + Rosebud/Lovable.

## Próximos passos
- Conectar Cloud + IA para gerar JSON estruturado e GameRunners reais.
- Implementar suporte 3D com Babylon no preview.
` ,
      },
    ],
  },
  {
    path: "assets/",
    kind: "folder",
    children: [
      { path: "sprites/", kind: "folder", children: [] },
      { path: "audio/", kind: "folder", children: [] },
      { path: "prefabs/", kind: "folder", children: [] },
    ],
  },
];

function flatten(nodes: FileNode[], base = ""): { key: string; node: FileNode }[] {
  const out: { key: string; node: FileNode }[] = [];
  for (const n of nodes) {
    const key = base + n.path;
    out.push({ key, node: n });
    if (n.kind === "folder" && n.children?.length) {
      out.push(...flatten(n.children, key));
    }
  }
  return out;
}

export default function OrdaxCodePanel({
  collapsed,
  onToggleCollapse,
}: {
  collapsed: boolean;
  onToggleCollapse: () => void;
}) {
  const all = useMemo(() => flatten(projectTree), []);
  const defaultFile = all.find((x) => x.node.kind === "file" && x.node.path.endsWith("GameRunner.ts"))?.key;
  const [active, setActive] = useState<string | undefined>(defaultFile);
  const [tab, setTab] = useState<"Editor" | "Módulos">("Editor");

  const activeNode = useMemo(() => {
    const found = all.find((x) => x.key === active);
    return found?.node;
  }, [active, all]);

  if (collapsed) {
    return (
      <aside className="h-full border-l border-border/60 bg-surface-1/60">
        <button
          className="h-full w-full ordax-grid ordax-grid-anim text-left"
          onClick={onToggleCollapse}
          aria-label="Expandir Editor"
        >
          <div className="flex h-full items-center justify-center">
            <div className="text-xs font-medium tracking-wide text-muted-foreground [writing-mode:vertical-rl]">EDITOR</div>
          </div>
        </button>
      </aside>
    );
  }

  return (
    <aside className="h-full border-l border-border/60 bg-surface-1/60">
      <div className="flex h-full flex-col">
        <div className="flex items-center justify-between border-b border-border/60 px-3 py-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold tracking-wide">Ordax</span>
            <span className="text-[11px] text-muted-foreground">Editor & Assets</span>
          </div>
          <button
            onClick={onToggleCollapse}
            className="rounded-md border border-border/60 bg-surface-2/60 px-2 py-1 text-xs text-muted-foreground hover:text-foreground"
            aria-label="Colapsar Editor"
          >
            Collapse
          </button>
        </div>

        <div className="border-b border-border/60 p-2">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setTab("Editor")}
              className={
                tab === "Editor"
                  ? "rounded-md border border-primary/30 bg-primary/15 px-2 py-1 text-xs text-foreground"
                  : "rounded-md border border-border/60 bg-surface-2/50 px-2 py-1 text-xs text-muted-foreground hover:text-foreground"
              }
            >
              Editor
            </button>
            <button
              onClick={() => setTab("Módulos")}
              className={
                tab === "Módulos"
                  ? "rounded-md border border-secondary/30 bg-secondary/15 px-2 py-1 text-xs text-foreground"
                  : "rounded-md border border-border/60 bg-surface-2/50 px-2 py-1 text-xs text-muted-foreground hover:text-foreground"
              }
            >
              Módulos
            </button>
          </div>
        </div>

        {tab === "Editor" ? (
          <div className="grid flex-1 grid-cols-[42%_58%]">
            <div className="border-r border-border/60">
              <div className="px-3 py-2 text-xs font-semibold tracking-wide text-muted-foreground">Arquivos</div>
              <div className="h-[calc(100%-2.25rem)] overflow-auto px-2 pb-2">
                <Tree nodes={projectTree} base="" active={active} onPick={setActive} />
              </div>
            </div>
            <div className="flex flex-col">
              <div className="border-b border-border/60 px-3 py-2">
                <div className="text-xs font-semibold tracking-wide">{active ?? "Selecione um arquivo"}</div>
                <div className="text-[11px] text-muted-foreground">syntax highlighting (simples)</div>
              </div>
              <div className="flex-1 overflow-auto">
                <OrdaxCodeView
                  language={activeNode?.language ?? "ts"}
                  code={activeNode?.content ?? "// Selecione um arquivo à esquerda"}
                />
              </div>
            </div>
          </div>
        ) : (
          <div className="flex-1 overflow-auto p-3">
            <div className="rounded-lg border border-border/60 bg-surface-2/35 p-3">
              <div className="text-xs font-semibold tracking-wide">Engine: Ordax</div>
              <div className="mt-1 text-sm text-muted-foreground">Módulos carregados (mock) — pronto para milhares de combinações</div>
            </div>

            <div className="mt-3 space-y-2">
              {engineModules.map((m) => (
                <div
                  key={m.name}
                  className="rounded-lg border border-border/60 bg-surface-2/30 px-3 py-2 hover:border-primary/25"
                >
                  <div className="flex items-center justify-between">
                    <div className="text-sm font-semibold">{m.name}</div>
                    <div className="text-xs text-muted-foreground">{m.status}</div>
                  </div>
                  <div className="mt-1 text-sm text-muted-foreground">{m.detail}</div>
                </div>
              ))}
            </div>

            <div className="mt-4 rounded-lg border border-secondary/25 bg-surface-2/25 p-3">
              <div className="text-xs font-semibold tracking-wide">Próximo (prioridades)</div>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                <li>GameRunners: RacingGameRunner, SportsGameRunner, PuzzleGameRunner</li>
                <li>Sistemas: GridSystem, CardSystem, TowerDefenseSystem</li>
                <li>IA: prompt mais detalhado + retorno de JSON estruturado com gameType explícito</li>
              </ul>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}

function Tree({
  nodes,
  base,
  active,
  onPick,
}: {
  nodes: FileNode[];
  base: string;
  active?: string;
  onPick: (k: string) => void;
}) {
  return (
    <div className="space-y-1">
      {nodes.map((n) => {
        const key = base + n.path;
        if (n.kind === "folder") {
          return (
            <div key={key}>
              <div className="px-2 py-1 text-xs font-semibold tracking-wide text-muted-foreground">{n.path}</div>
              <div className="pl-2">
                <Tree nodes={n.children ?? []} base={key} active={active} onPick={onPick} />
              </div>
            </div>
          );
        }
        const isActive = key === active;
        return (
          <button
            key={key}
            onClick={() => onPick(key)}
            className={
              isActive
                ? "w-full rounded-md border border-primary/25 bg-primary/10 px-2 py-1 text-left text-sm"
                : "w-full rounded-md border border-border/50 bg-surface-2/20 px-2 py-1 text-left text-sm text-muted-foreground hover:text-foreground"
            }
          >
            {n.path}
          </button>
        );
      })}
    </div>
  );
}
