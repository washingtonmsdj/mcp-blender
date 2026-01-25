// Timer System
export type Timer = {
  id: string;
  duration: number;
  elapsed: number;
  repeat: boolean;
  callback: () => void;
  active: boolean;
};

export class TimerSystem {
  private timers: Map<string, Timer> = new Map();

  create(id: string, duration: number, callback: () => void, repeat: boolean = false) {
    this.timers.set(id, {
      id,
      duration,
      elapsed: 0,
      repeat,
      callback,
      active: true,
    });
  }

  update(dt: number) {
    for (const timer of this.timers.values()) {
      if (!timer.active) continue;

      timer.elapsed += dt;

      if (timer.elapsed >= timer.duration) {
        timer.callback();

        if (timer.repeat) {
          timer.elapsed = 0;
        } else {
          timer.active = false;
        }
      }
    }
  }

  pause(id: string) {
    const timer = this.timers.get(id);
    if (timer) timer.active = false;
  }

  resume(id: string) {
    const timer = this.timers.get(id);
    if (timer) timer.active = true;
  }

  remove(id: string) {
    this.timers.delete(id);
  }

  clear() {
    this.timers.clear();
  }
}
