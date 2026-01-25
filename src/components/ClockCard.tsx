import { useEffect, useMemo, useRef, useState } from "react";
import { useNow } from "@/hooks/useNow";

type ClockCardProps = {
  timeZone?: string;
};

const pad2 = (n: number) => String(n).padStart(2, "0");

function formatTime(now: Date, hour12: boolean) {
  let hours = now.getHours();
  const minutes = now.getMinutes();
  const seconds = now.getSeconds();

  if (!hour12) {
    return `${pad2(hours)}:${pad2(minutes)}:${pad2(seconds)}`;
  }

  const ampm = hours >= 12 ? "PM" : "AM";
  hours = hours % 12;
  if (hours === 0) hours = 12;
  return `${pad2(hours)}:${pad2(minutes)}:${pad2(seconds)} ${ampm}`;
}

function formatDate(now: Date, locale = "pt-BR") {
  return new Intl.DateTimeFormat(locale, {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(now);
}

export default function ClockCard({ timeZone }: ClockCardProps) {
  const [hour12, setHour12] = useState(false);
  const now = useNow({ intervalMs: 250, timeZone });

  const timeLabel = useMemo(() => formatTime(now, hour12), [now, hour12]);
  const dateLabel = useMemo(() => formatDate(now), [now]);

  // Signature moment: a subtle “light field” that follows the pointer.
  const rootRef = useRef<HTMLDivElement | null>(null);
  const [spot, setSpot] = useState<{ x: number; y: number } | null>(null);

  useEffect(() => {
    const el = rootRef.current;
    if (!el) return;

    const media = window.matchMedia?.("(prefers-reduced-motion: reduce)");
    if (media?.matches) return;

    const onMove = (e: PointerEvent) => {
      const rect = el.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 100;
      const y = ((e.clientY - rect.top) / rect.height) * 100;
      setSpot({ x, y });
    };

    const onLeave = () => setSpot(null);

    el.addEventListener("pointermove", onMove);
    el.addEventListener("pointerleave", onLeave);
    return () => {
      el.removeEventListener("pointermove", onMove);
      el.removeEventListener("pointerleave", onLeave);
    };
  }, []);

  const seconds = now.getSeconds() + now.getMilliseconds() / 1000;
  const minutes = now.getMinutes() + seconds / 60;
  const hours = (now.getHours() % 12) + minutes / 60;

  const secAngle = seconds * 6; // 360/60
  const minAngle = minutes * 6;
  const hourAngle = hours * 30; // 360/12

  const spotStyle =
    spot == null
      ? undefined
      : ({
          backgroundImage: `radial-gradient(600px 420px at ${spot.x}% ${spot.y}%, hsl(var(--primary) / 0.18), transparent 55%)`,
        } as React.CSSProperties);

  return (
    <section
      ref={rootRef}
      className="relative w-full max-w-4xl overflow-hidden rounded-3xl border bg-card/70 p-6 shadow-soft backdrop-blur md:p-8"
      aria-label="Relógio"
    >
      <div className="pointer-events-none absolute inset-0 bg-hero opacity-90" aria-hidden="true" />
      <div
        className="pointer-events-none absolute inset-0 transition-opacity duration-500"
        style={spotStyle}
        aria-hidden="true"
      />

      <div className="relative grid gap-8 md:grid-cols-[1.1fr_0.9fr] md:items-center">
        <header className="space-y-3">
          <h1 className="text-balance text-3xl font-semibold tracking-tight md:text-4xl">
            Relógio
          </h1>
          <p className="text-balance text-sm text-muted-foreground md:text-base">
            Um relógio digital e analógico com um visual “midnight” e brilho suave.
          </p>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => setHour12((v) => !v)}
              className="rounded-full border bg-secondary/70 px-4 py-2 text-sm font-medium text-secondary-foreground shadow-soft transition hover:translate-y-[-1px] hover:shadow-elev focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {hour12 ? "Usar 24h" : "Usar 12h"}
            </button>
            <div className="rounded-full border bg-secondary/40 px-4 py-2 text-sm text-muted-foreground">
              {timeZone ? `Fuso: ${timeZone}` : "Fuso: local"}
            </div>
          </div>

          <div className="pt-3">
            <div
              className="font-mono text-4xl tracking-tight md:text-5xl"
              aria-label={`Hora atual: ${timeLabel}`}
            >
              {timeLabel}
            </div>
            <div className="mt-2 text-sm text-muted-foreground capitalize" aria-label={`Data: ${dateLabel}`}>
              {dateLabel}
            </div>
          </div>
        </header>

        <div className="flex items-center justify-center">
          <div className="relative aspect-square w-full max-w-[320px]">
            <div
              className="absolute inset-0 rounded-full border bg-surface/55 shadow-elev"
              aria-hidden="true"
            />
            <div
              className="absolute inset-[-10px] rounded-full ring-gradient opacity-70 blur-[10px]"
              aria-hidden="true"
            />
            <svg
              viewBox="0 0 200 200"
              className="relative h-full w-full"
              role="img"
              aria-label="Relógio analógico"
            >
              <defs>
                <filter id="softShadow" x="-50%" y="-50%" width="200%" height="200%">
                  <feDropShadow dx="0" dy="10" stdDeviation="10" floodColor="hsl(var(--foreground) / 0.10)" />
                </filter>
              </defs>

              {/* ticks */}
              {[...Array(60)].map((_, i) => {
                const isHour = i % 5 === 0;
                const len = isHour ? 10 : 6;
                const stroke = isHour ? "hsl(var(--foreground) / 0.8)" : "hsl(var(--foreground) / 0.35)";
                const w = isHour ? 2.2 : 1.2;
                const angle = (i * 6 * Math.PI) / 180;
                const rOuter = 92;
                const rInner = rOuter - len;
                const x1 = 100 + Math.cos(angle) * rInner;
                const y1 = 100 + Math.sin(angle) * rInner;
                const x2 = 100 + Math.cos(angle) * rOuter;
                const y2 = 100 + Math.sin(angle) * rOuter;
                return (
                  <line
                    key={i}
                    x1={x1}
                    y1={y1}
                    x2={x2}
                    y2={y2}
                    stroke={stroke}
                    strokeWidth={w}
                    strokeLinecap="round"
                    opacity={1}
                  />
                );
              })}

              {/* hands */}
              <g filter="url(#softShadow)">
                <line
                  x1="100"
                  y1="100"
                  x2="100"
                  y2="50"
                  stroke="hsl(var(--foreground) / 0.85)"
                  strokeWidth="4"
                  strokeLinecap="round"
                  transform={`rotate(${hourAngle} 100 100)`}
                />
                <line
                  x1="100"
                  y1="100"
                  x2="100"
                  y2="32"
                  stroke="hsl(var(--foreground) / 0.7)"
                  strokeWidth="2.6"
                  strokeLinecap="round"
                  transform={`rotate(${minAngle} 100 100)`}
                />
                <line
                  x1="100"
                  y1="110"
                  x2="100"
                  y2="24"
                  stroke="hsl(var(--primary) / 0.95)"
                  strokeWidth="2"
                  strokeLinecap="round"
                  transform={`rotate(${secAngle} 100 100)`}
                />
              </g>

              {/* center */}
              <circle cx="100" cy="100" r="6" fill="hsl(var(--primary))" />
              <circle cx="100" cy="100" r="2.4" fill="hsl(var(--primary-foreground) / 0.9)" />
            </svg>
          </div>
        </div>
      </div>
    </section>
  );
}
