export type OrdaxGameType = "platformer" | "topdown" | "shooter" | "puzzle" | "racing" | "sports" | "unknown";

export type OrdaxEntity = {
  id: string;
  type: string;
  x: number;
  y: number;
  w: number;
  h: number;
  props?: Record<string, unknown>;
  sprite?: {
    url: string;
    frameWidth: number;
    frameHeight: number;
    currentAnimation?: string;
  };
};

export type OrdaxVisualTheme = {
  /** CSS color string. Prefer hsl(...) */
  background?: string;
  primary?: string;
  accent?: string;
  /** CSS font-family string */
  font?: string;
};

export type OrdaxBackgroundLayer = {
  /** starfield | gradient | nebula (procedural) */
  type: "starfield" | "gradient" | "nebula" | "solid";
  /** 0..1 (how much it moves relative to camera) */
  parallax?: number;
  /** optional density for starfield */
  density?: number;
  /** optional speed for auto-scroll */
  speedY?: number;
};

export type OrdaxSpec = {
  gameType: OrdaxGameType;
  title: string;
  description: string;
  systems: string[];
  visual?: {
    theme?: OrdaxVisualTheme;
    background?: {
      layers: OrdaxBackgroundLayer[];
    };
  };
  audio?: {
    music?: string;
    sounds?: {
      collision?: string;
      score?: string;
      gameOver?: string;
      jump?: string;
      shoot?: string;
    };
  };
  scene: {
    gravity: { x: number; y: number };
    entities: OrdaxEntity[];
  };
};
