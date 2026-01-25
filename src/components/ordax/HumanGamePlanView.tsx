import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { buildHumanGamePlanSections, type EngineGapReport } from "@/lib/ordax/human-game-plan";

type Props = {
  plan: unknown;
  planDiff?: unknown;
  warnings?: string[];
  engineGapReport?: EngineGapReport;
  heightClassName?: string;
};

export function HumanGamePlanView({ plan, planDiff, warnings, engineGapReport, heightClassName }: Props) {
  const sections = buildHumanGamePlanSections({ plan, planDiff, warnings, engineGapReport });

  return (
    <div className="rounded-md border border-border/50 bg-background/10">
      <div className="px-3 py-2 text-xs font-semibold">Plano (linguagem humana)</div>
      <Separator />
      <ScrollArea className={heightClassName ?? "h-[42vh]"}>
        <div className="p-3 space-y-4">
          {sections.map((s) => (
            <section key={s.id} className="space-y-1">
              <h3 className="text-xs font-semibold">{s.title}</h3>
              <ul className="list-disc pl-4 text-xs text-muted-foreground space-y-1">
                {s.bullets.map((b, i) => (
                  <li key={i}>{b}</li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}
