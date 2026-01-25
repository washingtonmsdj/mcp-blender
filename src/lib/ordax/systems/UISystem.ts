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

  render(ctx: CanvasRenderingContext2D) {
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
