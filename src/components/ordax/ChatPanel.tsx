import { useState } from "react";
import { Send } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import type { OrdaxSpec } from "@/lib/ordax/types";
import { generateOrdaxSpec, type ChatMsg } from "@/lib/ordax/ai";

type Props = {
  onSpec: (spec: OrdaxSpec, raw: string) => void;
  currentSpec?: OrdaxSpec;
};

export function ChatPanel({ onSpec, currentSpec }: Props) {
  const { toast } = useToast();
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMsg[]>([
  ]);

  const send = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || isLoading) return;

    const nextMessages: ChatMsg[] = [...messages, { role: "user", content: trimmed }];
    setMessages(nextMessages);
    setInput("");
    setIsLoading(true);

    try {
      const result = await generateOrdaxSpec(
        nextMessages.filter((m) => m.role !== "assistant" || m.content.trim().length > 0),
        currentSpec,
      );
      if (result.error) {
        toast({
          title: "Erro",
          description: result.error,
          variant: "destructive",
        });
      }
      if (result.spec && result.raw) {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: `✓ ${result.spec.title}`,
          },
        ]);
        onSpec(result.spec, result.raw);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: "Não consegui gerar. Seja mais específico (gênero + mecânicas).",
          },
        ]);
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between gap-2 border-b border-border/50 glass-panel px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="text-sm font-bold tracking-wide">CHAT AI</div>
          <div className="h-2 w-2 rounded-full bg-neon-green animate-pulse"></div>
        </div>
        {isLoading && <div className="text-xs text-primary font-mono animate-pulse">Generating...</div>}
      </div>

      <ScrollArea className="flex-1 px-4 py-4">
        {messages.length === 0 && (
          <div className="glass-panel p-4 rounded-lg border border-border/50">
            <div className="text-sm text-muted-foreground">
              Descreva seu jogo (ex: "jogo de nave espacial com asteroides").
            </div>
          </div>
        )}
        <div className="space-y-3">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={cn(
                "max-w-[90%] rounded-lg px-4 py-3 text-sm animate-fade-in",
                m.role === "user"
                  ? "ml-auto glass-panel border border-primary/30 text-foreground"
                  : "glass-panel border border-border/50 text-foreground",
              )}
            >
              <div className="whitespace-pre-wrap leading-relaxed font-mono text-xs">{m.content}</div>
            </div>
          ))}
        </div>
      </ScrollArea>

      <div className="border-t border-border/50 glass-panel p-4">
        <div className="flex gap-2">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Descreva o jogo..."
            className="min-h-[60px] max-h-[120px] resize-none glass-panel border-border/50 font-mono text-sm"
            onKeyDown={(e) => {
              if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
                e.preventDefault();
                void send(input);
              }
            }}
          />
          <Button
            size="icon"
            className="h-auto shrink-0 self-end neon-glow bg-primary hover:bg-primary/80"
            onClick={() => void send(input)}
            disabled={isLoading || !input.trim()}
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
