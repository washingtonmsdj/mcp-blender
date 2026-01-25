import { useMemo, useState } from "react";
import ClockCard from "@/components/ClockCard";
import TimezonePicker from "@/components/TimezonePicker";

const Index = () => {
  const [tz, setTz] = useState<string>("local");
  const timeZone = useMemo(() => (tz === "local" ? undefined : tz), [tz]);

  return (
    <main className="min-h-screen bg-background">
      <div className="relative isolate overflow-hidden">
        <div className="pointer-events-none absolute inset-0 bg-hero opacity-70" aria-hidden="true" />
        <div className="pointer-events-none absolute inset-x-0 top-[-240px] mx-auto h-[520px] w-[520px] rounded-full bg-primary/15 blur-3xl" aria-hidden="true" />
        <div className="pointer-events-none absolute right-[-160px] top-[120px] h-[420px] w-[420px] rounded-full bg-accent/15 blur-3xl" aria-hidden="true" />

        <div className="container relative flex flex-col items-center gap-6 py-14 md:py-20">
          <div className="w-full animate-enter-up">
            <ClockCard timeZone={timeZone} />
          </div>

          <div className="w-full max-w-4xl animate-enter-up">
            <div className="rounded-3xl border bg-card/40 p-6 shadow-soft backdrop-blur">
              <TimezonePicker value={tz} onChange={setTz} />
              <p className="mt-4 text-sm text-muted-foreground">
                Dica: o relógio atualiza continuamente (e respeita “reduzir movimento”, se ativado no sistema).
              </p>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
};

export default Index;
