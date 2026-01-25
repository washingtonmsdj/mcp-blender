import { KEYS } from "./constants";
import type { GameInput } from "./types";

export class KeyboardInput {
  private down = new Set<string>();
  private pressed = new Set<string>();

  attach() {
    const onDown = (e: KeyboardEvent) => {
      this.down.add(e.key);
      this.pressed.add(e.key);
    };
    const onUp = (e: KeyboardEvent) => {
      this.down.delete(e.key);
    };
    window.addEventListener("keydown", onDown);
    window.addEventListener("keyup", onUp);
    return () => {
      window.removeEventListener("keydown", onDown);
      window.removeEventListener("keyup", onUp);
    };
  }

  /**
   * snapshot; `consumePress(key)` is used for one-shot actions.
   */
  getState(): GameInput {
    const has = (keys: readonly string[]) => keys.some((k) => this.down.has(k));
    return {
      up: has(KEYS.up),
      down: has(KEYS.down),
      left: has(KEYS.left),
      right: has(KEYS.right),
      shoot: has(KEYS.shoot),
      dash: has(KEYS.dash),
      special: has(KEYS.special),
      bomb: has(KEYS.bomb),
    };
  }

  consumePress(keys: readonly string[]): boolean {
    for (const k of keys) {
      if (this.pressed.has(k)) {
        this.pressed.delete(k);
        return true;
      }
    }
    return false;
  }
}
