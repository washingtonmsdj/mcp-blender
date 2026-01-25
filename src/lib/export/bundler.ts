import { vfs } from "@/lib/vfs/VirtualFileSystem";
import { compiler } from "@/lib/compiler/TypeScriptCompiler";
import type { OrdaxSpec } from "@/lib/ordax/types";

export type ExportOptions = {
  projectName: string;
  includeAssets: boolean;
  minify: boolean;
};

export type ExportResult = {
  success: boolean;
  files?: Map<string, string>;
  html?: string;
  error?: string;
};

export class GameBundler {
  async bundle(spec: OrdaxSpec, options: ExportOptions): Promise<ExportResult> {
    try {
      // Get all TypeScript files from VFS
      const files = vfs.getAllFiles();
      const compiledFiles = new Map<string, string>();

      // Compile TypeScript files
      for (const file of files) {
        if (file.language === "typescript") {
          const result = compiler.compile(file.name, file.content);
          
          if (!result.success) {
            return {
              success: false,
              error: `Compilation error in ${file.name}: ${result.errors?.join(", ")}`,
            };
          }

          compiledFiles.set(
            file.name.replace(".ts", ".js"),
            result.output || ""
          );
        } else {
          compiledFiles.set(file.name, file.content);
        }
      }

      // Generate HTML
      const html = this.generateHTML(spec, compiledFiles, options);

      return {
        success: true,
        files: compiledFiles,
        html,
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : String(error),
      };
    }
  }

  private generateHTML(
    spec: OrdaxSpec,
    files: Map<string, string>,
    options: ExportOptions
  ): string {
    // Bundle all JS files
    const jsBundle = Array.from(files.entries())
      .filter(([name]) => name.endsWith(".js"))
      .map(([_, content]) => content)
      .join("\n\n");

    // Generate engine code
    const engineCode = this.generateEngineCode(spec);

    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${options.projectName}</title>
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }
    
    body {
      background: #000;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      font-family: system-ui, -apple-system, sans-serif;
    }
    
    #game-container {
      position: relative;
    }
    
    canvas {
      border: 1px solid #333;
      display: block;
    }
    
    #info {
      position: absolute;
      top: 10px;
      left: 10px;
      color: #fff;
      font-size: 12px;
      text-shadow: 1px 1px 2px #000;
    }
  </style>
</head>
<body>
  <div id="game-container">
    <canvas id="game-canvas" width="800" height="600"></canvas>
    <div id="info">
      <div>Controls: WASD or Arrow Keys</div>
      <div id="fps">FPS: 60</div>
    </div>
  </div>

  <script type="module">
    // Game Spec
    const SPEC = ${JSON.stringify(spec, null, 2)};
    
    // Engine Code
    ${engineCode}
    
    // User Code
    ${jsBundle}
    
    // Initialize Game
    const game = new OrdaxGame(SPEC);
    game.start();
  </script>
</body>
</html>`;
  }

  private generateEngineCode(spec: OrdaxSpec): string {
    return `
// Ordax Engine Runtime
class OrdaxGame {
  constructor(spec) {
    this.spec = spec;
    this.canvas = document.getElementById('game-canvas');
    this.ctx = this.canvas.getContext('2d');
    this.running = false;
    this.entities = [];
    this.keys = {};
    this.lastTime = 0;
    this.fps = 60;
    
    this.initEntities();
    this.initInput();
  }
  
  initEntities() {
    this.entities = this.spec.scene.entities.map(e => ({
      ...e,
      vx: 0,
      vy: 0,
    }));
  }
  
  initInput() {
    window.addEventListener('keydown', (e) => {
      this.keys[e.key] = true;
    });
    
    window.addEventListener('keyup', (e) => {
      this.keys[e.key] = false;
    });
  }
  
  start() {
    this.running = true;
    this.lastTime = performance.now();
    this.loop();
  }
  
  loop() {
    if (!this.running) return;
    
    const now = performance.now();
    const dt = Math.min(0.05, (now - this.lastTime) / 1000);
    this.lastTime = now;
    
    this.update(dt);
    this.render();
    
    // Update FPS
    this.fps = Math.round(1 / dt);
    document.getElementById('fps').textContent = 'FPS: ' + this.fps;
    
    requestAnimationFrame(() => this.loop());
  }
  
  update(dt) {
    // Update player
    const player = this.entities.find(e => e.type === 'player' || e.id === 'player');
    if (player) {
      const speed = player.props?.speed || 220;
      let vx = 0, vy = 0;
      
      if (this.keys['ArrowLeft'] || this.keys['a']) vx -= 1;
      if (this.keys['ArrowRight'] || this.keys['d']) vx += 1;
      if (this.keys['ArrowUp'] || this.keys['w']) vy -= 1;
      if (this.keys['ArrowDown'] || this.keys['s']) vy += 1;
      
      const len = Math.hypot(vx, vy) || 1;
      vx /= len;
      vy /= len;
      
      player.x += vx * speed * dt;
      player.y += vy * speed * dt;
      
      player.x = Math.max(0, Math.min(800, player.x));
      player.y = Math.max(0, Math.min(600, player.y));
    }
    
    // Update spawners
    const spawners = this.entities.filter(e => e.type === 'spawner');
    spawners.forEach(spawner => {
      if (!spawner.timer) spawner.timer = 0;
      spawner.timer += dt;
      
      const rate = spawner.props?.spawnRate || 1.5;
      if (spawner.timer >= 1 / rate) {
        spawner.timer = 0;
        this.entities.push({
          id: 'spawned_' + Date.now(),
          type: 'enemy',
          x: spawner.x + (Math.random() - 0.5) * spawner.w,
          y: spawner.y,
          w: 24,
          h: 24,
          vy: 80,
        });
      }
    });
    
    // Update spawned entities
    this.entities = this.entities.filter(e => {
      if (e.vy) {
        e.y += e.vy * dt;
        return e.y < 650;
      }
      return true;
    });
  }
  
  render() {
    const ctx = this.ctx;
    const theme = this.spec.visual?.theme || {};
    
    // Clear
    ctx.fillStyle = theme.background || '#0a0a0a';
    ctx.fillRect(0, 0, 800, 600);
    
    // Draw background layers
    const layers = this.spec.visual?.background?.layers || [];
    layers.forEach(layer => {
      if (layer.type === 'gradient') {
        const grad = ctx.createLinearGradient(0, 0, 0, 600);
        grad.addColorStop(0, theme.primary || '#00ffff');
        grad.addColorStop(1, theme.background || '#0a0a0a');
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, 800, 600);
      }
    });
    
    // Draw entities
    this.entities.forEach(e => {
      let fill = theme.primary || '#00ffff';
      let stroke = theme.primary || '#00ffff';
      
      if (e.type === 'player' || e.id === 'player') {
        fill = theme.primary || '#00ffff';
      } else if (e.type.includes('enemy')) {
        fill = theme.accent || '#ff00ff';
      } else if (e.type === 'spawner') {
        fill = 'rgba(255,255,0,0.2)';
        stroke = 'rgba(255,255,0,0.5)';
      }
      
      ctx.fillStyle = fill + '40';
      ctx.strokeStyle = stroke;
      ctx.lineWidth = 2;
      
      ctx.beginPath();
      ctx.roundRect(e.x - e.w/2, e.y - e.h/2, e.w, e.h, 4);
      ctx.fill();
      ctx.stroke();
      
      // Label
      ctx.fillStyle = '#fff';
      ctx.font = '10px monospace';
      ctx.fillText(e.id, e.x - e.w/2 + 6, e.y - e.h/2 + 16);
    });
  }
}
`;
  }

  async exportAsZip(spec: OrdaxSpec, options: ExportOptions): Promise<Blob | null> {
    const result = await this.bundle(spec, options);
    
    if (!result.success || !result.html) {
      return null;
    }

    // For now, just return HTML as blob
    // In production, use JSZip to create proper zip
    return new Blob([result.html], { type: "text/html" });
  }

  downloadHTML(spec: OrdaxSpec, options: ExportOptions) {
    this.bundle(spec, options).then((result) => {
      if (!result.success || !result.html) {
        console.error("Export failed:", result.error);
        return;
      }

      const blob = new Blob([result.html], { type: "text/html" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${options.projectName}.html`;
      a.click();
      URL.revokeObjectURL(url);
    });
  }
}

export const bundler = new GameBundler();
