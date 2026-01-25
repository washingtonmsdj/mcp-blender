// Camera System
export type Camera = {
  x: number;
  y: number;
  width: number;
  height: number;
  zoom: number;
  rotation: number;
  followTarget: string | null;
  followSpeed: number;
  bounds?: {
    minX: number;
    minY: number;
    maxX: number;
    maxY: number;
  };
};

export class CameraSystem {
  private camera: Camera;

  constructor(width: number, height: number) {
    this.camera = {
      x: width / 2,
      y: height / 2,
      width,
      height,
      zoom: 1.0,
      rotation: 0,
      followTarget: null,
      followSpeed: 5,
    };
  }

  // Set position
  setPosition(x: number, y: number) {
    this.camera.x = x;
    this.camera.y = y;
    this.applyBounds();
  }

  // Move camera
  move(dx: number, dy: number) {
    this.camera.x += dx;
    this.camera.y += dy;
    this.applyBounds();
  }

  // Set zoom
  setZoom(zoom: number) {
    this.camera.zoom = Math.max(0.1, Math.min(5, zoom));
  }

  // Zoom in/out
  zoom(delta: number) {
    this.setZoom(this.camera.zoom + delta);
  }

  // Set rotation
  setRotation(rotation: number) {
    this.camera.rotation = rotation;
  }

  // Rotate
  rotate(delta: number) {
    this.camera.rotation += delta;
  }

  // Follow target
  follow(targetId: string, speed: number = 5) {
    this.camera.followTarget = targetId;
    this.camera.followSpeed = speed;
  }

  // Stop following
  stopFollow() {
    this.camera.followTarget = null;
  }

  // Set bounds
  setBounds(minX: number, minY: number, maxX: number, maxY: number) {
    this.camera.bounds = { minX, minY, maxX, maxY };
    this.applyBounds();
  }

  // Clear bounds
  clearBounds() {
    this.camera.bounds = undefined;
  }

  // Update camera (follow target)
  update(dt: number, entities: any[]) {
    if (!this.camera.followTarget) return;

    const target = entities.find(
      (e) => e.id === this.camera.followTarget || e.type === this.camera.followTarget
    );

    if (!target) return;

    // Smooth follow
    const dx = target.x - this.camera.x;
    const dy = target.y - this.camera.y;
    const speed = this.camera.followSpeed;

    this.camera.x += dx * speed * dt;
    this.camera.y += dy * speed * dt;

    this.applyBounds();
  }

  // Apply bounds
  private applyBounds() {
    if (!this.camera.bounds) return;

    const halfWidth = (this.camera.width / 2) / this.camera.zoom;
    const halfHeight = (this.camera.height / 2) / this.camera.zoom;

    this.camera.x = Math.max(
      this.camera.bounds.minX + halfWidth,
      Math.min(this.camera.bounds.maxX - halfWidth, this.camera.x)
    );

    this.camera.y = Math.max(
      this.camera.bounds.minY + halfHeight,
      Math.min(this.camera.bounds.maxY - halfHeight, this.camera.y)
    );
  }

  // Apply camera transform to canvas
  apply(ctx: CanvasRenderingContext2D) {
    ctx.save();
    
    // Center on camera position
    ctx.translate(this.camera.width / 2, this.camera.height / 2);
    
    // Apply zoom
    ctx.scale(this.camera.zoom, this.camera.zoom);
    
    // Apply rotation
    ctx.rotate(this.camera.rotation);
    
    // Translate to camera position
    ctx.translate(-this.camera.x, -this.camera.y);
  }

  // Restore canvas transform
  restore(ctx: CanvasRenderingContext2D) {
    ctx.restore();
  }

  // World to screen coordinates
  worldToScreen(worldX: number, worldY: number): { x: number; y: number } {
    const dx = worldX - this.camera.x;
    const dy = worldY - this.camera.y;

    return {
      x: this.camera.width / 2 + dx * this.camera.zoom,
      y: this.camera.height / 2 + dy * this.camera.zoom,
    };
  }

  // Screen to world coordinates
  screenToWorld(screenX: number, screenY: number): { x: number; y: number } {
    const dx = (screenX - this.camera.width / 2) / this.camera.zoom;
    const dy = (screenY - this.camera.height / 2) / this.camera.zoom;

    return {
      x: this.camera.x + dx,
      y: this.camera.y + dy,
    };
  }

  // Shake camera
  shake(intensity: number, duration: number) {
    const startX = this.camera.x;
    const startY = this.camera.y;
    const startTime = Date.now();

    const shakeInterval = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const progress = elapsed / duration;

      if (progress >= 1) {
        clearInterval(shakeInterval);
        this.camera.x = startX;
        this.camera.y = startY;
        return;
      }

      const currentIntensity = intensity * (1 - progress);
      this.camera.x = startX + (Math.random() - 0.5) * currentIntensity;
      this.camera.y = startY + (Math.random() - 0.5) * currentIntensity;
    }, 16);
  }

  // Get camera
  getCamera(): Camera {
    return this.camera;
  }
}
