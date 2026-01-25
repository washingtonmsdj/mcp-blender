// Animation System
export type AnimationFrame = {
  x: number;
  y: number;
  w: number;
  h: number;
  duration: number;
};

export type Animation = {
  name: string;
  frames: AnimationFrame[];
  loop: boolean;
  currentFrame: number;
  timer: number;
  playing: boolean;
};

export type AnimatedEntity = {
  id: string;
  animations: Map<string, Animation>;
  currentAnimation: string | null;
};

export class AnimationSystem {
  private entities: Map<string, AnimatedEntity> = new Map();

  // Register entity
  register(entityId: string): AnimatedEntity {
    const entity: AnimatedEntity = {
      id: entityId,
      animations: new Map(),
      currentAnimation: null,
    };
    
    this.entities.set(entityId, entity);
    return entity;
  }

  // Add animation
  addAnimation(
    entityId: string,
    name: string,
    frames: AnimationFrame[],
    loop: boolean = true
  ) {
    const entity = this.entities.get(entityId);
    if (!entity) return;

    entity.animations.set(name, {
      name,
      frames,
      loop,
      currentFrame: 0,
      timer: 0,
      playing: false,
    });
  }

  // Play animation
  play(entityId: string, animationName: string) {
    const entity = this.entities.get(entityId);
    if (!entity) return;

    const animation = entity.animations.get(animationName);
    if (!animation) return;

    entity.currentAnimation = animationName;
    animation.playing = true;
    animation.currentFrame = 0;
    animation.timer = 0;
  }

  // Stop animation
  stop(entityId: string) {
    const entity = this.entities.get(entityId);
    if (!entity || !entity.currentAnimation) return;

    const animation = entity.animations.get(entity.currentAnimation);
    if (animation) {
      animation.playing = false;
    }
  }

  // Update animations
  update(dt: number) {
    for (const entity of this.entities.values()) {
      if (!entity.currentAnimation) continue;

      const animation = entity.animations.get(entity.currentAnimation);
      if (!animation || !animation.playing) continue;

      animation.timer += dt;
      const frame = animation.frames[animation.currentFrame];

      if (animation.timer >= frame.duration) {
        animation.timer = 0;
        animation.currentFrame++;

        if (animation.currentFrame >= animation.frames.length) {
          if (animation.loop) {
            animation.currentFrame = 0;
          } else {
            animation.playing = false;
            animation.currentFrame = animation.frames.length - 1;
          }
        }
      }
    }
  }

  // Get current frame
  getCurrentFrame(entityId: string): AnimationFrame | null {
    const entity = this.entities.get(entityId);
    if (!entity || !entity.currentAnimation) return null;

    const animation = entity.animations.get(entity.currentAnimation);
    if (!animation) return null;

    return animation.frames[animation.currentFrame];
  }

  // Check if animation is playing
  isPlaying(entityId: string, animationName?: string): boolean {
    const entity = this.entities.get(entityId);
    if (!entity) return false;

    if (animationName) {
      const animation = entity.animations.get(animationName);
      return animation?.playing || false;
    }

    if (!entity.currentAnimation) return false;
    const animation = entity.animations.get(entity.currentAnimation);
    return animation?.playing || false;
  }

  // Unregister entity
  unregister(entityId: string) {
    this.entities.delete(entityId);
  }
}
