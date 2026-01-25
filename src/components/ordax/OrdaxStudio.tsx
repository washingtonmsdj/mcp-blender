import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { useMemo, useState } from "react";
import OrdaxChatPanel from "@/components/ordax/panels/OrdaxChatPanel";
import OrdaxCodePanel from "@/components/ordax/panels/OrdaxCodePanel";
import OrdaxPreviewPanel from "@/components/ordax/panels/OrdaxPreviewPanel";

type PanelState = {
  chatCollapsed: boolean;
  codeCollapsed: boolean;
};

export default function OrdaxStudio() {
  const [panelState, setPanelState] = useState<PanelState>({
    chatCollapsed: false,
    codeCollapsed: false,
  });

  const sizes = useMemo(() => {
    // chat / preview / code
    if (panelState.chatCollapsed && panelState.codeCollapsed) return [0, 100, 0] as const;
    if (panelState.chatCollapsed) return [0, 62, 38] as const;
    if (panelState.codeCollapsed) return [26, 74, 0] as const;
    return [26, 46, 28] as const;
  }, [panelState.chatCollapsed, panelState.codeCollapsed]);

  return (
    <section className="h-[calc(100vh-3rem)]">
      <PanelGroup direction="horizontal" className="h-full">
        <Panel defaultSize={sizes[0]} minSize={16} collapsible collapsedSize={0}>
          <OrdaxChatPanel
            collapsed={panelState.chatCollapsed}
            onToggleCollapse={() =>
              setPanelState((s) => ({ ...s, chatCollapsed: !s.chatCollapsed }))
            }
          />
        </Panel>

        <PanelResizeHandle className="w-2 bg-border/30 hover:bg-primary/25 transition-colors" />

        <Panel defaultSize={sizes[1]} minSize={30}>
          <OrdaxPreviewPanel
            leftCollapsed={panelState.chatCollapsed}
            rightCollapsed={panelState.codeCollapsed}
            onToggleLeft={() => setPanelState((s) => ({ ...s, chatCollapsed: !s.chatCollapsed }))}
            onToggleRight={() => setPanelState((s) => ({ ...s, codeCollapsed: !s.codeCollapsed }))}
          />
        </Panel>

        <PanelResizeHandle className="w-2 bg-border/30 hover:bg-secondary/20 transition-colors" />

        <Panel defaultSize={sizes[2]} minSize={18} collapsible collapsedSize={0}>
          <OrdaxCodePanel
            collapsed={panelState.codeCollapsed}
            onToggleCollapse={() =>
              setPanelState((s) => ({ ...s, codeCollapsed: !s.codeCollapsed }))
            }
          />
        </Panel>
      </PanelGroup>
    </section>
  );
}
