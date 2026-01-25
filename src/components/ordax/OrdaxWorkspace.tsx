import { useState } from "react";
import { Link } from "react-router-dom";

import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
import {
  Sidebar,
  SidebarContent,
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Sparkles } from "lucide-react";

import type { OrdaxSpec } from "@/lib/ordax/types";
import { ChatPanel } from "@/components/ordax/ChatPanel";
import { PreviewPanel } from "@/components/ordax/PreviewPanel";
import { EditorPanel } from "@/components/ordax/EditorPanel";

export function OrdaxWorkspace() {
  const [spec, setSpec] = useState<OrdaxSpec | undefined>(undefined);
  const [rawJson, setRawJson] = useState<string | undefined>(undefined);

  return (
    <SidebarProvider>
      {/* Right sidebar = Editor/Assets */}
      <Sidebar side="right" variant="inset" collapsible="offcanvas" className="border-l border-border/50 glass-panel">
        <SidebarContent className="p-0">
          <EditorPanel spec={spec} rawJson={rawJson} />
        </SidebarContent>
      </Sidebar>

      {/* Main app */}
      <SidebarInset>
        <header className="flex h-14 items-center justify-between border-b border-border/50 glass-panel px-4">
          <div className="flex items-center gap-3">
            <SidebarTrigger className="mr-1" />
            <div className="font-bold tracking-tight text-lg neon-text">Ordax</div>
            <Badge variant="secondary" className="border border-primary/30 bg-primary/10 text-primary font-mono text-xs">
              ENGINE
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <Link to="/demo">
              <Button variant="outline" size="sm" className="glass-panel border-border/50 hover:border-primary/30 transition-colors font-mono text-xs">
                <Sparkles className="mr-2 h-3 w-3" />
                View Demo
              </Button>
            </Link>
            <Badge variant="outline" className="border-border/60 bg-surface-2 font-mono text-xs">
              {spec ? `${spec.gameType}` : "No Spec"}
            </Badge>
          </div>
        </header>

        <div className="h-[calc(100svh-3.5rem)]">
          <ResizablePanelGroup direction="horizontal" className="h-full w-full">
            <ResizablePanel defaultSize={28} minSize={20}>
              <div className="h-full border-r border-border/50">
                <ChatPanel
                  currentSpec={spec}
                  onSpec={(next, raw) => {
                    setSpec(next);
                    setRawJson(raw);
                  }}
                />
              </div>
            </ResizablePanel>

            <ResizableHandle withHandle className="bg-border/50 hover:bg-primary/30 transition-colors" />

            <ResizablePanel defaultSize={72} minSize={40}>
              <PreviewPanel spec={spec} />
            </ResizablePanel>
          </ResizablePanelGroup>
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
