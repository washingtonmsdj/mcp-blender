// UI System
export type UIElement = {
  id: string;
  type: "text" | "bar" | "button" | "image";
  x: number;
  y: number;
  width?: number;
  height?: number;
  text?: string;
  value?: number;
  maxValue?: number;
  color?: string;
  visible: boolean;
  onClick?: () => void;
};

export class UISystem {
  private elements: Map<string, UIElement> = new Map();

  addText(id: string, x: number, y: number, text: string, color: string = "#fff") {
    this.elements.set(id, {
      id,
      type: "text",
      x,
      y,
      text,
      color,
      visible: true,
    });
  }

  addBar(id: string, x: number, y: number, width: number, height: number, value: number, maxValue: number) {
    this.elements.set(id, {
      id,
      type: "bar",
      x,
      y,
      width,
      height,
      value,
      maxValue,
      visible: true,
    });
  }

  updateElement(id: string, updates: Partial<UIElement>) {
    const element = this.elements.get(id);
    if (element) {
      Object.assign(element, updates);
    }
  }

  render(ctx: CanvasRenderingContext2D, gameState?: string, entities?: any[], scoreSystem?: any, timerSystem?: any) {
    // Render manual elements
    for (const element of this.elements.values()) {
      if (!element.visible) continue;

      switch (element.type) {
        case "text":
          this.renderText(ctx, element);
          break;
        case "bar":
          this.renderBar(ctx, element);
          break;
      }
    }

    // Auto-render based on game state and metadata
    if (gameState && entities) {
      const uiMetadata = entities.find((e) => e.type === "ui" || e.id === "ui_metadata");
      
      if (gameState === "START") {
        this.renderStartScreen(ctx, uiMetadata?.props?.startScreen);
      } else if (gameState === "PLAYING") {
        this.renderHUD(ctx, entities, uiMetadata?.props?.hud, scoreSystem, timerSystem);
      } else if (gameState === "GAME_OVER") {
        this.renderGameOverScreen(ctx, uiMetadata?.props?.gameOverScreen, scoreSystem, timerSystem);
      }
    }
  }

  private renderStartScreen(ctx: CanvasRenderingContext2D, config?: any) {
    const title = config?.title || "Top-Down Shooter";
    const subtitle = config?.subtitle || "Survive as long as you can!";
    const instructions = config?.instructions || ["WASD - Move", "SPACE - Shoot"];

    ctx.fillStyle = "rgba(0, 0, 0, 0.8)";
    ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);

    ctx.fillStyle = "#fff";
    ctx.font = "48px monospace";
    ctx.textAlign = "center";
    ctx.fillText(title, ctx.canvas.width / 2, ctx.canvas.height / 2 - 100);

    ctx.font = "24px monospace";
    ctx.fillText(subtitle, ctx.canvas.width / 2, ctx.canvas.height / 2 - 50);

    ctx.font = "18px monospace";
    instructions.forEach((instruction: string, i: number) => {
      ctx.fillText(instruction, ctx.canvas.width / 2, ctx.canvas.height / 2 + i * 30);
    });

    ctx.font = "20px monospace";
    ctx.fillText("Press SPACE to start", ctx.canvas.width / 2, ctx.canvas.height / 2 + 150);
  }

  private renderHUD(ctx: CanvasRenderingContext2D, entities: any[], config?: any, scoreSystem?: any, timerSystem?: any) {
    const player = entities.find((e) => e.type === "player");
    if (!player || !player.props) return;

    const padding = 10;
    const barWidth = 200;
    const barHeight = 20;

    // Health bar
    const health = player.props.health || 0;
    const maxHealth = player.props.maxHealth || 100;
    
    ctx.fillStyle = "rgba(0, 0, 0, 0.5)";
    ctx.fillRect(padding, padding, barWidth, barHeight);
    
    ctx.fillStyle = health > 30 ? "#0f0" : "#f00";
    ctx.fillRect(padding, padding, barWidth * (health / maxHealth), barHeight);
    
    ctx.strokeStyle = "#fff";
    ctx.strokeRect(padding, padding, barWidth, barHeight);
    
    ctx.fillStyle = "#fff";
    ctx.font = "14px monospace";
    ctx.textAlign = "left";
    ctx.fillText(`Health: ${Math.floor(health)}/${maxHealth}`, padding, padding + barHeight + 15);

    // Score
    if (scoreSystem) {
      ctx.fillText(`Score: ${scoreSystem.getScore()}`, padding, padding + barHeight + 40);
    }

    // Timer
    if (timerSystem) {
      const time = Math.floor(timerSystem.getElapsedTime?.() || 0);
      ctx.fillText(`Time: ${time}s`, padding, padding + barHeight + 65);
    }

    // Wave (if available)
    const spawner = entities.find((e) => e.type === "spawner");
    if (spawner?.props?.currentWave) {
      ctx.fillText(`Wave: ${spawner.props.currentWave}`, padding, padding + barHeight + 90);
    }
  }

  private renderGameOverScreen(ctx: CanvasRenderingContext2D, config?: any, scoreSystem?: any, timerSystem?: any) {
    ctx.fillStyle = "rgba(0, 0, 0, 0.8)";
    ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);

    ctx.fillStyle = "#f00";
    ctx.font = "48px monospace";
    ctx.textAlign = "center";
    ctx.fillText("GAME OVER", ctx.canvas.width / 2, ctx.canvas.height / 2 - 100);

    ctx.fillStyle = "#fff";
    ctx.font = "24px monospace";

    if (scoreSystem) {
      ctx.fillText(`Final Score: ${scoreSystem.getScore()}`, ctx.canvas.width / 2, ctx.canvas.height / 2 - 30);
      ctx.fillText(`High Score: ${scoreSystem.getHighScore()}`, ctx.canvas.width / 2, ctx.canvas.height / 2 + 10);
    }

    if (timerSystem) {
      const time = Math.floor(timerSystem.getElapsedTime?.() || 0);
      ctx.fillText(`Survived: ${time}s`, ctx.canvas.width / 2, ctx.canvas.height / 2 + 50);
    }

    ctx.font = "20px monospace";
    ctx.fillText("Press R to restart", ctx.canvas.width / 2, ctx.canvas.height / 2 + 120);
  }

  private renderText(ctx: CanvasRenderingContext2D, element: UIElement) {
    ctx.fillStyle = element.color || "#fff";
    ctx.font = "16px monospace";
    ctx.fillText(element.text || "", element.x, element.y);
  }

  private renderBar(ctx: CanvasRenderingContext2D, element: UIElement) {
    const width = element.width || 100;
    const height = element.height || 20;
    const value = element.value || 0;
    const maxValue = element.maxValue || 100;
    const percent = value / maxValue;

    // Background
    ctx.fillStyle = "rgba(0,0,0,0.5)";
    ctx.fillRect(element.x, element.y, width, height);

    // Fill
    ctx.fillStyle = element.color || "#0f0";
    ctx.fillRect(element.x, element.y, width * percent, height);

    // Border
    ctx.strokeStyle = "#fff";
    ctx.strokeRect(element.x, element.y, width, height);
  }
}
