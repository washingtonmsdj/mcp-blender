// Performance Monitor - Track FPS, frame time, and system performance

export type PerformanceReport = {
  fps: number;
  avgFrameTime: number;
  minFrameTime: number;
  maxFrameTime: number;
  systems: Record<string, {
    avg: number;
    min: number;
    max: number;
    percentage: number;
  }>;
  memory?: {
    used: number;
    total: number;
    percentage: number;
  };
};

export class PerformanceMonitor {
  private frameTimes: number[] = [];
  private systemTimes: Map<string, number[]> = new Map();
  private frameStart: number = 0;
  private systemStart: number = 0;
  private currentSystem: string | null = null;
  private maxSamples: number = 60;

  // Start frame timing
  startFrame(): void {
    this.frameStart = performance.now();
  }

  // End frame timing
  endFrame(): void {
    const frameTime = performance.now() - this.frameStart;
    this.frameTimes.push(frameTime);
    if (this.frameTimes.length > this.maxSamples) {
      this.frameTimes.shift();
    }
  }

  // Start system timing
  startSystem(name: string): void {
    this.currentSystem = name;
    this.systemStart = performance.now();
  }

  // End system timing
  endSystem(name: string): void {
    if (this.currentSystem !== name) {
      console.warn(`System timing mismatch: expected ${this.currentSystem}, got ${name}`);
      return;
    }

    const time = performance.now() - this.systemStart;
    
    if (!this.systemTimes.has(name)) {
      this.systemTimes.set(name, []);
    }
    
    const times = this.systemTimes.get(name)!;
    times.push(time);
    if (times.length > this.maxSamples) {
      times.shift();
    }

    this.currentSystem = null;
  }

  // Get performance report
  getReport(): PerformanceReport {
    const avgFrameTime = this.average(this.frameTimes);
    const fps = avgFrameTime > 0 ? 1000 / avgFrameTime : 0;

    const systems: Record<string, any> = {};
    for (const [name, times] of this.systemTimes) {
      const avg = this.average(times);
      const min = Math.min(...times);
      const max = Math.max(...times);
      const percentage = avgFrameTime > 0 ? (avg / avgFrameTime) * 100 : 0;

      systems[name] = { avg, min, max, percentage };
    }

    // Memory (if available)
    let memory: PerformanceReport["memory"] = undefined;
    if ((performance as any).memory) {
      const mem = (performance as any).memory;
      memory = {
        used: mem.usedJSHeapSize / 1024 / 1024, // MB
        total: mem.totalJSHeapSize / 1024 / 1024, // MB
        percentage: (mem.usedJSHeapSize / mem.totalJSHeapSize) * 100,
      };
    }

    return {
      fps: Math.round(fps),
      avgFrameTime: Math.round(avgFrameTime * 100) / 100,
      minFrameTime: Math.round(Math.min(...this.frameTimes) * 100) / 100,
      maxFrameTime: Math.round(Math.max(...this.frameTimes) * 100) / 100,
      systems,
      memory,
    };
  }

  // Get FPS
  getFPS(): number {
    const avgFrameTime = this.average(this.frameTimes);
    return avgFrameTime > 0 ? Math.round(1000 / avgFrameTime) : 0;
  }

  // Get frame times for graphing
  getFrameTimes(): number[] {
    return [...this.frameTimes];
  }

  // Get system times for graphing
  getSystemTimes(systemName: string): number[] {
    return [...(this.systemTimes.get(systemName) ?? [])];
  }

  // Clear all data
  clear(): void {
    this.frameTimes = [];
    this.systemTimes.clear();
  }

  // Helper: Calculate average
  private average(arr: number[]): number {
    if (arr.length === 0) return 0;
    return arr.reduce((a, b) => a + b, 0) / arr.length;
  }

  // Set max samples
  setMaxSamples(max: number): void {
    this.maxSamples = max;
  }
}
