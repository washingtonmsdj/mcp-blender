import { useEffect, useMemo, useRef, useState } from "react";

type Mode = "2D" | "3D";

type Player = { x: number; y: number; vx: number; vy: number };

export default function OrdaxPreviewPanel({
  leftCollapsed,
  rightCollapsed,
  onToggleLeft,
  onToggleRight,
}: {
  leftCollapsed: boolean;
  rightCollapsed: boolean;
  onToggleLeft: () => void;
  onToggleRight: () => void;
}) {
  const [mode, setMode] = useState<Mode>("2D");
  const [running, setRunning] = useState(true);
  const [device, setDevice] = useState<"Desktop" | "Mobile">("Desktop");
  const [fps, setFps] = useState(60);
  const [pointer, setPointer] = useState({ x: 0.5, y: 0.35 });

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const rafRef = useRef<number | null>(null);
  const playerRef = useRef<Player>({ x: 64, y: 48, vx: 0, vy: 0 });
  const keysRef = useRef<Record<string, boolean>>({});

  const previewFrame = useMemo(() => {
    return device === "Desktop" ? "aspect-[16/9]" : "aspect-[9/16]";
  }, [device]);

  useEffect(() => {
    const onDown = (e: KeyboardEvent) => {
      keysRef.current[e.key.toLowerCase()] = true;
    };
    const onUp = (e: KeyboardEvent) => {
      keysRef.current[e.key.toLowerCase()] = false;
    };
    window.addEventListener("keydown", onDown);
    window.addEventListener("keyup", onUp);
    return () => {
      window.removeEventListener("keydown", onDown);
      window.removeEventListener("keyup", onUp);
    };
  }, []);

  useEffect(() => {
    if (mode !== "2D") return;
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let last = performance.now();
    let frames = 0;
    let fpsLast = performance.now();

    const resize = () => {
      const dpr = Math.max(1, Math.min(2, window.devicePixelRatio || 1));
      const rect = canvas.getBoundingClientRect();
      canvas.width = Math.floor(rect.width * dpr);
      canvas.height = Math.floor(rect.height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const ro = new ResizeObserver(resize);
    ro.observe(canvas);
    resize();

    const groundY = () => (canvas.getBoundingClientRect().height ?? 360) - 64;
    const platform = { x: 42, y: 0, w: 0, h: 14 };

    const loop = (t: number) => {
      rafRef.current = requestAnimationFrame(loop);
      const dt = Math.min(0.032, (t - last) / 1000);
      last = t;
      if (!running) {
        draw();
        return;
      }

      frames++;
      if (t - fpsLast >= 500) {
        setFps(Math.round((frames * 1000) / (t - fpsLast)));
        fpsLast = t;
        frames = 0;
      }

      // update platform based on current canvas size
      const rect = canvas.getBoundingClientRect();
      platform.y = rect.height * 0.62;
      platform.w = rect.width * 0.55;

      const p = playerRef.current;
      const keys = keysRef.current;

      const accel = 1500;
      const maxVx = 320;
      const gravity = 1600;
      const jump = 520;
      const friction = 0.88;

      if (keys["a"] || keys["arrowleft"]) p.vx -= accel * dt;
      if (keys["d"] || keys["arrowright"]) p.vx += accel * dt;
      p.vx = Math.max(-maxVx, Math.min(maxVx, p.vx));

      // gravity
      p.vy += gravity * dt;

      // integrate
      p.x += p.vx * dt;
      p.y += p.vy * dt;

      // collisions (ground + one platform)
      const gY = groundY();
      const size = 22;

      // ground
      if (p.y + size > gY) {
        p.y = gY - size;
        p.vy = 0;
        if (keys["w"] || keys[" "] || keys["arrowup"]) {
          p.vy = -jump;
        }
      }

      // platform AABB (simple top collision)
      const px = p.x;
      const py = p.y;
      const onTop =
        px + size > platform.x &&
        px < platform.x + platform.w &&
        py + size > platform.y &&
        py + size < platform.y + platform.h + 18 &&
        p.vy >= 0;

      if (onTop) {
        p.y = platform.y - size;
        p.vy = 0;
        if (keys["w"] || keys[" "] || keys["arrowup"]) {
          p.vy = -jump;
        }
      }

      // bounds
      const boundsW = rect.width;
      p.x = Math.max(16, Math.min(boundsW - 16 - size, p.x));

      // friction when grounded
      const grounded = p.y + size >= gY - 0.5 || onTop;
      if (grounded) p.vx *= friction;

      draw();
    };

    const draw = () => {
      const rect = canvas.getBoundingClientRect();

      // clear
      ctx.clearRect(0, 0, rect.width, rect.height);

      // background
      ctx.fillStyle = "rgba(0,0,0,0)";
      ctx.fillRect(0, 0, rect.width, rect.height);

      // grid overlay
      ctx.save();
      ctx.globalAlpha = 0.55;
      ctx.strokeStyle = "rgba(255,255,255,0.05)";
      ctx.lineWidth = 1;
      const step = 28;
      for (let x = 0; x < rect.width; x += step) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, rect.height);
        ctx.stroke();
      }
      for (let y = 0; y < rect.height; y += step) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(rect.width, y);
        ctx.stroke();
      }
      ctx.restore();

      // ground
      const gY = groundY();
      ctx.fillStyle = "rgba(0,229,255,0.10)";
      ctx.fillRect(0, gY, rect.width, rect.height - gY);
      ctx.strokeStyle = "rgba(0,229,255,0.30)";
      ctx.beginPath();
      ctx.moveTo(0, gY);
      ctx.lineTo(rect.width, gY);
      ctx.stroke();

      // platform
      ctx.fillStyle = "rgba(255,0,229,0.10)";
      ctx.fillRect(platform.x, platform.y, platform.w, platform.h);
      ctx.strokeStyle = "rgba(255,0,229,0.35)";
      ctx.strokeRect(platform.x, platform.y, platform.w, platform.h);

      // player
      const p = playerRef.current;
      const size = 22;
      ctx.fillStyle = "rgba(0,229,255,0.45)";
      ctx.fillRect(p.x, p.y, size, size);
      ctx.strokeStyle = "rgba(0,229,255,0.9)";
      ctx.strokeRect(p.x, p.y, size, size);

      // hud
      ctx.fillStyle = "rgba(255,255,255,0.72)";
      ctx.font = "12px JetBrains Mono";
      ctx.fillText("W/A/D ou setas — pular/andar", 12, 18);
      ctx.fillText("Espaço — pular", 12, 36);
    };

    rafRef.current = requestAnimationFrame(loop);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      ro.disconnect();
    };
  }, [mode, running]);

  const previewStyle = useMemo(() => {
    const x = Math.round(pointer.x * 100);
    const y = Math.round(pointer.y * 100);
    return {
      backgroundImage: `radial-gradient(800px 520px at ${x}% ${y}%, hsl(var(--glow-primary) / 0.22), transparent 58%), radial-gradient(700px 520px at ${100 - x}% ${Math.min(
        85,
        y + 18,
      )}%, hsl(var(--glow-secondary) / 0.15), transparent 55%)`,
    } as const;
  }, [pointer.x, pointer.y]);

  return (
    <section className="h-full">
      <div className="flex h-full flex-col">
        <div className="flex items-center justify-between border-b border-border/60 bg-surface-1/55 px-3 py-2 backdrop-blur">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold tracking-wide">Preview</span>
            <span className="text-[11px] text-muted-foreground">{mode}</span>
            <span className="ml-2 rounded-md border border-border/60 bg-surface-2/60 px-2 py-1 text-[11px] text-muted-foreground">
              FPS: {fps}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={onToggleLeft}
              className="rounded-md border border-border/60 bg-surface-2/50 px-2 py-1 text-xs text-muted-foreground hover:text-foreground"
              aria-label={leftCollapsed ? "Expandir Chat" : "Colapsar Chat"}
            >
              {leftCollapsed ? "Show Chat" : "Hide Chat"}
            </button>
            <button
              onClick={() => setRunning((r) => !r)}
              className="rounded-md border border-primary/30 bg-primary/15 px-2 py-1 text-xs text-foreground hover:bg-primary/20"
            >
              {running ? "Pause" : "Play"}
            </button>
            <button
              onClick={() => setDevice((d) => (d === "Desktop" ? "Mobile" : "Desktop"))}
              className="rounded-md border border-border/60 bg-surface-2/50 px-2 py-1 text-xs text-muted-foreground hover:text-foreground"
            >
              {device}
            </button>
            <div className="mx-1 h-6 w-px bg-border/60" aria-hidden="true" />
            <button
              onClick={() => setMode((m) => (m === "2D" ? "3D" : "2D"))}
              className={
                mode === "2D"
                  ? "rounded-md border border-border/60 bg-surface-2/50 px-2 py-1 text-xs text-muted-foreground hover:text-foreground"
                  : "rounded-md border border-secondary/30 bg-secondary/15 px-2 py-1 text-xs text-foreground hover:bg-secondary/20"
              }
            >
              {mode === "2D" ? "2D" : "3D (Babylon)"}
            </button>
            <button
              onClick={onToggleRight}
              className="rounded-md border border-border/60 bg-surface-2/50 px-2 py-1 text-xs text-muted-foreground hover:text-foreground"
              aria-label={rightCollapsed ? "Expandir Editor" : "Colapsar Editor"}
            >
              {rightCollapsed ? "Show Editor" : "Hide Editor"}
            </button>
          </div>
        </div>

        <div className="flex-1 p-4">
          <div
            className={`relative mx-auto w-full max-w-5xl overflow-hidden rounded-xl border border-border/60 bg-surface-2/40 shadow-elev ${previewFrame}`}
            onPointerMove={(e) => {
              const r = (e.currentTarget as HTMLDivElement).getBoundingClientRect();
              const x = (e.clientX - r.left) / r.width;
              const y = (e.clientY - r.top) / r.height;
              setPointer({ x: Math.max(0, Math.min(1, x)), y: Math.max(0, Math.min(1, y)) });
            }}
            style={previewStyle}
          >
            <div className="absolute inset-0 ordax-grid ordax-grid-anim opacity-60" aria-hidden="true" />
            {mode === "2D" ? (
              <canvas ref={canvasRef} className="relative h-full w-full" />
            ) : (
              <div className="relative flex h-full w-full items-center justify-center p-8">
                <div className="max-w-lg rounded-xl border border-secondary/25 bg-surface-1/70 p-5 shadow-magenta">
                  <div className="text-sm font-semibold">Preview 3D (Babylon) — em breve</div>
                  <p className="mt-2 text-sm text-muted-foreground">
                    Nesta primeira versão, o toggle 3D é um placeholder de pipeline. Quando conectarmos o Cloud + IA, a Ordax poderá
                    gerar um <span className="text-foreground">GameRunner 3D</span> e inicializar Babylon no preview.
                  </p>
                  <div className="mt-3 text-xs text-muted-foreground">
                    Sugestão: peça no chat “gerar runner 3D com câmera follow + física” para simular o fluxo.
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="mx-auto mt-4 max-w-5xl">
            <div className="grid gap-3 md:grid-cols-3">
              <div className="rounded-lg border border-border/60 bg-surface-2/35 p-3">
                <div className="text-xs font-semibold tracking-wide">Cena</div>
                <div className="mt-1 text-sm text-muted-foreground">Platformer Demo • Camera Follow • AABB Collisions</div>
              </div>
              <div className="rounded-lg border border-border/60 bg-surface-2/35 p-3">
                <div className="text-xs font-semibold tracking-wide">Status</div>
                <div className="mt-1 text-sm text-muted-foreground">Build OK • Hot Reload • Assets: 14</div>
              </div>
              <div className="rounded-lg border border-border/60 bg-surface-2/35 p-3">
                <div className="text-xs font-semibold tracking-wide">Controles</div>
                <div className="mt-1 text-sm text-muted-foreground">W/A/D ou setas • Espaço p/ pular • Pause/Play acima</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
