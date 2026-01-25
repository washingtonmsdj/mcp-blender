import { useEffect, useMemo, useRef, useState } from "react";

type Msg = {
  id: string;
  role: "user" | "assistant";
  content: string;
  ts: number;
};

const quickCommands = [
  "/novo Plataforma 2D (pixel art)",
  "/add inimigos patrulha + colisão",
  "/gerar HUD (vida + score)",
  "/converter para 3D (Babylon) [preview]",
];

function uid() {
  return Math.random().toString(16).slice(2) + Date.now().toString(16);
}

export default function OrdaxChatPanel({
  collapsed,
  onToggleCollapse,
}: {
  collapsed: boolean;
  onToggleCollapse: () => void;
}) {
  const [input, setInput] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const [messages, setMessages] = useState<Msg[]>(() => [
    {
      id: uid(),
      role: "assistant",
      content:
        "Ordax online. Descreva o jogo ou use comandos rápidos. Dica: tente \"crie um platformer 2D com dash e checkpoints\".",
      ts: Date.now(),
    },
  ]);

  const listRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages.length, isThinking]);

  const assistantTemplates = useMemo(
    () => [
      "Entendido. Vou montar a cena base, configurar física/colisão e criar o loop de jogo.",
      "Aplicando patch: InputSystem + PhysicsSystem + CollisionSystem. Atualizando preview…",
      "Gerando assets placeholder (temporário) e ajustando câmera follow + bounds.",
      "OK. Build passou. Quer que eu gere variações (milhares de combinações) via GameRunner?",
    ],
    [],
  );

  const reply = async (userText: string) => {
    setIsThinking(true);
    const base = assistantTemplates[Math.floor(Math.random() * assistantTemplates.length)];
    const extra =
      userText.toLowerCase().includes("3d") || userText.toLowerCase().includes("babylon")
        ? "\n\nNota: suporte 3D (Babylon) está marcado como \"preview\" nesta versão — o pipeline real entra quando conectarmos o Cloud + IA."
        : "";

    // Simula streaming em 2 passos (rápido)
    await new Promise((r) => setTimeout(r, 420));
    setMessages((prev) => [
      ...prev,
      { id: uid(), role: "assistant", content: base, ts: Date.now() },
    ]);
    await new Promise((r) => setTimeout(r, 520));
    if (extra) {
      setMessages((prev) => [
        ...prev,
        { id: uid(), role: "assistant", content: extra, ts: Date.now() },
      ]);
    }
    setIsThinking(false);
  };

  const send = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || isThinking) return;

    setMessages((prev) => [...prev, { id: uid(), role: "user", content: trimmed, ts: Date.now() }]);
    setInput("");
    await reply(trimmed);
  };

  if (collapsed) {
    return (
      <aside className="h-full border-r border-border/60 bg-surface-1/60">
        <button
          className="h-full w-full ordax-grid ordax-grid-anim text-left"
          onClick={onToggleCollapse}
          aria-label="Expandir Chat"
        >
          <div className="flex h-full items-center justify-center">
            <div className="rotate-180 text-xs font-medium tracking-wide text-muted-foreground [writing-mode:vertical-rl]">
              CHAT IA
            </div>
          </div>
        </button>
      </aside>
    );
  }

  return (
    <aside className="h-full border-r border-border/60 bg-surface-1/60">
      <div className="flex h-full flex-col">
        <div className="flex items-center justify-between border-b border-border/60 px-3 py-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold tracking-wide">Chat IA</span>
            <span className="text-[11px] text-muted-foreground">(simulado)</span>
          </div>
          <button
            onClick={onToggleCollapse}
            className="rounded-md border border-border/60 bg-surface-2/60 px-2 py-1 text-xs text-muted-foreground hover:text-foreground"
            aria-label="Colapsar Chat"
          >
            Collapse
          </button>
        </div>

        <div className="border-b border-border/60 p-3">
          <div className="flex flex-wrap gap-2">
            {quickCommands.map((cmd) => (
              <button
                key={cmd}
                onClick={() => send(cmd)}
                className="rounded-md border border-border/60 bg-surface-2/50 px-2 py-1 text-xs text-muted-foreground hover:border-primary/40 hover:text-foreground"
              >
                {cmd}
              </button>
            ))}
          </div>
        </div>

        <div ref={listRef} className="flex-1 overflow-auto p-3">
          <div className="space-y-3">
            {messages.map((m) => (
              <div key={m.id} className={m.role === "user" ? "flex justify-end" : "flex justify-start"}>
                <div
                  className={
                    m.role === "user"
                      ? "max-w-[92%] rounded-xl border border-primary/25 bg-surface-2/65 px-3 py-2 shadow-glow"
                      : "max-w-[92%] rounded-xl border border-border/60 bg-surface-2/45 px-3 py-2"
                  }
                >
                  <div className="text-[11px] font-medium tracking-wide text-muted-foreground">
                    {m.role === "user" ? "VOCÊ" : "ORDAX"}
                  </div>
                  <div className="mt-1 whitespace-pre-wrap text-sm leading-relaxed text-foreground/95">
                    {m.content}
                  </div>
                </div>
              </div>
            ))}
            {isThinking ? (
              <div className="flex justify-start">
                <div className="max-w-[92%] rounded-xl border border-border/60 bg-surface-2/35 px-3 py-2">
                  <div className="text-[11px] font-medium tracking-wide text-muted-foreground">ORDAX</div>
                  <div className="mt-1 text-sm text-muted-foreground">Processando…</div>
                </div>
              </div>
            ) : null}
          </div>
        </div>

        <form
          className="border-t border-border/60 p-3"
          onSubmit={(e) => {
            e.preventDefault();
            void send(input);
          }}
        >
          <div className="flex items-center gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Descreva o jogo, peça mudanças, ou use /comandos…"
              className="h-10 flex-1 rounded-md border border-input bg-surface-2/50 px-3 text-sm outline-none placeholder:text-muted-foreground focus:ring-2 focus:ring-ring"
            />
            <button
              type="submit"
              className="h-10 rounded-md border border-primary/35 bg-primary/15 px-3 text-sm font-medium text-foreground hover:bg-primary/20"
            >
              Enviar
            </button>
          </div>
        </form>
      </div>
    </aside>
  );
}
