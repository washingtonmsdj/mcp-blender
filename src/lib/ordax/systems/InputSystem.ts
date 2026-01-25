// Input System - Handles keyboard/mouse input for top-down shooter
import type { OrdaxEntity } from "../types";

export type InputState = {
  keys: Set<string>;
  mouse: {
    x: number;
    y: number;
    buttons: Set<number>;
  };
};

export class InputSystem {
  private inputState: InputState = {
    keys: new Set(),
    mouse: {
      x: 0,
      y: 0,
      buttons: new Set(),
    },
  };

  private lastFireTime: number = 0;

  constructor() {
    this.setupListeners();
  }

  private setupListeners() {
    // Keyboard
    window.addEventListener("keydown", (e) => {
      this.inputState.keys.add(e.key.toUpperCase());
    });

    window.addEventListener("keyup", (e) => {
      this.inputState.keys.delete(e.key.toUpperCase());
    });

    // Mouse
    window.addEventListener("mousemove", (e) => {
      this.inputState.mouse.x = e.clientX;
      this.inputState.mouse.y = e.clientY;
    });

    window.addEventListener("mousedown", (e) => {
      this.inputState.mouse.buttons.add(e.button);
    });

    window.addEventListener("mouseup", (e) => {
      this.inputState.mouse.buttons.delete(e.button);
    });
  }

  update(dt: number, entities: OrdaxEntity[], currentTime: number = Date.now() / 1000) {
    // Find player
    const player = entities.find((e) => e.type === "player");
    if (!player || !player.props) return;

    // Read controls from metadata or use defaults
    const controlsEntity = entities.find((e) => e.type === "controls");
    const controls = controlsEntity?.props || {
      movement: { up: "W", down: "S", left: "A", right: "D" },
      action: { shoot: " ", shootAlt: "MOUSE_LEFT" }, // SPACE is " "
    };

    // Movement (WASD)
    let vx = 0;
    let vy = 0;
    const speed = player.props.speed || 200;

    if (this.inputState.keys.has(controls.movement.up)) vy -= 1;
    if (this.inputState.keys.has(controls.movement.down)) vy += 1;
    if (this.inputState.keys.has(controls.movement.left)) vx -= 1;
    if (this.inputState.keys.has(controls.movement.right)) vx += 1;

    // Normalize diagonal movement
    if (vx !== 0 && vy !== 0) {
      const length = Math.sqrt(vx * vx + vy * vy);
      vx /= length;
      vy /= length;
    }

    // Apply velocity
    player.props.vx = vx * speed;
    player.props.vy = vy * speed;

    // Shooting (SPACE or MOUSE_LEFT)
    const fireRate = player.props.fireRate || 0.25;
    const canFire = currentTime - this.lastFireTime >= fireRate;

    if (canFire && (this.inputState.keys.has(" ") || this.inputState.mouse.buttons.has(0))) {
      this.createBullet(player, entities);
      this.lastFireTime = currentTime;
    }
  }

  private createBullet(player: OrdaxEntity, entities: OrdaxEntity[]) {
    // Find bullet template
    const bulletTemplate = entities.find((e) => e.type === "bullet");
    if (!bulletTemplate) return;

    // Create new bullet
    const bullet: OrdaxEntity = {
      id: `bullet_${Date.now()}_${Math.random()}`,
      type: "bullet",
      x: player.x,
      y: player.y,
      w: bulletTemplate.w,
      h: bulletTemplate.h,
      props: {
        ...bulletTemplate.props,
        vx: 0,
        vy: -(bulletTemplate.props?.speed || 400), // Shoot upward
        owner: "player",
        createdAt: Date.now() / 1000,
        _justCreated: true, // Flag for juice system
      },
    };

    entities.push(bullet);
  }

  // Check if key is pressed
  isKeyPressed(key: string): boolean {
    return this.inputState.keys.has(key.toUpperCase());
  }

  // Get mouse position
  getMousePosition(): { x: number; y: number } {
    return { ...this.inputState.mouse };
  }

  // Clear input state (useful for cleanup)
  clear() {
    this.inputState.keys.clear();
    this.inputState.mouse.buttons.clear();
  }
}
